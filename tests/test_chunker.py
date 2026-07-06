"""Tests unitaires pour le chunker."""

from __future__ import annotations

from config.settings import Settings, get_settings
from processing.chunker import DocumentChunker
from scraper.exporter import ScrapedPageDocument


def _doc() -> ScrapedPageDocument:
    return ScrapedPageDocument(
        id="kuzan",
        title="Kuzan",
        url="https://onepiece.fandom.com/wiki/Kuzan",
        type="character",
        categories=["Characters"],
        infobox={},
        sections={"abilities_and_powers": "Il a mange le Hie Hie no Mi. " * 60},
        related_entities=[],
        last_scraped="2026-07-06T00:00:00Z",
    )


def test_chunker_creates_chunks_with_metadata() -> None:
    settings = get_settings()
    chunker = DocumentChunker(settings)

    document = ScrapedPageDocument(
        id="monkey_d_luffy",
        title="Monkey D. Luffy",
        url="https://onepiece.fandom.com/wiki/Monkey_D._Luffy",
        type="character",
        categories=["Characters"],
        infobox={"bounty": "3000000000"},
        sections={
            "appearance": "Luffy porte un chapeau de paille. " * 80,
            "history": {"early_life": "Natif de Foosha Village. " * 60},
        },
        related_entities=["Shanks", "Roronoa Zoro"],
        last_scraped="2026-04-07T00:00:00Z",
    )

    chunks = chunker.chunk_document(document)

    assert chunks
    assert all(chunk.entity_id == "monkey_d_luffy" for chunk in chunks)
    assert all(chunk.source_url == document.url for chunk in chunks)
    assert all(chunk.token_count > 0 for chunk in chunks)


def test_contextual_prefix_grounds_chunk_when_enabled() -> None:
    chunker = DocumentChunker(Settings(chunk_contextual=True))
    chunk = chunker.chunk_document(_doc())[0]
    # Le prefixe ancre le chunk a son entite/type/section...
    assert chunk.content.startswith("Page: Kuzan (character). Section: abilities and powers.")
    # ... sans perdre le texte original de la section.
    assert "Hie Hie no Mi" in chunk.content


def test_contextual_prefix_absent_when_disabled() -> None:
    chunker = DocumentChunker(Settings(chunk_contextual=False))
    chunk = chunker.chunk_document(_doc())[0]
    assert not chunk.content.startswith("Page:")
    assert chunk.content.startswith("Il a mange le Hie Hie no Mi")
