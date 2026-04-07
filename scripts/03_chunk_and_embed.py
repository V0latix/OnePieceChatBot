"""Phase 2: chunking + embeddings + upload optionnel Supabase."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config.settings import get_settings
from src.processing.chunker import DocumentChunker
from src.processing.embedder import EmbeddingGenerator
from src.processing.vector_store import SupabaseVectorStore
from src.scraper.exporter import JsonExporter
from src.utils.logger import configure_logging, get_logger


def load_documents(raw_dir: Path) -> list:
    """Charge les documents JSON valides depuis data/raw."""
    exporter = JsonExporter(raw_dir)
    documents = []
    for file_path in sorted(raw_dir.glob("*.json")):
        documents.append(exporter.load(file_path))
    return documents


def main() -> None:
    """Point d'entree CLI du pipeline de vectorisation."""
    parser = argparse.ArgumentParser(description="Chunk, embed, and optionally upload to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Ne fait pas l'upload Supabase")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    documents = load_documents(settings.raw_data_dir)
    if not documents:
        logger.warning("Aucun document dans data/raw. Lance d'abord scripts/01_scrape.py")
        return

    chunker = DocumentChunker(settings)
    chunks = chunker.chunk_documents(documents)
    logger.info("Chunks generes: %s", len(chunks))

    chunks_path = settings.chunk_data_dir / "chunks.jsonl"
    chunker.save_chunks_jsonl(chunks, chunks_path)
    logger.info("Chunks sauves: %s", chunks_path)

    embedder = EmbeddingGenerator(settings.embedding_model)
    embeddings = embedder.embed_texts([chunk.content for chunk in chunks])

    embeddings_path = settings.chunk_data_dir / "chunks_with_embeddings.jsonl"
    with embeddings_path.open("w", encoding="utf-8") as handle:
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            payload = chunk.model_dump(mode="json")
            payload["embedding"] = embedding
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")
    logger.info("Chunks + embeddings sauves: %s", embeddings_path)

    if args.dry_run:
        logger.info("Dry-run actif: pas d'upload Supabase")
        return

    if not (settings.supabase_url and settings.supabase_key):
        logger.warning("SUPABASE_URL/SUPABASE_KEY absents: upload ignore")
        return

    store = SupabaseVectorStore(settings.supabase_url, settings.supabase_key)
    store.upsert_chunks(chunks, embeddings)
    logger.info("Upload Supabase termine (%s chunks)", len(chunks))


if __name__ == "__main__":
    main()
