"""Tests pour le pipeline SSE de ask_stream."""

from __future__ import annotations

import json
from collections.abc import Generator
from unittest.mock import MagicMock, patch

from src.api.dependencies import RAGService
from src.config.settings import Settings


def _make_service() -> RAGService:
    """Cree un RAGService avec des settings minimaux (sans DB ni LLM reels)."""
    settings = Settings(
        supabase_url=None,
        supabase_key=None,
        neo4j_uri=None,
        neo4j_user=None,
        neo4j_password=None,
        groq_api_key=None,
    )
    return RAGService(settings)


def _collect_sse(gen: Generator[str, None, None]) -> list[tuple[str, dict]]:
    """Parse un generateur SSE en liste de (event_name, data)."""
    events = []
    buffer = ""
    for chunk in gen:
        buffer += chunk
        while "\n\n" in buffer:
            part, buffer = buffer.split("\n\n", 1)
            lines = part.strip().splitlines()
            event_name = None
            data_raw = None
            for line in lines:
                if line.startswith("event: "):
                    event_name = line[len("event: "):]
                elif line.startswith("data: "):
                    data_raw = line[len("data: "):]
            if event_name and data_raw:
                events.append((event_name, json.loads(data_raw)))
    return events


def test_ask_stream_event_order():
    """Le stream doit emettre metadata -> token(s) -> done dans le bon ordre."""
    service = _make_service()

    # Mock retriever, reranker, graph_retriever et generator
    mock_retrieval_result = MagicMock()
    mock_retrieval_result.entity_name = "Luffy"
    mock_retrieval_result.section = "abilities"
    mock_retrieval_result.source_url = "https://example.com"
    mock_retrieval_result.final_score = 0.9
    mock_retrieval_result.entity_type = "character"
    mock_retrieval_result.content = "Luffy a le Gomu Gomu no Mi."

    service._retriever = MagicMock()
    service._retriever.retrieve.return_value = [mock_retrieval_result]
    service.reranker = MagicMock()
    service.reranker.rerank.return_value = [mock_retrieval_result]
    service.graph_retriever = MagicMock()
    service.graph_retriever.fetch_relations.return_value = []
    service.generator = MagicMock()
    service.generator.generate_answer_stream.return_value = iter(["Le ", "Gomu ", "Gomu."])

    events = _collect_sse(service.ask_stream("Quel est le fruit de Luffy ?"))

    event_names = [e[0] for e in events]
    assert event_names[0] == "metadata"
    assert "token" in event_names
    assert event_names[-1] == "done"


def test_ask_stream_metadata_fields():
    """L'event metadata contient sources, entities et confidence."""
    service = _make_service()

    mock_result = MagicMock()
    mock_result.entity_name = "Trafalgar Law"
    mock_result.section = "abilities"
    mock_result.source_url = "https://example.com/law"
    mock_result.final_score = 0.85
    mock_result.entity_type = "character"
    mock_result.content = "Law possede l'Ope Ope no Mi."

    service._retriever = MagicMock()
    service._retriever.retrieve.return_value = [mock_result]
    service.reranker = MagicMock()
    service.reranker.rerank.return_value = [mock_result]
    service.graph_retriever = MagicMock()
    service.graph_retriever.fetch_relations.return_value = []
    service.generator = MagicMock()
    service.generator.generate_answer_stream.return_value = iter(["Ope Ope no Mi."])

    events = _collect_sse(service.ask_stream("Fruit de Law ?"))
    metadata = next(data for name, data in events if name == "metadata")

    assert "sources" in metadata
    assert "entities" in metadata
    assert "confidence" in metadata
    assert isinstance(metadata["confidence"], float)


def test_ask_stream_tokens_concatenate_to_answer():
    """Les tokens concatenes doivent reconstituer la reponse complete."""
    service = _make_service()

    mock_result = MagicMock()
    mock_result.entity_name = "Zoro"
    mock_result.section = "history"
    mock_result.source_url = "https://example.com/zoro"
    mock_result.final_score = 0.8
    mock_result.entity_type = "character"
    mock_result.content = "Zoro est le bras droit de Luffy."

    service._retriever = MagicMock()
    service._retriever.retrieve.return_value = [mock_result]
    service.reranker = MagicMock()
    service.reranker.rerank.return_value = [mock_result]
    service.graph_retriever = MagicMock()
    service.graph_retriever.fetch_relations.return_value = []
    service.generator = MagicMock()
    service.generator.generate_answer_stream.return_value = iter(["Zoro ", "est ", "le ", "bras ", "droit."])

    events = _collect_sse(service.ask_stream("Qui est Zoro ?"))
    tokens = [data["text"] for name, data in events if name == "token"]
    assert "".join(tokens) == "Zoro est le bras droit."


def test_ask_stream_passes_history_to_generator():
    """L'historique est bien transmis au generator."""
    service = _make_service()

    mock_result = MagicMock()
    mock_result.entity_name = "Nami"
    mock_result.section = "history"
    mock_result.source_url = "https://example.com/nami"
    mock_result.final_score = 0.75
    mock_result.entity_type = "character"
    mock_result.content = "Nami est la navigatrice."

    service._retriever = MagicMock()
    service._retriever.retrieve.return_value = [mock_result]
    service.reranker = MagicMock()
    service.reranker.rerank.return_value = [mock_result]
    service.graph_retriever = MagicMock()
    service.graph_retriever.fetch_relations.return_value = []
    service.generator = MagicMock()
    service.generator.generate_answer_stream.return_value = iter(["Nami."])

    history = [
        {"role": "user", "content": "Qui est Luffy ?"},
        {"role": "assistant", "content": "Le capitaine des Straw Hats."},
    ]
    list(_collect_sse(service.ask_stream("Et Nami ?", history=history)))

    service.generator.generate_answer_stream.assert_called_once()
    call_kwargs = service.generator.generate_answer_stream.call_args
    passed_history = call_kwargs.kwargs.get("history") or call_kwargs.args[3] if len(call_kwargs.args) > 3 else call_kwargs.kwargs.get("history")
    assert passed_history == history
