"""Route POST /api/ask."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import RAGService, get_rag_service
from src.api.models import AskRequest, AskResponse

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
def ask(payload: AskRequest, service: RAGService = Depends(get_rag_service)) -> AskResponse:
    """Repond a une question via pipeline RAG."""
    return service.ask(payload.question, spoiler_limit_arc=payload.spoiler_limit_arc)
