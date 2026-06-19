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
    r"^(Volume|Episode|Chapter|SBS|Forum:|File:|Category:|Template:|User:|Talk:|Thread:|One Py)",
    re.IGNORECASE,
)


def is_noise_section(section: str) -> bool:
    return section in NOISE_SECTIONS


def is_noise_entity(entity_name: str) -> bool:
    """Vrai si la page est non-canonique (sous-page Gallery/Misc., volume, SBS...)."""
    if "/" in entity_name:  # sous-pages: "Roronoa Zoro/Gallery", ".../Misc."
        return True
    return bool(NOISE_TITLE_RE.match(entity_name.strip()))
