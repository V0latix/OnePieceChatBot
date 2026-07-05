"""Reranking des resultats retrieval via fusion RRF (Reciprocal Rank Fusion)."""

from __future__ import annotations

from typing import Any


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
        """Calcule final_score par fusion RRF et trie les resultats."""
        vec = self._rank_contrib(results, "vector_score")
        kw = self._rank_contrib(results, "keyword_score")
        for result in results:
            score = vec.get(id(result), 0.0) + kw.get(id(result), 0.0)
            if result.graph_score > 0:
                score += self.graph_boost / (self.k + 1)
            result.final_score = score
        return sorted(results, key=lambda item: item.final_score, reverse=True)
