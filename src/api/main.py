"""Application FastAPI principale."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.limiter import limiter
from api.routes.ask import router as ask_router
from api.routes.entity import router as entity_router
from api.routes.graph import router as graph_router
from api.routes.health import router as health_router
from api.routes.search import router as search_router

app = FastAPI(title="One Piece RAG API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ask_router, prefix="/api")
app.include_router(entity_router, prefix="/api")
app.include_router(graph_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(health_router, prefix="/api")
