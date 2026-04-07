"""Generation de reponse via Groq avec fallback Ollama."""

from __future__ import annotations

import json
from collections.abc import Generator

import httpx
from groq import Groq

from src.config.settings import Settings
from src.rag.prompt_builder import PromptBuilder
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

# Timeouts LLM
_GROQ_TIMEOUT = 30.0
_OLLAMA_TIMEOUT = 120.0


class AnswerGenerator:
    """Client de generation avec strategie de fallback et circuit breakers."""

    def __init__(self, settings: Settings, prompt_builder: PromptBuilder) -> None:
        self.settings = settings
        self.prompt_builder = prompt_builder
        self._cb_groq = CircuitBreaker("groq", failure_threshold=3, recovery_timeout=60.0)
        self._cb_ollama = CircuitBreaker("ollama", failure_threshold=3, recovery_timeout=30.0)

    def _generate_with_groq(self, messages: list[dict[str, str]]) -> str:
        if not self.settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY absent")

        self._cb_groq.before_call()
        try:
            client = Groq(api_key=self.settings.groq_api_key, timeout=_GROQ_TIMEOUT)
            completion = client.chat.completions.create(
                model=self.settings.groq_model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            result = completion.choices[0].message.content or ""
            self._cb_groq.on_success()
            return result
        except CircuitBreakerOpen:
            raise
        except Exception as exc:
            self._cb_groq.on_failure()
            raise exc

    def _stream_with_groq(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        """Yield des tokens depuis Groq en mode streaming."""
        if not self.settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY absent")

        self._cb_groq.before_call()
        try:
            client = Groq(api_key=self.settings.groq_api_key, timeout=_GROQ_TIMEOUT)
            stream = client.chat.completions.create(
                model=self.settings.groq_model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
                stream=True,
            )
            for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    yield token
            self._cb_groq.on_success()
        except CircuitBreakerOpen:
            raise
        except Exception as exc:
            self._cb_groq.on_failure()
            raise exc

    def _generate_with_ollama(self, messages: list[dict[str, str]]) -> str:
        self._cb_ollama.before_call()
        model_name = self.settings.ollama_model or self.settings.llm_model or "llama3.1:8b"
        try:
            response = httpx.post(
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=_OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            result = response.json().get("message", {}).get("content", "")
            self._cb_ollama.on_success()
            return result
        except CircuitBreakerOpen:
            raise
        except Exception as exc:
            self._cb_ollama.on_failure()
            raise exc

    def _stream_with_ollama(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        """Yield des tokens depuis Ollama en mode streaming (NDJSON)."""
        self._cb_ollama.before_call()
        model_name = self.settings.ollama_model or self.settings.llm_model or "llama3.1:8b"
        try:
            with httpx.stream(
                "POST",
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": model_name,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.3},
                },
                timeout=_OLLAMA_TIMEOUT,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
            self._cb_ollama.on_success()
        except CircuitBreakerOpen:
            raise
        except Exception as exc:
            self._cb_ollama.on_failure()
            raise exc

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

    def generate_answer_stream(
        self, question: str, context: str, graph_context: str
    ) -> Generator[str, None, None]:
        """Yield des tokens en essayant Groq streaming puis Ollama streaming."""
        messages = self.prompt_builder.build_messages(question, context, graph_context)

        try:
            yield from self._stream_with_groq(messages)
            return
        except Exception:
            pass

        try:
            yield from self._stream_with_ollama(messages)
            return
        except Exception:
            pass

        # Fallback snippet : simuler un stream mot par mot
        fallback = self._fallback_from_context(context)
        for word in fallback.split(" "):
            yield word + " "
