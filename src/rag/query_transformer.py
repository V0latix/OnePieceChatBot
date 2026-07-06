"""Query transformation HyDE (Hypothetical Document Embeddings).

Les questions sont en francais, le corpus + le modele d'embedding (bge-large-en)
sont en anglais. HyDE genere une reponse hypothetique en anglais et embarque
CELLE-CI pour la recherche dense, comblant l'ecart cross-lingue.
"""

from __future__ import annotations

from typing import Any

from utils.logger import get_logger

_logger = get_logger(__name__)

_HYDE_SYSTEM = (
    "You are a One Piece expert. Given a question (possibly in French), write a "
    "concise, factual English passage (2-3 sentences) that would plausibly answer it. "
    "Output ONLY the passage, no preamble."
)


class QueryTransformer:
    """Transforme la question avant retrieval. Reutilise le client Groq du generator."""

    def __init__(self, generator: Any) -> None:
        self.generator = generator

    def hyde(self, question: str) -> str:
        """Retourne un passage hypothetique anglais, ou "" si le LLM echoue."""
        messages = [
            {"role": "system", "content": _HYDE_SYSTEM},
            {"role": "user", "content": question},
        ]
        try:
            return (self.generator._generate_with_groq(messages) or "").strip()
        except Exception as exc:  # noqa: BLE001 - degradation gracieuse -> question brute
            _logger.warning("HyDE indisponible (%s): fallback sur la question brute", exc)
            return ""
