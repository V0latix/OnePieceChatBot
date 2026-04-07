"""Tests unitaires scraper/cleaner."""

from __future__ import annotations

from src.scraper.cleaner import WikitextCleaner


def test_cleaner_extracts_infobox_and_sections() -> None:
    cleaner = WikitextCleaner()
    sample = """
{{Infobox Character
|name = Monkey D. Luffy
|bounty = 3000000000
}}
== Appearance ==
Luffy porte un chapeau de paille.
== Abilities and Powers ==
Il maitrise le Haki.
"""
    page = cleaner.clean_page(
        title="Monkey D. Luffy",
        url="https://onepiece.fandom.com/wiki/Monkey_D._Luffy",
        categories=["Characters"],
        wikitext=sample,
    )

    assert page.infobox.get("name") == "Monkey D. Luffy"
    assert "appearance" in page.sections
    assert page.related_entities == []
