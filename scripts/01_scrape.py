"""Orchestrateur Phase 1: scraping Fandom -> JSON structures."""

from __future__ import annotations

import argparse
import re
import time
from collections import OrderedDict

from config.settings import get_settings
from scraper.categorizer import PageCategorizer
from scraper.cleaner import WikitextCleaner
from scraper.exporter import JsonExporter, ScrapedPageDocument
from scraper.fandom_spider import FandomSpider
from utils.logger import configure_logging, get_logger

SEED_CATEGORIES = [
    # Personnages (sources principales — ~1300 pages uniques)
    "Category:Male_Characters",              # 1043 pages
    "Category:Female_Characters",            # 290 pages
    # Groupes & organisations
    "Category:Pirate_Captains",              # 108 pages
    "Category:Organizations",               # ~10 pages
    # Pouvoirs & capacites
    "Category:Paramecia_Devil_Fruit_Users",  # 102 pages
    "Category:Zoan_Devil_Fruit_Users",       # ~60 pages
    "Category:Logia_Devil_Fruit_Users",      # ~20 pages
    "Category:Observation_Haki_Users",       # 128 pages
    "Category:Haki_Users",                  # ~20 pages
    # Lore
    "Category:Story_Arcs",                  # arcs narratifs
    "Category:Fighting_Styles",             # styles de combat
    "Category:Devil_Fruits",                # fruits du demon (taxonomie)
    "Category:Events",                      # evenements canon
]


def slugify_title(title: str) -> str:
    """Normalise un titre wiki vers un id fichier local."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", title.strip().lower()).strip("_")


def collect_seed_titles(
    spider: FandomSpider,
    max_pages: int,
    existing_ids: set[str],
) -> list[str]:
    """Construit une file de titres uniques non encore traites.

    Filtre sur DEUX criteres pour etre robuste meme si etat et disque divergent :
    - titres dans completed_titles (etat persiste)
    - titres dont le fichier JSON existe deja sur disque (existing_ids)
    """
    from utils.logger import get_logger
    logger = get_logger(__name__)

    titles: OrderedDict[str, None] = OrderedDict()
    completed = spider.completed_titles
    logger.info("Etat: %s titres deja traites", len(completed))

    # Recupere assez de candidats pour trouver max_pages nouveaux titres meme
    # si la majorite de la categorie est deja scraped.
    per_category = min(max(1_000, max_pages * 3 if max_pages else 5_000), 5_000)

    for category in SEED_CATEGORIES:
        before = len(titles)
        category_titles = spider.fetch_category_members(category, max_pages=per_category)
        skipped = 0
        for title in category_titles:
            if title in completed or slugify_title(title) in existing_ids:
                skipped += 1
                continue
            titles[title] = None
            if 0 < max_pages <= len(titles):
                logger.info("Categorie %s: %s nouveaux (+%s skipped)", category, len(titles) - before, skipped)
                return list(titles.keys())
        logger.info(
            "Categorie %s: %s membres API, %s skipped, %s nouveaux",
            category, len(category_titles), skipped, len(titles) - before,
        )

    return list(titles.keys())


def main() -> None:
    """Point d'entree CLI de la phase scraping."""
    parser = argparse.ArgumentParser(description="Scrape One Piece Fandom via API MediaWiki")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Nombre max de pages a traiter (0 = illimite)",
    )
    parser.add_argument(
        "--time-limit",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Duree max en secondes (0 = illimitee). Ex: --time-limit 1800 pour 30 min.",
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
    existing_ids.discard("scrape_state")  # exclure le fichier d'etat lui-meme

    titles = collect_seed_titles(spider, max_pages=args.max_pages, existing_ids=existing_ids)
    logger.info("Demarrage scraping: %s pages candidates a traiter", len(titles))
    if not titles:
        logger.info("Aucune nouvelle page trouvee — scraping complet ou categories epuisees.")
        spider.close()
        return

    deadline = time.monotonic() + args.time_limit if args.time_limit > 0 else None
    if deadline:
        logger.info("Time limit: %s secondes", args.time_limit)

    success = 0
    failed = 0

    try:
        for index, title in enumerate(titles, start=1):
            if deadline and time.monotonic() >= deadline:
                logger.info("Time limit atteint apres %s pages. Arret propre.", index - 1)
                break
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
