"""Tests unitaires pour l'extracteur d'entites."""

from __future__ import annotations

from rag.entity_extractor import EntityExtractor, _mine_aliases
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


def test_fuzzy_fallback_matches_typo() -> None:
    """Une faute de frappe ("Zorro") resout vers l'entite via difflib."""
    extractor = EntityExtractor(["Roronoa Zoro", "Monkey D. Luffy"])
    assert "Roronoa Zoro" in extractor.extract("Que fait Zorro au combat ?")


def test_fuzzy_fallback_ignores_unrelated_token() -> None:
    """Un mot sans rapport ne doit pas declencher de faux positif."""
    extractor = EntityExtractor(["Roronoa Zoro", "Monkey D. Luffy"])
    assert extractor.extract("Explique la photosynthese des plantes") == []


def test_alias_collision_resolves_to_canonical_by_importance() -> None:
    """"luffy" doit resoudre vers Monkey D. Luffy (145 related), pas Nightmare Luffy (1)."""
    importance = {"Monkey D. Luffy": 145, "Nightmare Luffy": 1}
    # Ordre d'insertion inverse : prouve que ce n'est pas du last-write-wins.
    extractor = EntityExtractor(["Monkey D. Luffy", "Nightmare Luffy"], importance=importance)
    assert "Monkey D. Luffy" in extractor.extract("Quel est le fruit de Luffy ?")
    assert "Nightmare Luffy" not in extractor.extract("Quel est le fruit de Luffy ?")

    extractor_rev = EntityExtractor(["Nightmare Luffy", "Monkey D. Luffy"], importance=importance)
    assert "Monkey D. Luffy" in extractor_rev.extract("Quel est le fruit de Luffy ?")


def test_no_importance_first_write_wins() -> None:
    """Sans prior d'importance, la 1ere entite listee garde l'alias (ordre stable)."""
    assert "Monkey D. Luffy" in EntityExtractor(
        ["Monkey D. Luffy", "Nightmare Luffy"]
    ).extract("Quel est le fruit de Luffy ?")
    assert "Nightmare Luffy" in EntityExtractor(
        ["Nightmare Luffy", "Monkey D. Luffy"]
    ).extract("Quel est le fruit de Luffy ?")


def test_mine_aliases_from_lede() -> None:
    """Le lede "X, known by his alias Y, is..." doit extraire Y."""
    assert _mine_aliases("Kuzan, better known by his alias Aokiji, is one of the Ten.") == ["Aokiji"]
    assert _mine_aliases('Edward Newgate, more commonly known as "Whitebeard", was a pirate.') == ["Whitebeard"]
    assert _mine_aliases("Sakazuki, formerly known by his Admiral alias Akainu, is Fleet Admiral.") == ["Akainu"]


def test_mine_aliases_ignores_benign_sentences() -> None:
    """Pas d'alias -> rien (pas de faux positif sur une phrase descriptive)."""
    assert _mine_aliases("This island is a place where pirates gather and fight.") == []
    assert _mine_aliases("It is commonly known as the Grand Line by sailors.") == []


def test_mined_alias_resolves_to_entity() -> None:
    """"aokiji" (alias hors-titre) doit resoudre vers Kuzan."""
    extractor = EntityExtractor(["Kuzan"], extra_aliases={"Kuzan": ["Aokiji"]})
    assert "Kuzan" in extractor.extract("Qui est l'amiral Aokiji ?")


def test_mined_alias_does_not_clobber_important_title() -> None:
    """Un alias mine ne doit pas voler une cle a un titre canonique plus important."""
    extractor = EntityExtractor(
        ["Baroque Works", "Zala"],
        importance={"Baroque Works": 50, "Zala": 2},
        extra_aliases={"Zala": ["Baroque Works"]},
    )
    assert "Baroque Works" in extractor.extract("Parle-moi de Baroque Works")
    assert "Zala" not in extractor.extract("Parle-moi de Baroque Works")


def test_noise_categories_flags_non_canon_pages() -> None:
    """Merch/jeux/chansons sont du bruit ; les vraies categories persos non."""
    assert is_noise_categories(["Music_Stubs", "Movie_Songs"])          # Compass
    assert is_noise_categories(["Merchandise"])                          # seal wafers
    assert is_noise_categories(["Mobile_Games"])                         # Bounty Rush
    assert not is_noise_categories(["Male_Characters", "Pirate_Captains"])  # Baggaley
