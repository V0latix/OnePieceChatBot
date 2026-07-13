"""Route GET /api/search."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.dependencies import RAGService, get_rag_service
from api.models import SearchResponse, SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(min_length=1),
    type: str | None = Query(default=None),
    service: RAGService = Depends(get_rag_service),
) -> SearchResponse:
    """Expose les meilleurs chunks retrieval pour une requete."""
    results = service.search(q, entity_type=type)
    payload = [
        SearchResult(
            chunk_id=result.chunk_id,
            entity_name=result.entity_name,
            entity_type=result.entity_type,
            section=result.section,
            content=result.content,
            source_url=result.source_url,
            score=result.final_score,
        )
        for result in results
    ]
    return SearchResponse(results=payload)
