"""Reranking des resultats retrieval : fusion RRF puis cross-encoder (2e etage)."""

from __future__ import annotations

from typing import Any, Protocol

from utils.logger import get_logger

_logger = get_logger(__name__)


class RRFReranker:
    """Fusionne les rankings vecteur + BM25 par rang, + biais graphe.

    RRF (`score = Σ 1/(k+rang)`) est robuste aux echelles heterogenes (cosinus vs
    BM25 vs binaire) : plus de poids a calibrer a la main. Le signal graphe reste
    un biais additif (variante "weighted RRF"), les entites etant centrales pour
    les questions de lore One Piece.
    """

    def __init__(self, k: int = 60, graph_boost: float = 1.0) -> None:
        self.k = k
        self.graph_boost = graph_boost

    def _rank_contrib(self, results: list[Any], score_attr: str) -> dict[int, float]:
        """1/(k+rang) pour chaque resultat ayant un score > 0 sur ce signal."""
        ranked = sorted(
            (r for r in results if getattr(r, score_attr) > 0),
            key=lambda r: getattr(r, score_attr),
            reverse=True,
        )
        return {id(r): 1.0 / (self.k + rank) for rank, r in enumerate(ranked, start=1)}

    def rerank(self, results: list[Any]) -> list[Any]:
        """Calcule final_score par fusion RRF (vecteur + BM25 + graphe) et trie."""
        vec = self._rank_contrib(results, "vector_score")
        kw = self._rank_contrib(results, "keyword_score")
        # Le graphe est un 3e signal classe par rang (weighted RRF) : gere aussi bien
        # le score binaire (0/1) que le score continu PPR, sans poids a calibrer.
        gph = self._rank_contrib(results, "graph_score")
        for result in results:
            score = (
                vec.get(id(result), 0.0)
                + kw.get(id(result), 0.0)
                + self.graph_boost * gph.get(id(result), 0.0)
            )
            result.final_score = score
        return sorted(results, key=lambda item: item.final_score, reverse=True)


class _Predictor(Protocol):
    def predict(self, pairs: list[tuple[str, str]]) -> Any: ...


class CrossEncoderReranker:
    """2e etage : reordonne le top-N du RRF en scorant chaque paire (query, chunk).

    Le cross-encoder (bge-reranker-v2-m3) juge la pertinence query/passage bien mieux
    que la similarite cosinus seule, ce qui corrige les cas ou le bon chunk est
    recupere mais mal classe. Modele charge paresseusement au 1er appel.

    Degradation gracieuse : si le modele ne charge pas (hors-ligne, non telecharge)
    ou si predict echoue, on renvoie les resultats inchanges (comme les fallbacks
    Qdrant->local et Groq->Ollama du reste du pipeline).
    """

    def __init__(self, model_name: str, predictor: _Predictor | None = None) -> None:
        self.model_name = model_name
        self._predictor = predictor  # injectable pour les tests (evite le download)

    def _get_predictor(self) -> _Predictor | None:
        if self._predictor is None:
            try:
                from sentence_transformers import CrossEncoder

                try:
                    self._predictor = CrossEncoder(self.model_name)
                except Exception:  # noqa: BLE001 - reseau indispo -> cache local
                    self._predictor = CrossEncoder(self.model_name, local_files_only=True)
            except Exception as exc:  # noqa: BLE001 - modele indisponible
                _logger.warning("Cross-encoder indisponible (%s): fallback RRF seul", exc)
                return None
        return self._predictor

    def rerank(self, query: str, results: list[Any], top_n: int) -> list[Any]:
        """Reordonne les `top_n` premiers resultats par score cross-encoder.

        Les resultats au-dela de `top_n` ne sont pas rescored et gardent leur ordre.
        # ponytail: on ne rescore que le top_n ; un bon chunk classe plus bas par RRF
        # ne peut pas etre remonte -> augmenter rerank_candidates si besoin.
        """
        head = results[:top_n]
        tail = results[top_n:]
        if not head:
            return results

        predictor = self._get_predictor()
        if predictor is None:
            return results

        try:
            scores = predictor.predict([(query, r.content) for r in head])
        except Exception as exc:  # noqa: BLE001 - degradation gracieuse
            _logger.warning("Echec cross-encoder predict (%s): fallback RRF seul", exc)
            return results

        for result, score in zip(head, scores):
            result.rerank_score = float(score)
        head_sorted = sorted(head, key=lambda item: item.rerank_score, reverse=True)
        return head_sorted + tail
