"""Tests unitaires pour le reranker RRF."""

from __future__ import annotations

from rag.reranker import CrossEncoderReranker, RRFReranker
from rag.retriever import RetrievalResult


def _result(
    chunk_id: str,
    vector: float = 0.0,
    keyword: float = 0.0,
    graph: float = 0.0,
    content: str = "",
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        entity_name=chunk_id,
        entity_type="character",
        section="overview",
        content=content or chunk_id,
        source_url="",
        vector_score=vector,
        keyword_score=keyword,
        graph_score=graph,
    )


def test_rrf_orders_by_combined_rank() -> None:
    # b est 1er en vecteur mais dernier en keyword ; a est 2e/1er -> a gagne.
    a = _result("a", vector=0.8, keyword=5.0)
    b = _result("b", vector=0.9, keyword=1.0)
    ranked = RRFReranker(k=60).rerank([a, b])
    assert ranked[0].chunk_id == "a"


def test_graph_boost_breaks_tie() -> None:
    # Scores identiques ; seul b a le signal graphe -> b passe devant.
    a = _result("a", vector=0.5, keyword=2.0)
    b = _result("b", vector=0.5, keyword=2.0, graph=1.0)
    ranked = RRFReranker(k=60, graph_boost=1.0).rerank([a, b])
    assert ranked[0].chunk_id == "b"


def test_zero_signal_contributes_nothing() -> None:
    # Un resultat sans aucun signal reste a 0.
    solo = _result("solo")
    ranked = RRFReranker().rerank([solo])
    assert ranked[0].final_score == 0.0


def test_continuous_graph_score_orders_by_proximity() -> None:
    # Graphe seul signal : le graph_score continu (PPR) classe b (0.9) devant a (0.1).
    a = _result("a", graph=0.1)
    b = _result("b", graph=0.9)
    ranked = RRFReranker(k=60, graph_boost=1.0).rerank([a, b])
    assert ranked[0].chunk_id == "b"


# --- Cross-encoder (2e etage) ---------------------------------------------


class _FakePredictor:
    """Retourne un score par (query, content) selon une table, sans reseau."""

    def __init__(self, scores_by_content: dict[str, float]) -> None:
        self.scores_by_content = scores_by_content

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        return [self.scores_by_content[content] for _query, content in pairs]


def test_cross_encoder_reorders_top_n_by_score() -> None:
    # RRF donne l'ordre [a, b] ; le cross-encoder prefere b -> b passe devant.
    a = _result("a", content="doc a")
    b = _result("b", content="doc b")
    ce = CrossEncoderReranker("fake", predictor=_FakePredictor({"doc a": 0.1, "doc b": 0.9}))
    ranked = ce.rerank("q", [a, b], top_n=2)
    assert [r.chunk_id for r in ranked] == ["b", "a"]
    assert ranked[0].rerank_score == 0.9


def test_cross_encoder_leaves_tail_untouched() -> None:
    # Seuls les top_n=1 premiers sont rescored ; le reste garde son ordre.
    a = _result("a", content="doc a")
    b = _result("b", content="doc b")
    c = _result("c", content="doc c")
    ce = CrossEncoderReranker("fake", predictor=_FakePredictor({"doc a": 0.5}))
    ranked = ce.rerank("q", [a, b, c], top_n=1)
    assert [r.chunk_id for r in ranked] == ["a", "b", "c"]


def test_cross_encoder_degrades_gracefully_on_predict_error() -> None:
    class _Boom:
        def predict(self, pairs):  # noqa: ANN001, ANN201
            raise RuntimeError("model exploded")

    a = _result("a", vector=0.9, content="doc a")
    b = _result("b", vector=0.1, content="doc b")
    ce = CrossEncoderReranker("fake", predictor=_Boom())
    ranked = ce.rerank("q", [a, b], top_n=2)
    # ordre d'entree preserve, pas de crash
    assert [r.chunk_id for r in ranked] == ["a", "b"]
