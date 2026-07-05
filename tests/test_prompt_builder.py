"""Tests unitaires pour le grounding des citations."""

from __future__ import annotations

from rag.prompt_builder import grounded_ratio


def test_all_citations_valid() -> None:
    assert grounded_ratio("D'apres [1] et [2], Luffy...", n_sources=3) == 1.0


def test_no_citation_no_penalty() -> None:
    assert grounded_ratio("Luffy est le capitaine.", n_sources=3) == 1.0


def test_out_of_range_citation_penalized() -> None:
    # [9] n'existe pas parmi 2 sources -> 1 citation valide sur 2.
    assert grounded_ratio("Selon [1] et [9]", n_sources=2) == 0.5
