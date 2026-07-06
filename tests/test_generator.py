"""Tests de la chaine de fallback du generateur (Groq -> Ollama -> snippet)."""

from __future__ import annotations

from config.settings import get_settings
from rag.generator import AnswerGenerator
from rag.prompt_builder import PromptBuilder


def _gen() -> AnswerGenerator:
    return AnswerGenerator(get_settings(), PromptBuilder())


def _boom(_messages):  # noqa: ANN001, ANN202
    raise RuntimeError("LLM indisponible")


def test_generate_answer_uses_groq_when_available() -> None:
    gen = _gen()
    gen._generate_with_groq = lambda _m: "REPONSE GROQ"
    assert gen.generate_answer("Q", "contexte", "graphe") == "REPONSE GROQ"


def test_generate_answer_falls_back_to_ollama() -> None:
    gen = _gen()
    gen._generate_with_groq = _boom
    gen._generate_with_ollama = lambda _m: "REPONSE OLLAMA"
    assert gen.generate_answer("Q", "contexte", "graphe") == "REPONSE OLLAMA"


def test_generate_answer_falls_back_to_context_snippet() -> None:
    gen = _gen()
    gen._generate_with_groq = _boom
    gen._generate_with_ollama = _boom
    out = gen.generate_answer("Q", "Luffy est le capitaine.", "graphe")
    assert out.startswith("Je n'ai pas pu joindre le LLM")
    assert "Luffy est le capitaine." in out


def test_fallback_from_context_empty_context() -> None:
    gen = _gen()
    assert gen._fallback_from_context("") == "Je n'ai pas trouve cette information dans ma base de donnees."


def test_fallback_from_context_returns_first_block() -> None:
    gen = _gen()
    out = gen._fallback_from_context("Premier bloc pertinent.\n\nSecond bloc ignore.")
    assert "Premier bloc pertinent." in out
    assert "Second bloc ignore." not in out


def test_generate_answer_stream_falls_back_word_by_word() -> None:
    gen = _gen()
    gen._stream_with_groq = _boom
    gen._stream_with_ollama = _boom
    tokens = list(gen.generate_answer_stream("Q", "Zoro manie trois sabres.", "graphe"))
    text = "".join(tokens)
    assert "Zoro manie trois sabres." in text
    assert len(tokens) > 1  # bien un stream mot par mot, pas un seul bloc
