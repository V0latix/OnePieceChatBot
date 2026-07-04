"""Tests unitaires pour l'extracteur d'entites."""

from __future__ import annotations

from rag.entity_extractor import EntityExtractor
from rag.noise import is_noise_categories


def test_entity_extractor_detects_full_name_from_alias() -> None:
    extractor = EntityExtractor([
        "Monkey D. Luffy",
        "Trafalgar D. Water Law",
        "Roronoa Zoro",
    ])

    entities = extractor.extract("Quel est le fruit du demon de Law ?")

    assert "Trafalgar D. Water Law" in entities


def test_stopword_alias_does_not_false_match() -> None:
    """Le mot "who" de la question ne doit PAS resoudre vers "Who's-Who"."""
    extractor = EntityExtractor(["Who's-Who", "Trafalgar Law", "Monkey D. Luffy"])
    assert "Who's-Who" not in extractor.extract("Who is Monkey D. Luffy?")


def test_short_real_name_still_matches() -> None:
    """Un vrai nom court non-stopword (Law) reste detectable en anglais."""
    extractor = EntityExtractor(["Who's-Who", "Trafalgar Law"])
    assert "Trafalgar Law" in extractor.extract("What did Law do in Dressrosa?")


def test_noise_categories_flags_non_canon_pages() -> None:
    """Merch/jeux/chansons sont du bruit ; les vraies categories persos non."""
    assert is_noise_categories(["Music_Stubs", "Movie_Songs"])          # Compass
    assert is_noise_categories(["Merchandise"])                          # seal wafers
    assert is_noise_categories(["Mobile_Games"])                         # Bounty Rush
    assert not is_noise_categories(["Male_Characters", "Pirate_Captains"])  # Baggaley
