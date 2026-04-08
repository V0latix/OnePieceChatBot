"""Orchestrateur Phase 1: scraping Fandom -> JSON structures."""

from __future__ import annotations

import argparse
import re
from collections import OrderedDict

from config.settings import get_settings
from scraper.categorizer import PageCategorizer
from scraper.cleaner import WikitextCleaner
from scraper.exporter import JsonExporter, ScrapedPageDocument
from scraper.fandom_spider import FandomSpider
from utils.logger import configure_logging, get_logger

SEED_CATEGORIES = [
    "Category:Characters",
    "Category:Devil_Fruits",
    "Category:Pirate_Crews",
    "Category:Marine",
    "Category:World_Government",
    "Category:Story_Arcs",
    "Category:Locations",
    "Category:Fighting_Styles",
    "Category:Objects",
    "Category:Races",
    "Category:Events",
]


def slugify_title(title: str) -> str:
    """Normalise un titre wiki vers un id fichier local."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", title.strip().lower()).strip("_")


def collect_seed_titles(spider: FandomSpider, max_pages: int) -> list[str]:
    """Construit une file de titres unique a partir des categories seeds."""
    titles: OrderedDict[str, None] = OrderedDict()
    per_category = max(5, max_pages)

    for category in SEED_CATEGORIES:
        category_titles = spider.fetch_category_members(category, max_pages=per_category)
        for title in category_titles:
            if title in spider.completed_titles:
                continue
            titles[title] = None
            if len(titles) >= max_pages:
                return list(titles.keys())
    return list(titles.keys())


def main() -> None:
    """Point d'entree CLI de la phase scraping."""
    parser = argparse.ArgumentParser(description="Scrape One Piece Fandom via API MediaWiki")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="Nombre max de pages a traiter (subset de validation par defaut)",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    spider = FandomSpider(settings)
    cleaner = WikitextCleaner()
    categorizer = PageCategorizer()
    exporter = JsonExporter(settings.raw_data_dir)
    existing_ids = {path.stem for path in settings.raw_data_dir.glob("*.json")}

    titles = collect_seed_titles(spider, max_pages=args.max_pages)
    logger.info("Demarrage scraping subset: %s pages candidates", len(titles))

    success = 0
    failed = 0

    try:
        for index, title in enumerate(titles, start=1):
            logger.info("[%s/%s] Scraping %s", index, len(titles), title)
            try:
                if slugify_title(title) in existing_ids:
                    spider.mark_completed(title)
                    logger.info("SKIP %s (fichier deja present)", title)
                    continue

                raw_page = spider.scrape_page(title)
                cleaned = cleaner.clean_page(
                    title=raw_page.title,
                    url=raw_page.url,
                    categories=raw_page.categories,
                    wikitext=raw_page.wikitext,
                )
                entity_type = categorizer.detect_entity_type(
                    title=cleaned.title,
                    categories=cleaned.categories,
                    infobox=cleaned.infobox,
                )
                document = ScrapedPageDocument(
                    id=cleaned.id,
                    title=cleaned.title,
                    url=cleaned.url,
                    type=entity_type,
                    categories=cleaned.categories,
                    infobox=cleaned.infobox,
                    sections=cleaned.sections,
                    related_entities=cleaned.related_entities,
                    last_scraped=cleaned.last_scraped.isoformat(),
                )
                output_path = exporter.export(document)
                existing_ids.add(cleaned.id)
                spider.mark_completed(title)
                success += 1
                logger.info("OK %s -> %s", title, output_path)
            except Exception as exc:  # pylint: disable=broad-except
                failed += 1
                spider.mark_failed(title)
                logger.error("ECHEC %s: %s", title, exc)
    finally:
        spider.close()

    logger.info("Termine. success=%s failed=%s", success, failed)


if __name__ == "__main__":
    main()
