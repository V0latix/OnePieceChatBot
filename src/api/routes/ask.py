"""Route POST /api/ask."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from api.dependencies import RAGService, get_rag_service
from api.models import AskRequest, AskResponse
from api.limiter import limiter

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
@limiter.limit("10/minute")
def ask(request: Request, payload: AskRequest, service: RAGService = Depends(get_rag_service)) -> AskResponse:
    """Repond a une question via pipeline RAG."""
    history = [msg.model_dump() for msg in payload.history] if payload.history else None
    return service.ask(payload.question, spoiler_limit_arc=payload.spoiler_limit_arc, history=history)


@router.post("/stream")
@limiter.limit("10/minute")
def ask_stream(request: Request, payload: AskRequest, service: RAGService = Depends(get_rag_service)) -> StreamingResponse:
    """Repond a une question en streaming SSE (Server-Sent Events).

    Evenements emis:
        metadata — sources, entities, confidence (avant les tokens)
        token    — fragment de texte
        done     — fin du stream
    """
    history = [msg.model_dump() for msg in payload.history] if payload.history else None
    return StreamingResponse(
        service.ask_stream(payload.question, spoiler_limit_arc=payload.spoiler_limit_arc, history=history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
