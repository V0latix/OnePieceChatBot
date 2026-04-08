"""Route GET /api/graph/{entity_name}."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.dependencies import RAGService, get_rag_service
from api.models import GraphResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/{entity_name}", response_model=GraphResponse)
def get_graph(
    entity_name: str,
    depth: int = Query(default=2, ge=1, le=3),
    service: RAGService = Depends(get_rag_service),
) -> GraphResponse:
    """Retourne un sous-graphe autour de l'entite cible."""
    data = service.get_graph(entity_name, depth=depth)
    return GraphResponse.model_validate(data)
