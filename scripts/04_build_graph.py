"""Phase 3: construit le knowledge graph Neo4j depuis data/raw."""

from __future__ import annotations

import argparse

from src.config.settings import get_settings
from src.processing.graph_builder import GraphBuilder
from src.scraper.exporter import JsonExporter
from src.utils.logger import configure_logging, get_logger


def main() -> None:
    """Point d'entree CLI du build de graphe."""
    parser = argparse.ArgumentParser(description="Build Neo4j graph from scraped documents")
    parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    if not (settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password):
        logger.error("NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD manquants")
        return

    exporter = JsonExporter(settings.raw_data_dir)
    documents = [exporter.load(path) for path in sorted(settings.raw_data_dir.glob("*.json"))]
    if not documents:
        logger.warning("Aucun document source dans data/raw")
        return

    builder = GraphBuilder(settings)
    try:
        extracted_triplets, inserted_relations = builder.build_from_documents(documents)
        counts = builder.get_counts()
        logger.info(
            "Graph build termine. triplets=%s relations_upsert=%s nodes=%s edges=%s",
            extracted_triplets,
            inserted_relations,
            counts["nodes"],
            counts["edges"],
        )
    finally:
        builder.close()


if __name__ == "__main__":
    main()
