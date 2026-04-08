"""Tests unitaires pour le chunker."""

from __future__ import annotations

from config.settings import get_settings
from processing.chunker import DocumentChunker
from scraper.exporter import ScrapedPageDocument


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
