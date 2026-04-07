"""Export JSON strict des pages nettoyees."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScrapedPageDocument(BaseModel):
    """Schema final d'une page scrapee."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    url: str
    type: str
    categories: list[str] = Field(default_factory=list)
    infobox: dict[str, str] = Field(default_factory=dict)
    sections: dict[str, Any] = Field(default_factory=dict)
    related_entities: list[str] = Field(default_factory=list)
    last_scraped: str


class JsonExporter:
    """Exporte les documents dans `data/raw` en UTF-8 strict."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, document: ScrapedPageDocument) -> Path:
        """Valide et ecrit un document JSON sur disque."""
        payload = document.model_dump(mode="json")
        file_path = self.output_dir / f"{document.id}.json"
        file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return file_path

    def load(self, file_path: Path) -> ScrapedPageDocument:
        """Charge un document valide depuis disque."""
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        return ScrapedPageDocument.model_validate(raw)
