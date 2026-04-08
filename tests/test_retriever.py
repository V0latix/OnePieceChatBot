"""Tests unitaires pour le retriever hybride."""

from __future__ import annotations

import json

from config.settings import get_settings
from rag.retriever import HybridRetriever


class DummyEmbedder:
    """Embedder factice deterministe pour les tests."""

    def embed_query(self, _query: str) -> list[float]:
        return [1.0, 0.0]


def test_retriever_uses_local_index_and_scores_keyword(tmp_path) -> None:
    index_path = tmp_path / "chunks_with_embeddings.jsonl"
    rows = [
        {
            "chunk_id": "luffy__001",
            "entity_id": "luffy",
            "entity_name": "Monkey D. Luffy",
            "entity_type": "character",
            "section": "abilities",
            "content": "Luffy utilise Gear 5 et le Haki des rois.",
            "categories": ["Characters"],
            "related_entities": ["Kaido"],
            "token_count": 15,
            "source_url": "https://onepiece.fandom.com/wiki/Monkey_D._Luffy",
            "embedding": [1.0, 0.0],
        },
        {
            "chunk_id": "zoro__001",
            "entity_id": "zoro",
            "entity_name": "Roronoa Zoro",
            "entity_type": "character",
            "section": "abilities",
            "content": "Zoro maitrise le Santoryu.",
            "categories": ["Characters"],
            "related_entities": ["Mihawk"],
            "token_count": 8,
            "source_url": "https://onepiece.fandom.com/wiki/Roronoa_Zoro",
            "embedding": [0.0, 1.0],
        },
    ]
    with index_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")

    retriever = HybridRetriever(
        settings=get_settings(),
        embedder=DummyEmbedder(),
        vector_store=None,
        local_embeddings_path=index_path,
    )

    results = retriever.retrieve("Que sait faire Luffy avec son haki ?", entities=["Monkey D. Luffy"], top_k=5)

    assert results
    top = max(results, key=lambda row: row.vector_score)
    assert top.entity_name == "Monkey D. Luffy"
    assert any(row.keyword_score > 0 for row in results)
