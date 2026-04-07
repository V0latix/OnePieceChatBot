"""Route GET /api/health."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.dependencies import get_health_snapshot
from src.api.models import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    """Retourne l'etat de sante de l'API."""
    payload = get_health_snapshot()
    return HealthResponse.model_validate(payload)
