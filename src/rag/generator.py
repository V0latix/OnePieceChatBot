"""Generation de reponse via Groq avec fallback Ollama."""

from __future__ import annotations

import httpx
from groq import Groq

from src.config.settings import Settings
from src.rag.prompt_builder import PromptBuilder


class AnswerGenerator:
    """Client de generation avec strategie de fallback."""

    def __init__(self, settings: Settings, prompt_builder: PromptBuilder) -> None:
        self.settings = settings
        self.prompt_builder = prompt_builder

    def _generate_with_groq(self, messages: list[dict[str, str]]) -> str:
        if not self.settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY absent")

        client = Groq(api_key=self.settings.groq_api_key)
        completion = client.chat.completions.create(
            model=self.settings.llm_model,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )
        return completion.choices[0].message.content or ""

    def _generate_with_ollama(self, messages: list[dict[str, str]]) -> str:
        response = httpx.post(
            f"{self.settings.ollama_base_url}/api/chat",
            json={
                "model": "llama3.1:8b",
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.3},
            },
            timeout=120.0,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("message", {}).get("content", "")

    def _fallback_from_context(self, context: str) -> str:
        """Retourne une reponse minimale quand aucun LLM n'est joignable."""
        stripped = context.strip()
        if not stripped:
            return "Je n'ai pas trouve cette information dans ma base de donnees."

        first_block = stripped.split("\n\n", maxsplit=1)[0]
        snippet = first_block[:700].strip()
        return (
            "Je n'ai pas pu joindre le LLM (Groq/Ollama). Voici le meilleur contexte retrouve:\n\n"
            f"{snippet}"
        )

    def generate_answer(self, question: str, context: str, graph_context: str) -> str:
        """Genere la reponse finale en essayant Groq puis Ollama."""
        messages = self.prompt_builder.build_messages(question, context, graph_context)

        try:
            return self._generate_with_groq(messages)
        except Exception:
            try:
                return self._generate_with_ollama(messages)
            except Exception:
                return self._fallback_from_context(context)
