"""Tests du GraphRanker (Personalized PageRank sur les triplets)."""

from __future__ import annotations

import json
from pathlib import Path

from rag.graph_ranker import GraphRanker


def _write_triplets(path: Path, edges: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for subj, obj in edges:
            handle.write(json.dumps({"subject": subj, "relation": "RELATED_TO", "object": obj}) + "\n")


def test_ppr_ranks_neighbour_above_distant(tmp_path: Path) -> None:
    # Graphe: A-B-C-D en chaine. Seede sur A -> B (voisin direct) > D (loin).
    triplets = tmp_path / "triplets.jsonl"
    _write_triplets(triplets, [("A", "B"), ("B", "C"), ("C", "D")])
    scores = GraphRanker(triplets).personalized_scores(["A"])
    assert scores["B"] > scores["D"]


def test_ppr_empty_when_seed_absent(tmp_path: Path) -> None:
    triplets = tmp_path / "triplets.jsonl"
    _write_triplets(triplets, [("A", "B")])
    assert GraphRanker(triplets).personalized_scores(["Zoro"]) == {}
    assert GraphRanker(triplets).personalized_scores([]) == {}


def test_ppr_missing_file_degrades_gracefully(tmp_path: Path) -> None:
    ranker = GraphRanker(tmp_path / "does_not_exist.jsonl")
    assert ranker.personalized_scores(["A"]) == {}
