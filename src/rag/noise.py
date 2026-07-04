"""Filtres de bruit partages entre le retriever et l'entity extractor.

Le wiki Fandom contient beaucoup de pages/sections non-canoniques (menus de
navigation, volumes, SBS, forums, galeries) qui polluent a la fois le retrieval
ET la resolution d'entites. Centraliser ces filtres ici garantit que les deux
etages voient le meme univers de pages valides.
"""

from __future__ import annotations

import re

# Sections de pur bruit (menus, liens externes, meta) — ~7.6% des chunks.
NOISE_SECTIONS = frozenset(
    {
        "site_navigation",
        "external_links",
        "references",
        "author_s_note",
        "contents",
    }
)

# Prefixes de pages non-canoniques (volumes, episodes, SBS, forums, namespaces).
# Ces pages matchent des mots-cles ("Volume Zoro", "SBS Volume 44") mais ne sont
# jamais l'entite recherchee.
NOISE_TITLE_RE = re.compile(
    r"^("
    r"Volume|Episode|Chapter|SBS|Forum:|File:|Category:|Template:|User:|Talk:|Thread:"
    r"|One Py|One Piece Magazine|One Piece Great|Boss Luffy"  # media / merch / fillers
    r"|\d+(st|nd|rd|th) Branch"                                # stubs de branches Marine
    r")",
    re.IGNORECASE,
)

# Pages glossaire/liste : matchent une foule de mots-cles (elles listent des noms,
# epithetes, variantes) et remontent en tete sur des questions sans rapport.
# Ce ne sont jamais la reponse a une question sur une entite precise.
NOISE_TITLES = frozenset(
    {
        "Name Variants",
        "Epithet",
        "Name Variations",
        "List of Canon Characters",
        "Glossary",
    }
)


# Mots trop generiques pour servir d'alias court d'entite. Sans ce filtre,
# "Who's-Who" (normalise "who s who") cree l'alias "who" et capture la question
# "Who is Luffy?". On bloque la CREATION d'alias, pas le matching : les vrais noms
# courts non-stopwords (Law, Ace) restent intacts.
ALIAS_STOPWORDS = frozenset(
    {
        # Interrogatifs / articles / copules EN
        "who", "what", "where", "when", "which", "why", "how", "whose", "whom",
        "the", "an", "of", "is", "are", "was", "were", "and", "or", "to", "in",
        "on", "at", "by", "for", "with", "from", "his", "her", "its", "their",
        # Interrogatifs / articles FR
        "qui", "quoi", "quel", "quelle", "quels", "quelles", "est", "les", "des",
        "une", "dans", "sur", "avec", "pour", "son", "sor", "leur",
        # Termes One Piece trop generiques (collisions frequentes)
        "one", "piece", "king", "sea", "pirate", "pirates", "crew", "fruit",
        "devil", "island", "captain", "marine", "marines", "story", "name",
    }
)


# Categories non-canoniques (produits derives, jeux, chansons, publications,
# monde reel). Ces pages ne repondent jamais a une question de lore et polluent
# le retrieval en matchant sur les mots-cles. Filtrage par sous-chaine sur les
# categories Fandom (ex: "Mobile_Games", "Music_Stubs", "Merchandise").
NOISE_CATEGORY_SUBSTRINGS = frozenset(
    {
        "merchandise",
        "game",  # Mobile_Games, Video_Games, Console_Games
        "song",
        "music",
        "magazine",
        "real_world",
        "popularity_poll",
        "voice_actor",
        "4kids",
    }
)


def is_noise_categories(categories: list[str]) -> bool:
    """Vrai si une categorie indique une page non-canonique (merch/jeu/media)."""
    for category in categories:
        low = category.lower()
        if any(token in low for token in NOISE_CATEGORY_SUBSTRINGS):
            return True
    return False


def is_alias_stopword(word: str) -> bool:
    """Vrai si le mot est trop generique pour servir d'alias court d'entite."""
    return word.strip().lower() in ALIAS_STOPWORDS


def is_noise_section(section: str) -> bool:
    return section in NOISE_SECTIONS


def is_noise_entity(entity_name: str) -> bool:
    """Vrai si la page est non-canonique (sous-page Gallery/Misc., volume, SBS...)."""
    name = entity_name.strip()
    if "/" in name:  # sous-pages: "Roronoa Zoro/Gallery", ".../Misc."
        return True
    if name in NOISE_TITLES:
        return True
    return bool(NOISE_TITLE_RE.match(name))
