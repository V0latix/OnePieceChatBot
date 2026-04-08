"""Schemas Pydantic pour les endpoints API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConversationMessage(BaseModel):
    """Un tour de conversation (user ou assistant)."""

    model_config = ConfigDict(extra="forbid")

    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1)


class AskRequest(BaseModel):
    """Payload pour POST /api/ask."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    spoiler_limit_arc: str | None = None
    history: list[ConversationMessage] = Field(default_factory=list, max_length=20)


class SourceCitation(BaseModel):
    """Source de contexte utilisee dans une reponse."""

    model_config = ConfigDict(extra="forbid")

    entity_name: str
    section: str
    source_url: str
    score: float


class AskResponse(BaseModel):
    """Reponse standard du pipeline RAG."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    sources: list[SourceCitation]
    entities: list[str]
    confidence: float


class EntityResponse(BaseModel):
    """Representation detaillee d'une entite."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    infobox: dict[str, str]
    relations: list[dict[str, str]]


class GraphResponse(BaseModel):
    """Sous-graphe retourne par GET /api/graph/{entity}."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[dict[str, str]]
    edges: list[dict[str, str]]


class SearchResult(BaseModel):
    """Resultat de recherche /api/search."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    entity_name: str
    entity_type: str
    section: str
    content: str
    source_url: str
    score: float


class SearchResponse(BaseModel):
    """Payload de reponse /api/search."""

    model_config = ConfigDict(extra="forbid")

    results: list[SearchResult]


class HealthResponse(BaseModel):
    """Payload de sante applicative."""

    model_config = ConfigDict(extra="forbid")

    status: str
    chunks_count: int
    graph_nodes: int
