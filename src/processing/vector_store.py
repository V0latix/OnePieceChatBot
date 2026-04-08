"""Interface Qdrant pour stocker et rechercher les chunks vectorises."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from src.processing.chunker import ChunkRecord
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

# Dimensions du modele BAAI/bge-large-en-v1.5
_VECTOR_SIZE = 1024


def _chunk_id_to_uuid(chunk_id: str) -> str:
    """Convertit un chunk_id string en UUID v5 deterministe (requis par Qdrant)."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))


class VectorSearchResult(BaseModel):
    """Resultat normalise d'une recherche vectorielle."""

    model_config = ConfigDict(extra="ignore")

    id: str
    entity_name: str
    entity_type: str
    section: str
    content: str
    similarity: float


class QdrantVectorStore:
    """Client de persistance sur une collection Qdrant Cloud."""

    def __init__(self, qdrant_url: str, qdrant_api_key: str, collection_name: str = "op_chunks") -> None:
        self.collection_name = collection_name
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self._cb = CircuitBreaker("qdrant", failure_threshold=3, recovery_timeout=60.0)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Cree la collection si elle n'existe pas encore."""
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
            )

    def upsert_chunks(self, chunks: list[ChunkRecord], embeddings: list[list[float]]) -> None:
        """Upsert batch des chunks et embeddings dans Qdrant."""
        if len(chunks) != len(embeddings):
            raise ValueError("Le nombre de chunks doit correspondre au nombre d'embeddings")

        points = [
            PointStruct(
                id=_chunk_id_to_uuid(chunk.chunk_id),
                vector=embedding,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "entity_id": chunk.entity_id,
                    "entity_name": chunk.entity_name,
                    "entity_type": chunk.entity_type,
                    "section": chunk.section,
                    "content": chunk.content,
                    "categories": chunk.categories,
                    "related_entities": chunk.related_entities,
                    "token_count": chunk.token_count,
                    "source_url": chunk.source_url or "",
                },
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]

        # Upload par batch de 100 pour eviter les timeouts
        batch_size = 100
        self._cb.before_call()
        try:
            for i in range(0, len(points), batch_size):
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points[i : i + batch_size],
                )
            self._cb.on_success()
        except CircuitBreakerOpen:
            raise
        except Exception as exc:
            self._cb.on_failure()
            raise exc

    def search(
        self,
        query_embedding: list[float],
        match_count: int = 5,
        filter_type: str | None = None,
    ) -> list[VectorSearchResult]:
        """Recherche les chunks les plus similaires. Retourne [] si circuit ouvert."""
        try:
            self._cb.before_call()
        except CircuitBreakerOpen:
            return []

        query_filter = None
        if filter_type:
            query_filter = Filter(
                must=[FieldCondition(key="entity_type", match=MatchValue(value=filter_type))]
            )

        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=match_count,
                query_filter=query_filter,
                with_payload=True,
            )
            results = [
                VectorSearchResult(
                    id=hit.payload.get("chunk_id", str(hit.id)),
                    entity_name=hit.payload.get("entity_name", ""),
                    entity_type=hit.payload.get("entity_type", ""),
                    section=hit.payload.get("section", ""),
                    content=hit.payload.get("content", ""),
                    similarity=hit.score,
                )
                for hit in hits
            ]
            self._cb.on_success()
            return results
        except Exception:
            self._cb.on_failure()
            return []
