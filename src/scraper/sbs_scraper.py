"""Scraper des SBS (Questions/Reponses d'Oda)."""

from __future__ import annotations

from typing import Any

import httpx

from src.config.settings import Settings
from src.utils.logger import get_logger


class SBSScraper:
    """Client minimal pour collecter des pages SBS."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__)

    def fetch_page_html(self, url: str) -> str:
        """Recupere le HTML d'une page SBS."""
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> dict[str, Any]:
        """Parse minimal: laisse la place a une extraction plus fine ulterieure."""
        return {"raw_html": html}
