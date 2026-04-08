"""Smoke test de l'assemblage prompt/reponses."""

from __future__ import annotations

from rag.prompt_builder import PromptBuilder
from rag.retriever import RetrievalResult


def test_prompt_builder_formats_context_and_graph() -> None:
    builder = PromptBuilder()
    results = [
        RetrievalResult(
            chunk_id="luffy__001",
            entity_name="Monkey D. Luffy",
            entity_type="character",
            section="abilities",
            content="Luffy maitrise le Gear 5.",
            source_url="https://onepiece.fandom.com/wiki/Monkey_D._Luffy",
            vector_score=0.9,
            keyword_score=0.5,
            graph_score=1.0,
            final_score=0.86,
        )
    ]
    relations = [
        {
            "source": "Monkey D. Luffy",
            "relation": "MEMBER_OF",
            "target": "Straw Hat Pirates",
        }
    ]

    context = builder.build_context(results)
    graph_context = builder.build_graph_context(relations)

    assert "Monkey D. Luffy" in context
    assert "MEMBER_OF" in graph_context
