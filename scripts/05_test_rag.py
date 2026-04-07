"""Phase 4: test manuel du pipeline RAG complet."""

from __future__ import annotations

import argparse

from src.config.settings import get_settings
from src.processing.embedder import EmbeddingGenerator
from src.processing.vector_store import SupabaseVectorStore
from src.rag.entity_extractor import EntityExtractor
from src.rag.generator import AnswerGenerator
from src.rag.graph_retriever import GraphRetriever
from src.rag.prompt_builder import PromptBuilder
from src.rag.reranker import WeightedReranker
from src.rag.retriever import HybridRetriever
from src.utils.logger import configure_logging, get_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an end-to-end RAG query")
    parser.add_argument("--question", required=True, help="Question utilisateur")
    parser.add_argument("--filter-type", default=None, help="Filtre entity_type optionnel")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    entity_extractor = EntityExtractor.from_raw_documents(settings.raw_data_dir)
    embedder = EmbeddingGenerator(settings.embedding_model)

    vector_store = None
    if settings.supabase_url and settings.supabase_key:
        vector_store = SupabaseVectorStore(settings.supabase_url, settings.supabase_key)

    retriever = HybridRetriever(
        settings=settings,
        embedder=embedder,
        vector_store=vector_store,
    )
    reranker = WeightedReranker()
    graph_retriever = GraphRetriever(settings)
    prompt_builder = PromptBuilder()
    generator = AnswerGenerator(settings, prompt_builder)

    entities = entity_extractor.extract(args.question)
    logger.info("Entites detectees: %s", entities)

    results = retriever.retrieve(
        question=args.question,
        entities=entities,
        filter_type=args.filter_type,
        top_k=max(settings.retrieval_top_k * 3, settings.retrieval_top_k),
    )
    reranked = reranker.rerank(results)
    top_results = reranked[: settings.retrieval_top_k]

    graph_rows = []
    for entity in entities:
        graph_rows.extend(graph_retriever.fetch_relations(entity, limit=20))

    context = prompt_builder.build_context(top_results, top_k=settings.retrieval_top_k)
    graph_context = prompt_builder.build_graph_context(graph_rows)

    answer = generator.generate_answer(
        question=args.question,
        context=context,
        graph_context=graph_context,
    )

    logger.info("\n=== REPONSE ===\n%s", answer)
    logger.info("\n=== SOURCES ===")
    for row in top_results:
        logger.info("- %s | %s | %s", row.entity_name, row.section, row.source_url)


if __name__ == "__main__":
    main()
