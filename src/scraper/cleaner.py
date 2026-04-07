"""Nettoyage du wikitext Fandom vers JSON structure."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


_REFERENCE_RE = re.compile(r"\[\d+\]")
_REF_TAG_RE = re.compile(r"<ref[^>/]*/>|<ref[^>]*>.*?</ref>", re.IGNORECASE | re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$")
_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")
_TEMPLATE_SIMPLE_RE = re.compile(r"\{\{[^{}]*\}\}")
_CATEGORY_LINK_RE = re.compile(r"\[\[(?:Category|File|Image):[^\]]+\]\]", re.IGNORECASE)


class CleanedPage(BaseModel):
    """Donnee nettoyee prete pour categorisation et export."""

    id: str
    title: str
    url: str
    categories: list[str] = Field(default_factory=list)
    infobox: dict[str, str] = Field(default_factory=dict)
    sections: dict[str, Any] = Field(default_factory=dict)
    related_entities: list[str] = Field(default_factory=list)
    last_scraped: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WikitextCleaner:
    """Nettoyeur principal pour pages One Piece."""

    def __init__(self) -> None:
        self._alias_map = {
            "Luffy": "Monkey D. Luffy",
            "Zoro": "Roronoa Zoro",
            "Nami": "Nami",
            "Sanji": "Vinsmoke Sanji",
            "Usopp": "Usopp",
            "Chopper": "Tony Tony Chopper",
            "Robin": "Nico Robin",
            "Franky": "Franky",
            "Brook": "Brook",
            "Jinbe": "Jinbe",
        }

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
        return normalized.strip("_")

    def normalize_entity_name(self, name: str) -> str:
        """Normalise les alias frequents One Piece."""
        stripped = name.strip()
        return self._alias_map.get(stripped, stripped)

    def _remove_templates(self, text: str) -> str:
        """Supprime les templates simples de type {{...}}."""
        previous = None
        current = text
        while previous != current:
            previous = current
            current = _TEMPLATE_SIMPLE_RE.sub(" ", current)
        return current

    def _replace_links(self, text: str) -> str:
        """Convertit les liens MediaWiki en texte lisible."""

        def replacer(match: re.Match[str]) -> str:
            target = match.group(1) or ""
            label = match.group(2)
            base = (label or target).replace("_", " ")
            return base

        return _LINK_RE.sub(replacer, text)

    def clean_text(self, raw_text: str) -> str:
        """Nettoie le wikitext en texte brut."""
        cleaned = _CATEGORY_LINK_RE.sub(" ", raw_text)
        cleaned = _REF_TAG_RE.sub(" ", cleaned)
        cleaned = _REFERENCE_RE.sub(" ", cleaned)
        cleaned = self._remove_templates(cleaned)
        cleaned = self._replace_links(cleaned)
        cleaned = cleaned.replace("'''", "").replace("''", "")
        cleaned = _HTML_TAG_RE.sub(" ", cleaned)
        cleaned = re.sub(r"\[https?://[^\s\]]+(?:\s+[^\]]+)?\]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def extract_infobox(self, wikitext: str) -> dict[str, str]:
        """Extrait un infobox depuis le template {{Infobox ...}}."""
        start = wikitext.find("{{Infobox")
        if start == -1:
            return {}

        depth = 0
        end = -1
        i = start
        while i < len(wikitext) - 1:
            token = wikitext[i : i + 2]
            if token == "{{":
                depth += 1
                i += 2
                continue
            if token == "}}":
                depth -= 1
                i += 2
                if depth <= 0:
                    end = i
                    break
                continue
            i += 1

        if end == -1:
            return {}

        block = wikitext[start:end]
        infobox: dict[str, str] = {}
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("|") or "=" not in line:
                continue
            key_raw, value_raw = line[1:].split("=", 1)
            key = self._slugify(key_raw)
            value = self.clean_text(value_raw)
            if key and value:
                infobox[key] = value
        return infobox

    def split_sections(self, wikitext: str) -> dict[str, Any]:
        """Separe le contenu en sections, avec support de sous-sections."""
        sections: dict[str, Any] = {}

        current_main: str | None = None
        current_sub: str | None = None

        for line in wikitext.splitlines():
            heading_match = _HEADING_RE.match(line.strip())
            if heading_match:
                level = len(heading_match.group(1))
                heading = self._slugify(heading_match.group(2))
                if not heading:
                    continue

                if level == 2:
                    current_main = heading
                    current_sub = None
                    sections.setdefault(current_main, "")
                elif level >= 3 and current_main:
                    current_sub = heading
                    if not isinstance(sections.get(current_main), dict):
                        sections[current_main] = {}
                    sections[current_main].setdefault(current_sub, "")
                continue

            if current_main is None:
                sections.setdefault("overview", "")
                sections["overview"] += f"\n{line}"
                continue

            if current_sub and isinstance(sections.get(current_main), dict):
                sections[current_main][current_sub] += f"\n{line}"
            elif isinstance(sections.get(current_main), str):
                sections[current_main] += f"\n{line}"

        normalized: dict[str, Any] = {}
        for key, value in sections.items():
            if isinstance(value, dict):
                normalized[key] = {
                    sub_key: self.clean_text(sub_value)
                    for sub_key, sub_value in value.items()
                    if self.clean_text(sub_value)
                }
                if not normalized[key]:
                    normalized.pop(key, None)
            else:
                cleaned_value = self.clean_text(value)
                if cleaned_value:
                    normalized[key] = cleaned_value

        return normalized

    def extract_related_entities(self, wikitext: str) -> list[str]:
        """Extrait les entites mentionnees via liens internes."""
        entities: list[str] = []
        for match in _LINK_RE.finditer(wikitext):
            target = match.group(1) or ""
            if not target or ":" in target:
                continue
            name = target.replace("_", " ").strip()
            if not name:
                continue
            entities.append(self.normalize_entity_name(name))

        deduplicated = list(dict.fromkeys(entities))
        return deduplicated

    def clean_page(
        self,
        title: str,
        url: str,
        categories: list[str],
        wikitext: str,
    ) -> CleanedPage:
        """Pipeline complet de nettoyage d'une page brute."""
        normalized_title = self.normalize_entity_name(title)
        page_id = self._slugify(normalized_title)
        cleaned = CleanedPage(
            id=page_id,
            title=normalized_title,
            url=url,
            categories=categories,
            infobox=self.extract_infobox(wikitext),
            sections=self.split_sections(wikitext),
            related_entities=self.extract_related_entities(wikitext),
        )
        return cleaned
