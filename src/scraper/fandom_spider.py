"""Spider base API MediaWiki pour le wiki One Piece Fandom."""

from __future__ import annotations

import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from src.config.settings import Settings
from src.utils.logger import get_logger


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class RawWikiPage(BaseModel):
    """Representation brute d'une page wiki issue de l'API."""

    title: str
    url: str
    wikitext: str
    categories: list[str] = Field(default_factory=list)
    raw_parse: dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime


class ScrapeState(BaseModel):
    """Etat persistant pour reprendre le scraping."""

    completed_titles: list[str] = Field(default_factory=list)
    failed_titles: list[str] = Field(default_factory=list)
    last_updated: datetime | None = None


class FandomSpider:
    """Client resilient pour interroger l'API Fandom avec reprise."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__)
        self._state_path: Path = settings.scrape_state_path
        self._state = self._load_state()

    def _load_state(self) -> ScrapeState:
        """Charge l'etat depuis disque si present."""
        if not self._state_path.exists():
            return ScrapeState()

        raw = self._state_path.read_text(encoding="utf-8")
        if not raw.strip():
            return ScrapeState()
        return ScrapeState.model_validate_json(raw)

    def _save_state(self) -> None:
        """Persiste l'etat courant du scraping."""
        self._state.last_updated = datetime.now(timezone.utc)
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            self._state.model_dump_json(indent=2),
            encoding="utf-8",
        )

    @property
    def completed_titles(self) -> set[str]:
        """Titres deja traites."""
        return set(self._state.completed_titles)

    def mark_completed(self, title: str) -> None:
        """Marque un titre comme traite avec succes."""
        if title not in self._state.completed_titles:
            self._state.completed_titles.append(title)
        if title in self._state.failed_titles:
            self._state.failed_titles.remove(title)
        self._save_state()

    def mark_failed(self, title: str) -> None:
        """Marque un titre en echec."""
        if title not in self._state.failed_titles:
            self._state.failed_titles.append(title)
        self._save_state()

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Envoie une requete API avec retry exponentiel et rate limiting."""
        last_error: Exception | None = None

        for attempt in range(self.settings.scrape_max_retries):
            # Rate limiting volontaire pour respecter Fandom.
            delay = random.uniform(
                self.settings.scrape_request_delay_min,
                self.settings.scrape_request_delay_max,
            )
            time.sleep(delay)

            try:
                response = httpx.get(
                    str(self.settings.fandom_api_base),
                    params=params,
                    timeout=30.0,
                    follow_redirects=True,
                )
                if response.status_code in RETRYABLE_STATUS_CODES:
                    raise httpx.HTTPStatusError(
                        message=f"Retryable status: {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                last_error = exc
                backoff_seconds = min(2**attempt, 30)
                self.logger.warning(
                    "Erreur API Fandom, tentative %s/%s, backoff=%ss, erreur=%s",
                    attempt + 1,
                    self.settings.scrape_max_retries,
                    backoff_seconds,
                    exc,
                )
                time.sleep(backoff_seconds)

        raise RuntimeError(f"Echec API Fandom apres retries: {last_error}")

    def fetch_category_members(self, category: str, max_pages: int = 500) -> list[str]:
        """Retourne les titres de pages pour une categorie donnee."""
        normalized = category if category.startswith("Category:") else f"Category:{category}"
        titles: list[str] = []
        cmcontinue: str | None = None

        while len(titles) < max_pages:
            batch_size = min(500, max_pages - len(titles))
            params: dict[str, Any] = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": normalized,
                "cmlimit": batch_size,
                "cmtype": "page",
                "format": "json",
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue

            payload = self._request(params)
            members = payload.get("query", {}).get("categorymembers", [])
            if not members:
                break

            for item in members:
                title = item.get("title")
                if isinstance(title, str):
                    titles.append(title)

            cmcontinue = payload.get("continue", {}).get("cmcontinue")
            if not cmcontinue:
                break

        unique_titles = list(dict.fromkeys(titles))
        self.logger.info("Categorie %s: %s titres recuperes", normalized, len(unique_titles))
        return unique_titles

    def fetch_page_wikitext(self, title: str) -> str:
        """Recupere le wikitext brut d'une page."""
        payload = self._request(
            {
                "action": "query",
                "titles": title,
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "format": "json",
                "formatversion": 2,
            }
        )

        pages = payload.get("query", {}).get("pages", [])
        if not pages:
            raise ValueError(f"Page absente: {title}")

        revisions = pages[0].get("revisions", [])
        if not revisions:
            raise ValueError(f"Revisions absentes pour: {title}")

        slots = revisions[0].get("slots", {})
        main_slot = slots.get("main", {})
        content = main_slot.get("content")
        if not isinstance(content, str):
            # Fallback ancien format MediaWiki.
            content = revisions[0].get("*")
        if not isinstance(content, str):
            raise ValueError(f"Contenu introuvable pour: {title}")
        return content

    def fetch_page_categories(self, title: str) -> tuple[list[str], dict[str, Any]]:
        """Recupere les categories de la page via parse."""
        payload = self._request(
            {
                "action": "parse",
                "page": title,
                "format": "json",
                "prop": "categories",
            }
        )

        parsed = payload.get("parse", {})
        categories_payload = parsed.get("categories", [])
        categories: list[str] = []
        for category in categories_payload:
            value = category.get("*") if isinstance(category, dict) else None
            if isinstance(value, str):
                categories.append(value)

        return categories, parsed

    def scrape_page(self, title: str) -> RawWikiPage:
        """Scrape une page complete (wikitext + categories)."""
        wikitext = self.fetch_page_wikitext(title)
        categories, raw_parse = self.fetch_page_categories(title)

        url_title = quote(title.replace(" ", "_"), safe="_:.()")
        page = RawWikiPage(
            title=title,
            url=f"https://onepiece.fandom.com/wiki/{url_title}",
            wikitext=wikitext,
            categories=categories,
            raw_parse=raw_parse,
            fetched_at=datetime.now(timezone.utc),
        )
        return page
