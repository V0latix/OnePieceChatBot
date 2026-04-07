"""Reranking des resultats retrieval via score pondere."""

from __future__ import annotations

from typing import Any


class WeightedReranker:
    """Applique une combinaison ponderee vector/graph/keyword."""

    def __init__(self, vector_weight: float = 0.4, graph_weight: float = 0.4, keyword_weight: float = 0.2) -> None:
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        self.keyword_weight = keyword_weight

    def rerank(self, results: list[Any]) -> list[Any]:
        """Calcule final_score et trie les resultats."""
        for result in results:
            result.final_score = (
                result.vector_score * self.vector_weight
                + result.graph_score * self.graph_weight
                + result.keyword_score * self.keyword_weight
            )
        return sorted(results, key=lambda item: item.final_score, reverse=True)
