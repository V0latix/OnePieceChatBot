"""Retrieval hybride: vector search + keyword + signal graph."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from config.settings import Settings
from processing.embedder import EmbeddingGenerator
from processing.vector_store import QdrantVectorStore


_WORD_RE = re.compile(r"[a-zA-Z0-9']+")


class EmbeddedChunk(BaseModel):
    """Chunk local enrichi avec son embedding."""

    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    entity_id: str
    entity_name: str
    entity_type: str
    section: str
    content: str
    categories: list[str]
    related_entities: list[str]
    token_count: int
    source_url: str
    embedding: list[float]


class RetrievalResult(BaseModel):
    """Resultat normalise apres retrieval."""

    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    entity_name: str
    entity_type: str
    section: str
    content: str
    source_url: str
    vector_score: float = 0.0
    keyword_score: float = 0.0
    graph_score: float = 0.0
    final_score: float = 0.0


class HybridRetriever:
    """Retriever principal combine vectoriel, lexical et signal entite."""

    def __init__(
        self,
        settings: Settings,
        embedder: EmbeddingGenerator,
        vector_store: QdrantVectorStore | None = None,
        local_embeddings_path: Path | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder
        self.vector_store = vector_store
        self.local_embeddings_path = local_embeddings_path or settings.chunk_data_dir / "chunks_with_embeddings.jsonl"
        self.local_index = self._load_local_index()

    def _load_local_index(self) -> list[EmbeddedChunk]:
        if not self.local_embeddings_path.exists():
            return []

        entries: list[EmbeddedChunk] = []
        with self.local_embeddings_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entries.append(EmbeddedChunk.model_validate_json(line))
        return entries

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    def _keyword_score(self, query_terms: set[str], content: str) -> float:
        if not query_terms:
            return 0.0
        content_terms = set(term.lower() for term in _WORD_RE.findall(content))
        overlap = query_terms.intersection(content_terms)
        return len(overlap) / len(query_terms)

    def _local_vector_search(
        self,
        query_embedding: list[float],
        filter_type: str | None,
        top_k: int,
    ) -> list[RetrievalResult]:
        scored: list[RetrievalResult] = []

        for chunk in self.local_index:
            if filter_type and chunk.entity_type != filter_type:
                continue
            similarity = self._cosine_similarity(query_embedding, chunk.embedding)
            scored.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    entity_name=chunk.entity_name,
                    entity_type=chunk.entity_type,
                    section=chunk.section,
                    content=chunk.content,
                    source_url=chunk.source_url,
                    vector_score=similarity,
                )
            )

        scored.sort(key=lambda row: row.vector_score, reverse=True)
        return scored[:top_k]

    def _remote_vector_search(
        self,
        query_embedding: list[float],
        filter_type: str | None,
        top_k: int,
    ) -> list[RetrievalResult]:
        if self.vector_store is None:
            return []

        try:
            rows = self.vector_store.search(
                query_embedding=query_embedding,
                match_count=top_k,
                filter_type=filter_type,
            )
        except Exception:
            return []

        return [
            RetrievalResult(
                chunk_id=row.id,
                entity_name=row.entity_name,
                entity_type=row.entity_type,
                section=row.section,
                content=row.content,
                source_url="",
                vector_score=float(row.similarity),
            )
            for row in rows
        ]

    def retrieve(
        self,
        question: str,
        entities: list[str] | None = None,
        filter_type: str | None = None,
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        """Execute la recherche hybride pour une question."""
        top_k = top_k or self.settings.retrieval_top_k
        entities = entities or []

        query_embedding = self.embedder.embed_query(question)

        vector_results = self._remote_vector_search(query_embedding, filter_type, top_k)
        if not vector_results:
            vector_results = self._local_vector_search(query_embedding, filter_type, max(top_k * 3, top_k))

        query_terms = set(term.lower() for term in _WORD_RE.findall(question) if len(term) >= 3)

        combined: dict[str, RetrievalResult] = {}
        for result in vector_results:
            result.keyword_score = self._keyword_score(query_terms, result.content)
            if entities and any(entity.lower() in result.entity_name.lower() for entity in entities):
                result.graph_score = 1.0
            combined[result.chunk_id] = result

        # Ajout lexical pur si l'index local existe.
        for chunk in self.local_index:
            keyword_score = self._keyword_score(query_terms, chunk.content)
            if keyword_score <= 0:
                continue
            existing = combined.get(chunk.chunk_id)
            if existing:
                existing.keyword_score = max(existing.keyword_score, keyword_score)
                continue
            combined[chunk.chunk_id] = RetrievalResult(
                chunk_id=chunk.chunk_id,
                entity_name=chunk.entity_name,
                entity_type=chunk.entity_type,
                section=chunk.section,
                content=chunk.content,
                source_url=chunk.source_url,
                keyword_score=keyword_score,
                graph_score=1.0 if any(entity.lower() in chunk.entity_name.lower() for entity in entities) else 0.0,
            )

        results = list(combined.values())
        return results
