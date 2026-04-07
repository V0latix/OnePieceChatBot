"""Route GET /api/health."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import RAGService, get_rag_service
from src.api.models import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health(service: RAGService = Depends(get_rag_service)) -> HealthResponse:
    """Retourne l'etat de sante de l'API."""
    payload = service.health()
    return HealthResponse.model_validate(payload)
