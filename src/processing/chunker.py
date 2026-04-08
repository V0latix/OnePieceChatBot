"""Decoupage semantique des documents One Piece en chunks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

import tiktoken
from pydantic import BaseModel, ConfigDict, Field

from config.settings import Settings
from scraper.exporter import ScrapedPageDocument

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover
    from langchain.text_splitter import RecursiveCharacterTextSplitter


class ChunkRecord(BaseModel):
    """Schema strict d'un chunk indexable."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    entity_id: str
    entity_name: str
    entity_type: str
    section: str
    content: str
    categories: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    token_count: int
    source_url: str


class DocumentChunker:
    """Transforme les documents pages en chunks exploitable par le retriever."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._tokenizer = self._init_tokenizer()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=self.count_tokens,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def _init_tokenizer(self) -> tiktoken.Encoding | None:
        """Initialise le tokenizer tiktoken, avec fallback offline si indisponible."""
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None

    def count_tokens(self, text: str) -> int:
        """Retourne un nombre de tokens, en mode offline si tiktoken est indisponible."""
        if self._tokenizer is not None:
            return len(self._tokenizer.encode(text))

        # Fallback deterministic offline pour eviter les dependances reseau en test/CI.
        return max(1, len(re.findall(r"\w+|[^\w\s]", text)))

    def _normalize_section_key(self, key: str) -> str:
        normalized = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in key.lower())
        return normalized.strip("_") or "overview"

    def _flatten_sections(self, sections: dict[str, Any], prefix: str | None = None) -> Iterable[tuple[str, str]]:
        for key, value in sections.items():
            section_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    yield section_key, stripped
            elif isinstance(value, dict):
                yield from self._flatten_sections(value, prefix=section_key)
            elif isinstance(value, list):
                joined = "; ".join(str(item).strip() for item in value if str(item).strip())
                if joined:
                    yield section_key, joined

    def chunk_document(self, document: ScrapedPageDocument) -> list[ChunkRecord]:
        """Decoupe un document en chunks avec metadonnees completes."""
        chunks: list[ChunkRecord] = []

        for section, section_text in self._flatten_sections(document.sections):
            normalized_section = self._normalize_section_key(section)
            section_chunks = self._splitter.split_text(section_text)

            if not section_chunks:
                continue

            for idx, chunk_text in enumerate(section_chunks, start=1):
                token_count = self.count_tokens(chunk_text)
                chunk = ChunkRecord(
                    chunk_id=f"{document.id}__{normalized_section}__{idx:03d}",
                    entity_id=document.id,
                    entity_name=document.title,
                    entity_type=document.type,
                    section=normalized_section,
                    content=chunk_text,
                    categories=document.categories,
                    related_entities=document.related_entities,
                    token_count=token_count,
                    source_url=document.url,
                )
                chunks.append(chunk)

        if not chunks:
            fallback_content = json.dumps(document.sections, ensure_ascii=False)
            chunks.append(
                ChunkRecord(
                    chunk_id=f"{document.id}__overview__001",
                    entity_id=document.id,
                    entity_name=document.title,
                    entity_type=document.type,
                    section="overview",
                    content=fallback_content,
                    categories=document.categories,
                    related_entities=document.related_entities,
                    token_count=self.count_tokens(fallback_content),
                    source_url=document.url,
                )
            )

        return chunks

    def chunk_documents(self, documents: list[ScrapedPageDocument]) -> list[ChunkRecord]:
        """Decoupe une liste de documents en une liste aplatit de chunks."""
        all_chunks: list[ChunkRecord] = []
        for document in documents:
            all_chunks.extend(self.chunk_document(document))
        return all_chunks

    def save_chunks_jsonl(self, chunks: list[ChunkRecord], output_path: Path) -> None:
        """Persiste les chunks en JSONL."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(chunk.model_dump_json())
                handle.write("\n")
