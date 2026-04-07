"""Extraction d'entites nommees One Piece depuis la question utilisateur."""

from __future__ import annotations

import json
import re
from pathlib import Path


_NORMALIZE_RE = re.compile(r"[^a-z0-9\s]")


class EntityExtractor:
    """Extractor rule-based base sur un dictionnaire d'entites connues."""

    def __init__(self, entities: list[str]) -> None:
        self.entities = list(dict.fromkeys(entity.strip() for entity in entities if entity.strip()))
        self._alias_to_entity = self._build_alias_map(self.entities)

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = _NORMALIZE_RE.sub(" ", text.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _build_alias_map(self, entities: list[str]) -> dict[str, str]:
        alias_map: dict[str, str] = {}
        for entity in entities:
            normalized = self._normalize(entity)
            alias_map[normalized] = entity

            words = [word for word in normalized.split(" ") if len(word) >= 4]
            if words:
                alias_map[words[-1]] = entity

            compact = normalized.replace(" ", "")
            if len(compact) >= 6:
                alias_map[compact] = entity
        return alias_map

    @classmethod
    def from_raw_documents(cls, raw_dir: Path) -> "EntityExtractor":
        """Construit l'extractor depuis les JSON de data/raw."""
        entities: list[str] = []
        for path in sorted(raw_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            title = payload.get("title")
            if isinstance(title, str):
                entities.append(title)
        return cls(entities)

    def extract(self, question: str, max_entities: int = 5) -> list[str]:
        """Retourne les entites detectees dans la question."""
        normalized_question = self._normalize(question)
        compact_question = normalized_question.replace(" ", "")

        matches: list[str] = []
        for alias, entity in self._alias_to_entity.items():
            if not alias:
                continue
            if f" {alias} " in f" {normalized_question} " or alias == normalized_question:
                matches.append(entity)
                continue
            if alias in compact_question and len(alias) >= 8:
                matches.append(entity)

        deduped = list(dict.fromkeys(matches))
        return deduped[:max_entities]
