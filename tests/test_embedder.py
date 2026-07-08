"""Tests du prefixe de requete adapte au modele d'embedding (sans charger de modele)."""

from __future__ import annotations

from processing.embedder import _query_prefix


def test_bge_large_uses_instruction_prefix() -> None:
    assert _query_prefix("BAAI/bge-large-en-v1.5") == "Represent this sentence for retrieval: "


def test_bge_m3_uses_no_prefix() -> None:
    assert _query_prefix("BAAI/bge-m3") == ""
    assert _query_prefix("bge-m3") == ""
