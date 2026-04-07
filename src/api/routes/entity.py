"""Route GET /api/entity/{entity_name}."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import RAGService, get_rag_service
from src.api.models import EntityResponse

router = APIRouter(prefix="/entity", tags=["entity"])


@router.get("/{entity_name}", response_model=EntityResponse)
def get_entity(entity_name: str, service: RAGService = Depends(get_rag_service)) -> EntityResponse:
    """Retourne la fiche detaillee d'une entite."""
    data = service.get_entity(entity_name)
    if data is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityResponse.model_validate(data)
