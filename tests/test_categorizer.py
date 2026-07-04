"""Tests du categoriseur — regression sur le bug underscore."""

from __future__ import annotations

from scraper.categorizer import PageCategorizer


def test_underscore_categories_are_normalized() -> None:
    """Les categories Fandom a underscores doivent matcher les regles multi-mots."""
    cat = PageCategorizer()
    # Avant le fix, ces categories tombaient en "unknown".
    assert cat.detect_entity_type("Gomu Gomu no Mi", ["Paramecia", "Devil_Fruits"]) == "devil_fruit"
    assert cat.detect_entity_type("Straw Hat Pirates", ["Pirate_Crews"]) == "crew"
    assert cat.detect_entity_type("Cipher Pol", ["World_Government"]) == "organization"


def test_character_pages_still_win_over_fruit_type() -> None:
    """Un perso (avec 'Male Characters') reste 'character', pas 'devil_fruit'."""
    cat = PageCategorizer()
    result = cat.detect_entity_type("Monkey D. Luffy", ["Male_Characters", "Paramecia"])
    assert result == "character"
