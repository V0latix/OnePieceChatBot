"""Injection de dependances FastAPI."""

from __future__ import annotations

import json
import re
from collections.abc import Generator
from functools import lru_cache

from src.api.models import AskResponse, SourceCitation
from src.config.settings import Settings, get_settings
from src.processing.embedder import EmbeddingGenerator
from src.processing.graph_builder import GraphBuilder
from src.processing.vector_store import SupabaseVectorStore
from src.rag.entity_extractor import EntityExtractor
from src.rag.generator import AnswerGenerator
from src.rag.graph_retriever import GraphRetriever
from src.rag.prompt_builder import PromptBuilder
from src.rag.reranker import WeightedReranker
from src.rag.retriever import HybridRetriever, RetrievalResult
from src.utils.logger import configure_logging, get_logger


_SLUG_RE = re.compile(r"[^a-z0-9]+")


class RAGService:
    """Facade applicative pour servir le pipeline RAG aux routes API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        configure_logging(settings.log_level)
        self.logger = get_logger(__name__)

        self.entity_extractor = EntityExtractor.from_raw_documents(settings.raw_data_dir)
        self.vector_store = (
            SupabaseVectorStore(settings.supabase_url, settings.supabase_key)
            if settings.supabase_url and settings.supabase_key
            else None
        )
        self._embedder: EmbeddingGenerator | None = None
        self._retriever: HybridRetriever | None = None
        self.reranker = WeightedReranker(
            vector_weight=settings.rerank_vector_weight,
            graph_weight=settings.rerank_graph_weight,
            keyword_weight=settings.rerank_keyword_weight,
        )
        self.prompt_builder = PromptBuilder()
        self.generator = AnswerGenerator(settings, self.prompt_builder)
        self.graph_retriever = GraphRetriever(settings)

    def _slugify(self, value: str) -> str:
        return _SLUG_RE.sub("_", value.lower()).strip("_")

    def _sources_from_results(self, results: list[RetrievalResult]) -> list[SourceCitation]:
        return [
            SourceCitation(
                entity_name=result.entity_name,
                section=result.section,
                source_url=result.source_url,
                score=result.final_score,
            )
            for result in results
        ]

    def _get_retriever(self) -> HybridRetriever:
        """Initialise le retriever a la demande pour eviter un cold-start lourd."""
        if self._retriever is None:
            self._embedder = EmbeddingGenerator(self.settings.embedding_model)
            self._retriever = HybridRetriever(
                settings=self.settings,
                embedder=self._embedder,
                vector_store=self.vector_store,
            )
        return self._retriever

    def ask(self, question: str, spoiler_limit_arc: str | None = None) -> AskResponse:
        """Execute une requete RAG complete."""
        retriever = self._get_retriever()
        entities = self.entity_extractor.extract(question)
        retrieval_results = retriever.retrieve(
            question=question,
            entities=entities,
            top_k=max(self.settings.retrieval_top_k * 3, self.settings.retrieval_top_k),
        )
        reranked = self.reranker.rerank(retrieval_results)
        top_results = reranked[: self.settings.retrieval_top_k]

        graph_rows: list[dict[str, str]] = []
        for entity in entities:
            graph_rows.extend(self.graph_retriever.fetch_relations(entity, limit=20))

        context = self.prompt_builder.build_context(top_results, top_k=self.settings.retrieval_top_k)
        graph_context = self.prompt_builder.build_graph_context(graph_rows)

        # Le filtre spoiler est present pour extension future (pas encore applique finement ici).
        _ = spoiler_limit_arc

        answer = self.generator.generate_answer(
            question=question,
            context=context,
            graph_context=graph_context,
        )

        confidence = 0.0
        if top_results:
            confidence = sum(row.final_score for row in top_results) / len(top_results)
            confidence = max(0.0, min(1.0, confidence))

        return AskResponse(
            answer=answer,
            sources=self._sources_from_results(top_results),
            entities=entities,
            confidence=confidence,
        )

    def ask_stream(self, question: str, spoiler_limit_arc: str | None = None) -> Generator[str, None, None]:
        """Execute le pipeline RAG et yield des evenements SSE.

        Format SSE emis:
            event: metadata\\ndata: {sources, entities, confidence}\\n\\n
            event: token\\ndata: {text: "..."}\\n\\n   (repete)
            event: done\\ndata: {}\\n\\n
        """
        retriever = self._get_retriever()
        entities = self.entity_extractor.extract(question)
        retrieval_results = retriever.retrieve(
            question=question,
            entities=entities,
            top_k=max(self.settings.retrieval_top_k * 3, self.settings.retrieval_top_k),
        )
        reranked = self.reranker.rerank(retrieval_results)
        top_results = reranked[: self.settings.retrieval_top_k]

        graph_rows: list[dict[str, str]] = []
        for entity in entities:
            graph_rows.extend(self.graph_retriever.fetch_relations(entity, limit=20))

        context = self.prompt_builder.build_context(top_results, top_k=self.settings.retrieval_top_k)
        graph_context = self.prompt_builder.build_graph_context(graph_rows)

        _ = spoiler_limit_arc

        confidence = 0.0
        if top_results:
            confidence = sum(row.final_score for row in top_results) / len(top_results)
            confidence = max(0.0, min(1.0, confidence))

        sources = [
            {"entity_name": r.entity_name, "section": r.section, "source_url": r.source_url, "score": r.final_score}
            for r in top_results
        ]
        metadata_payload = json.dumps({"sources": sources, "entities": entities, "confidence": confidence})
        yield f"event: metadata\ndata: {metadata_payload}\n\n"

        for token in self.generator.generate_answer_stream(question, context, graph_context):
            yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"

        yield "event: done\ndata: {}\n\n"

    def get_entity(self, entity_name: str) -> dict | None:
        """Retourne la fiche entite depuis data/raw et le graphe."""
        slug = self._slugify(entity_name)
        direct_path = self.settings.raw_data_dir / f"{slug}.json"

        payload = None
        if direct_path.exists():
            payload = json.loads(direct_path.read_text(encoding="utf-8"))
        else:
            for path in sorted(self.settings.raw_data_dir.glob("*.json")):
                candidate = json.loads(path.read_text(encoding="utf-8"))
                if str(candidate.get("title", "")).lower() == entity_name.lower():
                    payload = candidate
                    break

        if payload is None:
            return None

        relations = self.graph_retriever.fetch_relations(payload["title"], limit=50)
        return {
            "name": payload["title"],
            "type": payload.get("type", "unknown"),
            "infobox": payload.get("infobox", {}),
            "relations": relations,
        }

    def get_graph(self, entity_name: str, depth: int = 2) -> dict[str, list[dict[str, str]]]:
        """Retourne un sous-graphe autour d'une entite."""
        return self.graph_retriever.fetch_subgraph(entity_name, depth=depth, limit=100)

    def search(self, query: str, entity_type: str | None = None) -> list[RetrievalResult]:
        """Expose la recherche hybride brute pour /api/search."""
        retriever = self._get_retriever()
        results = retriever.retrieve(
            question=query,
            entities=self.entity_extractor.extract(query),
            filter_type=entity_type,
            top_k=max(self.settings.retrieval_top_k * 3, self.settings.retrieval_top_k),
        )
        reranked = self.reranker.rerank(results)
        return reranked[: self.settings.retrieval_top_k]

    def health(self) -> dict[str, int | str]:
        """Retourne l'etat de sante applicatif."""
        chunks_count = 0
        chunks_path = self.settings.chunk_data_dir / "chunks_with_embeddings.jsonl"
        if chunks_path.exists():
            with chunks_path.open("r", encoding="utf-8") as handle:
                chunks_count = sum(1 for _ in handle)
        graph_nodes = 0

        if self.settings.neo4j_uri and self.settings.neo4j_user and self.settings.neo4j_password:
            builder = GraphBuilder(self.settings)
            try:
                graph_nodes = builder.get_counts()["nodes"]
            except Exception:
                graph_nodes = 0
            finally:
                builder.close()

        return {
            "status": "ok",
            "chunks_count": chunks_count,
            "graph_nodes": graph_nodes,
        }


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """Retourne un singleton de service RAG."""
    settings = get_settings()
    return RAGService(settings)


def get_health_snapshot(settings: Settings | None = None) -> dict[str, int | str]:
    """Construit un etat de sante sans initialiser le pipeline RAG complet."""
    settings = settings or get_settings()

    chunks_count = 0
    chunks_path = settings.chunk_data_dir / "chunks_with_embeddings.jsonl"
    if chunks_path.exists():
        with chunks_path.open("r", encoding="utf-8") as handle:
            chunks_count = sum(1 for _ in handle)

    graph_nodes = 0
    if settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password:
        builder = GraphBuilder(settings)
        try:
            graph_nodes = builder.get_counts()["nodes"]
        except Exception:
            graph_nodes = 0
        finally:
            builder.close()

    return {
        "status": "ok",
        "chunks_count": chunks_count,
        "graph_nodes": graph_nodes,
    }
