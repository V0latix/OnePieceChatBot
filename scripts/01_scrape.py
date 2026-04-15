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
    # ── Personnages ──────────────────────────────────────────
    "Category:Male_Characters",                    # 1043 pages
    "Category:Female_Characters",                  # 290 pages
    "Category:Deceased_Characters",                # 127 pages
    "Category:Swordsmen",                          # 238 pages
    "Category:Giants",                             # 44 pages
    "Category:Pets",                               # 57 pages
    "Category:Human_Hybrids",                      # 25 pages
    "Category:Unknown_Appearance_Characters",      # 20 pages
    # ── Groupes & equipages ───────────────────────────────────
    "Category:Pirate_Captains",                    # 108 pages
    "Category:Roger_Pirates",                      # 33 pages
    "Category:Whitebeard_Pirates'_Subordinates",   # 44 pages
    "Category:Big_Mom_Pirates_Officers",           # 70 pages
    "Category:Big_Mom_Pirates",                    # 20 pages
    "Category:Kid_Pirates",                        # 22 pages
    "Category:Spade_Pirates",                      # 20 pages
    "Category:Ninja-Pirate-Mink-Samurai_Alliance", # 31 pages
    "Category:Kuja",                               # 22 pages
    "Category:Organizations",                      # organisations mondiales
    "Category:Underworld_Organizations",           # 26 pages
    # ── Antagonistes par saga ────────────────────────────────
    "Category:East_Blue_Saga_Antagonists",         # 24 pages
    "Category:Water_7_Saga_Antagonists",           # 73 pages
    "Category:Summit_War_Saga_Antagonists",        # 70 pages
    "Category:Wano_Country_Saga_Antagonists",      # 107 pages
    "Category:Final_Saga_Antagonists",             # 35 pages
    # ── Marines ──────────────────────────────────────────────
    "Category:Marine_Vice_Admirals",               # 33 pages
    "Category:Marineford_Residents",               # 31 pages
    "Category:New_Marineford_Residents",           # 24 pages
    "Category:Kings",                              # 31 pages
    "Category:Samurai",                            # 20 pages
    "Category:Undercover_Operators",               # 24 pages
    "Category:Snipers",                            # 24 pages
    "Category:Martial_Artists",                    # 40 pages
    # ── Fruits du Demon ──────────────────────────────────────
    "Category:Shown_Devil_Fruits",                 # 40 pages (pages des fruits eux-memes)
    "Category:Paramecia",                          # 93 pages
    "Category:Zoan",                               # 25 pages
    "Category:Paramecia_Devil_Fruit_Users",        # 102 pages
    "Category:Zoan_Devil_Fruit_Users",             # ~60 pages
    "Category:Logia_Devil_Fruit_Users",            # ~20 pages
    "Category:Gifters",                            # 44 pages (Zoan de Wano)
    # ── Pouvoirs & styles de combat ─────────────────────────
    "Category:Observation_Haki_Users",             # 128 pages
    "Category:Haki_Users",                         # complementaire
    "Category:Fighting_Styles",                    # 43 pages
    "Category:Fighters_Who_Use_Animals",           # 24 pages
    # ── Armes & objets ───────────────────────────────────────
    "Category:Swords",                             # 40 pages
    "Category:Famous_Blades",                      # 30 pages
    # ── Lieux ────────────────────────────────────────────────
    "Category:Towns_and_Cities",                   # 25 pages
    "Category:Paradise_Islands",                   # 23 pages
    "Category:New_World_Islands",                  # 20 pages
    "Category:New_World_Locations",                # 20 pages
    "Category:Sabaody_Archipelago_Residents",      # 25 pages
    "Category:West_Blue_Residents",                # 40 pages
    "Category:South_Blue_Residents",               # 38 pages
    "Category:East_Blue_Residents",                # 35 pages
    # ── Races ────────────────────────────────────────────────
    "Category:Races_and_Tribes",                   # 24 pages
    # ── Equipages principaux ─────────────────────────────────
    "Category:Straw_Hat_Pirates",                  # Equipage de Luffy
    "Category:Heart_Pirates",                      # Equipage de Law
    "Category:Blackbeard_Pirates",                 # Equipage de Barbe Noire
    "Category:Red-Haired_Pirates",                 # Equipage de Shanks
    "Category:Beasts_Pirates",                     # Equipage de Kaido
    "Category:Donquixote_Pirates",                 # Equipage de Doflamingo
    "Category:Baroque_Works",                      # Organisation de Crocodile
    "Category:Revolutionary_Army",                 # Armee de Dragon
    "Category:Seven_Warlords_of_the_Sea",          # Shichibukai
    "Category:Worst_Generation",                   # Supernovas
    "Category:Cipher_Pol",                         # CP0/CP9 agents
    "Category:World_Government",                   # Gouvernement mondial
    "Category:Rocks_Pirates",                      # Equipage de Rocks D. Xebec
    "Category:Sun_Pirates",                        # Equipage de Fisher Tiger
    "Category:Foxy_Pirates",                       # Equipage de Foxy
    "Category:Thriller_Bark_Residents",            # Equipage de Moria
    # ── Races & especes ──────────────────────────────────────
    "Category:Fish-Men",                           # Hommes-poissons
    "Category:Dwarves",                            # Nains / Tontatta
    "Category:Lunarians",                          # Lunarians (race de King)
    "Category:Skypieans",                          # Habitants du ciel
    "Category:Shandians",                          # Guerriers de Skypiea
    "Category:Birkans",                            # Habitants de Birka
    "Category:Cyborgs",                            # Cyborgs (Franky, Kuma...)
    "Category:Zombies",                            # Zombies de Thriller Bark
    # ── Pouvoirs (suite) ─────────────────────────────────────
    "Category:Armament_Haki_Users",                # Utilisateurs Haki d'armement
    "Category:Ancient_Zoan_Devil_Fruit_Users",     # Zoan anciens
    "Category:SMILE_Devil_Fruit_Users",            # Utilisateurs SMILE
    "Category:Rokushiki_Users",                    # Utilisateurs Rokushiki
    "Category:Devil_Fruit_Awakening_Users",        # Awakening
    # ── Lieux (suite) ────────────────────────────────────────
    "Category:Sky_Islands",                        # Iles celestes
    "Category:Wano_Country_Residents",             # Habitants de Wano
    "Category:Water_7_Residents",                  # Habitants de Water 7
    "Category:Alabasta_Residents",                 # Habitants d'Alabasta
    "Category:Sabaody_Archipelago",                # Archipel de Sabaody
    "Category:Marineford",                         # Marinford
    # ── Bateaux, arcs & divers ───────────────────────────────
    "Category:Ships",                              # 21 pages
    "Category:Story_Arcs",                         # 34 pages
    "Category:Events",                             # evenements canon
    "Category:Terms",                              # 41 pages (termes de lore)
    "Category:Occupations",                        # 25 pages
    "Category:Devil_Fruits",                       # taxonomie
    # ── Personnages (suite) ──────────────────────────────────
    "Category:Humans",                             # 1046 pages
    "Category:Flashback_Introduction_Characters",  # 197 pages
    "Category:Children",                           # 72 pages
    "Category:Cover_Story_Introduction_Characters",# 60 pages
    "Category:Animals",                            # 43 pages
    "Category:Merfolk",                            # 30 pages
    "Category:Mink_Tribe",                         # 27 pages
    "Category:Former_Pirates",                     # 35 pages
    "Category:Supreme_King_Haki_Users",            # 30 pages
    "Category:Doctors",                            # 26 pages
    "Category:Assassins",                          # 24 pages
    "Category:Former_Marine_Prisoners",            # 23 pages
    "Category:Mentioned_Only_Characters",          # 18 pages
    "Category:SBS_Characters",                     # 18 pages
    "Category:Deities",                            # 17 pages
    "Category:Mythical_Zoan_Devil_Fruit_Users",    # 23 pages
    "Category:Multiple_Characters_Articles",       # 25 pages
    "Category:Toys",                               # 23 pages
    "Category:Former_Rulers",                      # 22 pages
    "Category:Shipwrights",                        # 19 pages
    "Category:Foosha_Village_Characters",          # 18 pages
    "Category:Fighters_Who_Use_Technology",        # 17 pages
    "Category:New_World_Residents",                # 17 pages
    "Category:Kouzuki_Family_Subordinates",        # 19 pages
    "Category:Donquixote_Pirates_Slaves",          # 20 pages
    "Category:Whole_Cake_Island_Residents",        # 23 pages
    "Category:Dressrosa_Residents",                # 29 pages
    "Category:Elbaph_Residents",                   # 18 pages
    "Category:Zou_Residents",                      # 15 pages
    "Category:Charlotte_Family",                   # 15 pages
    "Category:Former_Foxy_Pirates",                # 18 pages
    "Category:World_Seeker_Characters",            # 33 pages
    # ── Groupes (suite) ──────────────────────────────────────
    "Category:Antagonist_Groups",                  # 66 pages
    "Category:Former_Pirate_Crews",                # 26 pages
    "Category:Former_Organizations",               # 16 pages
    "Category:Marine_Organizations",               # 19 pages
    "Category:Four_Emperors'_Subordinate_Crews",   # 15 pages
    "Category:Flashback_Introduction_Groups",      # 16 pages
    "Category:Former_Marines",                     # 16 pages
    # ── Antagonistes (suite) ─────────────────────────────────
    "Category:Dressrosa_Saga_Antagonists",         # 47 pages
    "Category:Arabasta_Saga_Antagonists",          # 46 pages
    "Category:Flashback_Antagonists",              # 36 pages
    "Category:Cover_Story_Antagonists",            # 29 pages
    "Category:Premier_Show_Antagonists",           # 16 pages
    # ── Armes & combat (suite) ───────────────────────────────
    "Category:Trident_Users",                      # 23 pages
    "Category:Halberd_Users",                      # 21 pages
    "Category:Shield_Users",                       # 21 pages
    "Category:Dagger_Users",                       # 20 pages
    "Category:Lance_Users",                        # 19 pages
    "Category:Bazooka_Users",                      # 17 pages
    "Category:Archers",                            # 16 pages
    "Category:Scythe_Users",                       # 15 pages
    "Category:Polearms",                           # 16 pages
    "Category:Living_Weapons",                     # 19 pages
    "Category:Devil_Fruits_with_Multiple_Users",   # 16 pages
    "Category:Logia",                              # 16 pages
    # ── Lieux (suite) ────────────────────────────────────────
    "Category:Arabasta_Locations",                 # 19 pages
    "Category:East_Blue_Locations",                # 18 pages
    "Category:Flashback_Introduction_Locations",   # 38 pages
    "Category:Cover_Story_Introduction_Locations", # 19 pages
    "Category:Destroyed_Locations",                # 16 pages
    "Category:Bars_and_Restaurants",               # 15 pages
    "Category:Mentioned_Only_Totto_Land_Islands",  # 23 pages
    "Category:Mentioned_Only_World_Government_Kingdoms", # 21 pages
    "Category:World_Government_Kingdoms",          # 17 pages
    # ── Objets & technologie ─────────────────────────────────
    "Category:Technology",                         # 19 pages
    "Category:Artifacts",                          # 15 pages
    "Category:Lists",                              # 50 pages
    "Category:Positions",                          # 15 pages
    # ── Lore & media ─────────────────────────────────────────
    "Category:SBS",                                # 113 pages
    "Category:Cover_Stories",                      # 21 pages
    "Category:Battles",                            # 15 pages
    "Category:Incidents",                          # 15 pages
    "Category:One_Piece_Movies",                   # 16 pages
    "Category:One_Piece_Volumes",                  # 115 pages
    "Category:One_Piece_Magazine",                 # 23 pages
    "Category:Crossovers",                         # 17 pages
    "Category:Character_Galleries",                # 16 pages
    "Category:Special_Volumes",                    # 15 pages
    "Category:Citation_Needed",                    # 101 pages
    "Category:Articles_Without_References",        # 99 pages
    # ── Threads & communaute ─────────────────────────────────
    "Category:Archived_Threads",                   # 839 pages
    "Category:One_Piece_Manga_Threads",            # 331 pages
    "Category:Merchandise",                        # 230 pages
    "Category:One_Piece_Anime_Threads",            # 139 pages
    "Category:Wikia_Appearance_Threads",           # 119 pages
    "Category:One_Piece_Misc_Threads",             # 109 pages
    "Category:Translation_Threads",                # 46 pages
    "Category:One_Piece_International",            # 42 pages
    "Category:Spoilers_Threads",                   # 42 pages
    "Category:User_Rights_Threads",                # 36 pages
    "Category:Users_to_Be_Banned_Threads",         # 30 pages
    "Category:One_Piece_Openings",                 # 28 pages
    "Category:One_Piece_Endings",                  # 26 pages
    "Category:One_Piece_Music",                    # 23 pages
    "Category:One_Piece_Nippon_Judan!_47_Cruise_CD", # 49 pages
    "Category:Movie_Songs",                        # 18 pages
    "Category:Community_Cafe_Threads",             # 17 pages
    "Category:Speedy_Ban_Threads",                 # 17 pages
    "Category:Miscellaneous_Threads",              # 19 pages
    "Category:Chit-Chat_Threads",                  # 15 pages
    "Category:Live_Performances",                  # 16 pages
    "Category:Manga",                              # 16 pages
    "Category:One_Piece_in_Love_Characters",       # 16 pages
    "Category:Pirate_Ships",                       # 15 pages
    "Category:Males",                              # 15 pages
    "Category:Discontinued_Mobile_Games",          # 20 pages
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
