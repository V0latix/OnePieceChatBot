"""Upload Qdrant depuis chunks_with_embeddings.jsonl (sans recalcul d'embeddings).

Utile quand le cluster Qdrant a ete recree mais que les embeddings locaux sont
deja calcules: on evite ainsi de re-embed les 36k chunks (~2h).
"""

from __future__ import annotations

import json

from config.settings import get_settings
from processing.chunker import ChunkRecord
from processing.vector_store import QdrantVectorStore
from utils.logger import configure_logging, get_logger


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    path = settings.chunk_data_dir / "chunks_with_embeddings.jsonl"
    if not path.exists():
        logger.error("Fichier introuvable: %s", path)
        return

    if not (settings.qdrant_url and settings.qdrant_api_key):
        logger.error("QDRANT_URL/QDRANT_API_KEY absents")
        return

    chunks: list[ChunkRecord] = []
    embeddings: list[list[float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            embeddings.append(payload.pop("embedding"))
            chunks.append(ChunkRecord.model_validate(payload))

    logger.info("Chunks charges depuis JSONL: %s", len(chunks))

    store = QdrantVectorStore(
        settings.qdrant_url, settings.qdrant_api_key, settings.qdrant_collection
    )
    store.upsert_chunks(chunks, embeddings)
    logger.info("Upload Qdrant termine (%s chunks)", len(chunks))


if __name__ == "__main__":
    main()
