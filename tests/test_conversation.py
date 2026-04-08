"""Tests pour l'injection de l'historique conversationnel dans le prompt."""

from __future__ import annotations

from rag.prompt_builder import PromptBuilder


def _make_builder() -> PromptBuilder:
    return PromptBuilder()


def test_build_messages_without_history():
    """Sans historique, le resultat contient system + user uniquement."""
    builder = _make_builder()
    msgs = builder.build_messages("Qui est Luffy ?", "contexte", "graphe")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "Qui est Luffy ?"


def test_build_messages_with_history():
    """L'historique est insere entre system et la question courante."""
    builder = _make_builder()
    history = [
        {"role": "user", "content": "Quel est le fruit de Luffy ?"},
        {"role": "assistant", "content": "Le Gomu Gomu no Mi."},
    ]
    msgs = builder.build_messages("Et celui de Law ?", "contexte", "graphe", history=history)
    assert msgs[0]["role"] == "system"
    assert msgs[1] == {"role": "user", "content": "Quel est le fruit de Luffy ?"}
    assert msgs[2] == {"role": "assistant", "content": "Le Gomu Gomu no Mi."}
    assert msgs[3] == {"role": "user", "content": "Et celui de Law ?"}


def test_build_messages_history_capped_at_6():
    """L'historique est tronque aux 6 derniers messages (3 echanges)."""
    builder = _make_builder()
    # 10 messages d'historique
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(10)]
    msgs = builder.build_messages("Question finale", "contexte", "graphe", history=history)
    # system + 6 historique + question = 8
    assert len(msgs) == 8
    assert msgs[1]["content"] == "msg 4"   # premier des 6 derniers
    assert msgs[-1]["content"] == "Question finale"


def test_build_messages_empty_history_list():
    """Une liste vide est equivalente a None."""
    builder = _make_builder()
    msgs_none = builder.build_messages("Q", "ctx", "graph", history=None)
    msgs_empty = builder.build_messages("Q", "ctx", "graph", history=[])
    assert len(msgs_none) == len(msgs_empty) == 2


def test_system_prompt_contains_context():
    """Le system prompt integre le contexte et le graphe."""
    builder = _make_builder()
    msgs = builder.build_messages("Q", "MON_CONTEXTE", "MON_GRAPHE")
    system_content = msgs[0]["content"]
    assert "MON_CONTEXTE" in system_content
    assert "MON_GRAPHE" in system_content
