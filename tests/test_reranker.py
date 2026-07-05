"""Tests unitaires pour le reranker RRF."""

from __future__ import annotations

from rag.reranker import RRFReranker
from rag.retriever import RetrievalResult


def _result(chunk_id: str, vector: float = 0.0, keyword: float = 0.0, graph: float = 0.0) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        entity_name=chunk_id,
        entity_type="character",
        section="overview",
        content="",
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
