"""Interface Supabase/pgvector pour stocker et rechercher les chunks."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict
from supabase import Client, create_client

from src.processing.chunker import ChunkRecord


class VectorSearchResult(BaseModel):
    """Resultat normalise d'une recherche vectorielle."""

    model_config = ConfigDict(extra="ignore")

    id: str
    entity_name: str
    entity_type: str
    section: str
    content: str
    similarity: float


class SupabaseVectorStore:
    """Client de persistance sur la table `op_chunks`."""

    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        self.client: Client = create_client(supabase_url, supabase_key)

    def upsert_chunks(self, chunks: list[ChunkRecord], embeddings: list[list[float]]) -> None:
        """Upsert batch des chunks et embeddings."""
        if len(chunks) != len(embeddings):
            raise ValueError("Le nombre de chunks doit correspondre au nombre d'embeddings")

        payload: list[dict[str, Any]] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            payload.append(
                {
                    "id": chunk.chunk_id,
                    "entity_id": chunk.entity_id,
                    "entity_name": chunk.entity_name,
                    "entity_type": chunk.entity_type,
                    "section": chunk.section,
                    "content": chunk.content,
                    "embedding": embedding,
                    "categories": chunk.categories,
                    "related_entities": chunk.related_entities,
                    "token_count": chunk.token_count,
                    "source_url": chunk.source_url,
                }
            )

        self.client.table("op_chunks").upsert(payload, on_conflict="id").execute()

    def search(
        self,
        query_embedding: list[float],
        match_count: int = 5,
        filter_type: str | None = None,
    ) -> list[VectorSearchResult]:
        """Interroge la fonction SQL `search_chunks`."""
        response = self.client.rpc(
            "search_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": match_count,
                "filter_type": filter_type,
            },
        ).execute()

        data = response.data or []
        return [VectorSearchResult.model_validate(row) for row in data]
