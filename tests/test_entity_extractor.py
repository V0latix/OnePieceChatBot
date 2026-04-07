"""Tests unitaires pour l'extracteur d'entites."""

from __future__ import annotations

from src.rag.entity_extractor import EntityExtractor


def test_entity_extractor_detects_full_name_from_alias() -> None:
    extractor = EntityExtractor([
        "Monkey D. Luffy",
        "Trafalgar D. Water Law",
        "Roronoa Zoro",
    ])

    entities = extractor.extract("Quel est le fruit du demon de Law ?")

    assert "Trafalgar D. Water Law" in entities
