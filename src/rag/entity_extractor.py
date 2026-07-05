"""Extraction d'entites nommees One Piece depuis la question utilisateur."""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from rag.noise import is_alias_stopword, is_noise_entity


_NORMALIZE_RE = re.compile(r"[^a-z0-9\s]")


class EntityExtractor:
    """Extractor rule-based base sur un dictionnaire d'entites connues."""

    def __init__(self, entities: list[str], importance: dict[str, int] | None = None) -> None:
        self.entities = list(dict.fromkeys(entity.strip() for entity in entities if entity.strip()))
        # Prior d'importance (ex: nb de related_entities) pour arbitrer les collisions
        # d'alias : "luffy" -> "Monkey D. Luffy" (145) plutot que "Nightmare Luffy" (1).
        self._importance = importance or {}
        self._alias_to_entity = self._build_alias_map(self.entities)

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = _NORMALIZE_RE.sub(" ", text.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _assign(self, alias_map: dict[str, str], alias: str, entity: str) -> None:
        """Pose alias->entity, en gardant l'entite la plus importante en cas de collision."""
        existing = alias_map.get(alias)
        if existing is None or self._importance.get(entity, 0) > self._importance.get(existing, 0):
            alias_map[alias] = entity

    def _build_alias_map(self, entities: list[str]) -> dict[str, str]:
        alias_map: dict[str, str] = {}
        # Passe 1 : titres complets normalises (cles canoniques, jamais ecrasees par un alias court).
        for entity in entities:
            self._assign(alias_map, self._normalize(entity), entity)

        # Passe 2 : alias courts + forme compacte, arbitres par l'importance.
        for entity in entities:
            normalized = self._normalize(entity)

            words = [word for word in normalized.split(" ") if len(word) >= 4]
            if words and not is_alias_stopword(words[-1]):
                self._assign(alias_map, words[-1], entity)

            # Alias court utile pour les questions naturelles (ex: "Law", "Zoro").
            # On exclut les mots trop generiques ("who" -> "Who's-Who") qui polluent
            # le retrieval et les signaux graphe.
            all_words = [word for word in normalized.split(" ") if word]
            if all_words and len(all_words[-1]) >= 3 and not is_alias_stopword(all_words[-1]):
                self._assign(alias_map, all_words[-1], entity)

            compact = normalized.replace(" ", "")
            if len(compact) >= 6:
                self._assign(alias_map, compact, entity)
        return alias_map

    @classmethod
    def from_raw_documents(cls, raw_dir: Path) -> "EntityExtractor":
        """Construit l'extractor depuis les JSON de data/raw."""
        entities: list[str] = []
        importance: dict[str, int] = {}
        for path in sorted(raw_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            title = payload.get("title")
            # Exclut les pages non-canoniques (Volume/SBS/Forum/Gallery...) pour
            # eviter que "Zoro" resolve vers "Volume Zoro" lors d'une collision d'alias.
            if isinstance(title, str) and not is_noise_entity(title):
                entities.append(title)
                # Prior d'importance = nb de related_entities (les pages canoniques des
                # personnages principaux en ont des centaines, les pages filler ~1).
                importance[title] = len(payload.get("related_entities", []) or [])
        return cls(entities, importance=importance)

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

        # Repli fuzzy : rattrape les fautes de frappe / alias approchants
        # ("Zorro" -> "Roronoa Zoro") quand le matching exact n'a rien trouve.
        # ponytail: difflib stdlib, O(tokens x aliases) ; passer a rapidfuzz si
        # ca apparait au profiling. Cutoff 0.8 = pas assez pour une substitution
        # sur un nom <=4 lettres (ex. "Zolo"/"Zoro" = 0.75) mais evite les faux
        # positifs ; ne se declenche que si le matching exact n'a rien donne.
        if not matches:
            alias_keys = list(self._alias_to_entity.keys())
            for token in normalized_question.split(" "):
                if len(token) < 4 or is_alias_stopword(token):
                    continue
                close = difflib.get_close_matches(token, alias_keys, n=1, cutoff=0.8)
                if close:
                    matches.append(self._alias_to_entity[close[0]])

        deduped = list(dict.fromkeys(matches))
        # Tri stable par importance decroissante : le cap max_entities garde les
        # entites canoniques plutot que des collisions residuelles.
        deduped.sort(key=lambda entity: self._importance.get(entity, 0), reverse=True)
        return deduped[:max_entities]
