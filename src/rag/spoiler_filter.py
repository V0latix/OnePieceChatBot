"""Filtre anti-spoiler : exclut les chunks dont l'arc est posterieur a la limite choisie.

Semantique fail-closed : quand un arc limite est actif, seuls les chunks dont la section
est explicitement identifiee comme anterieure ou egale a l'arc limite sont conserves.
Les sections "history.*" non reconnues sont exclues (elles peuvent contenir des spoilers).
Les sections non-histoire (overview, abilities, personality, site_navigation, etc.) sont
toujours conservees car elles decrivent des traits permanents, pas des evenements d'arc.
"""

from __future__ import annotations

from rag.retriever import RetrievalResult


# Ordre chronologique des arcs One Piece.
# Les mots-cles correspondent aux patterns trouves dans le champ `section` des chunks
# (ex: "history.marineford_arc" -> keyword "marineford").
_ARC_ORDER: list[tuple[str, list[str]]] = [
    ("East Blue",         ["romance_dawn", "orange_town", "syrup_village", "baratie", "arlong_park", "loguetown", "east_blue"]),
    ("Alabasta",          ["reverse_mountain", "whisky_peak", "little_garden", "drum_island", "alabasta"]),
    ("Skypiea",           ["jaya", "skypiea", "sky_island"]),
    ("Enies Lobby",       ["long_ring", "water_7", "enies_lobby", "post_enies"]),
    ("Thriller Bark",     ["thriller_bark"]),
    ("Sabaody",           ["sabaody", "amazon_lily", "impel_down", "straw_hat_separation"]),
    ("Marineford",        ["marineford", "post_war", "post_marineford"]),
    ("Fishman Island",    ["fishman_island", "fish_man_island"]),
    ("Punk Hazard",       ["punk_hazard"]),
    ("Dressrosa",         ["dressrosa", "green_bit"]),
    ("Zou",               ["zou_arc", "zou"]),
    ("Whole Cake Island", ["whole_cake", "totto_land"]),
    ("Wano",              ["wano_country", "wano"]),
    ("Egghead",           ["egghead", "final_saga", "egghead_arc"]),
]

# Sections non-histoire : toujours sures (ne revelent pas d'evenements d'arc)
_SAFE_SECTION_PREFIXES: tuple[str, ...] = (
    "overview",
    "personality",
    "appearance",
    "abilities",
    "relationships",
    "site_navigation",
    "gallery",
    "trivia",
    "infobox",
    "categories",
    "etymology",
    "creation",
    "merchandise",
    "references",
    "external",
    "navigation",
    "misc",
)

# Mapping nom d'arc (tel qu'affiche dans le frontend) -> index chronologique
_ARC_NAME_TO_INDEX: dict[str, int] = {name: i for i, (name, _) in enumerate(_ARC_ORDER)}

# Mapping keyword de section -> index chronologique
_KEYWORD_TO_INDEX: dict[str, int] = {}
for _idx, (_arc_name, _keywords) in enumerate(_ARC_ORDER):
    for _kw in _keywords:
        _KEYWORD_TO_INDEX[_kw] = _idx


def _is_safe_section(section: str) -> bool:
    """Retourne True si la section est non-histoire (toujours conservee)."""
    s = section.lower()
    return any(s == prefix or s.startswith(prefix + ".") or s.startswith(prefix + "_")
               for prefix in _SAFE_SECTION_PREFIXES)


def _arc_index_from_section(section: str) -> int | None:
    """Extrait l'index chronologique d'un arc a partir du nom de section.

    Retourne None si aucun arc connu n'est trouve dans la section.
    """
    normalized = section.lower().replace("-", "_")
    for keyword, index in _KEYWORD_TO_INDEX.items():
        if keyword in normalized:
            return index
    return None


def arc_limit_index(spoiler_limit_arc: str) -> int | None:
    """Retourne l'index chronologique de l'arc limite, ou None si non reconnu / 'Aucun'."""
    if not spoiler_limit_arc or spoiler_limit_arc.strip().lower() in ("aucun", "none", ""):
        return None
    return _ARC_NAME_TO_INDEX.get(spoiler_limit_arc)


def filter_by_spoiler_limit(
    results: list[RetrievalResult],
    spoiler_limit_arc: str | None,
) -> list[RetrievalResult]:
    """Filtre les resultats pour ne garder que les chunks anterieurs ou egaux a l'arc limite.

    Comportement fail-closed quand un arc limite est actif :
    - Sections non-histoire (overview, abilities, etc.) : toujours conservees.
    - Sections histoire avec arc identifie <= limite : conservees.
    - Sections histoire avec arc identifie > limite : exclues (spoiler).
    - Sections history.* dont l'arc n'est pas reconnu : exclues (precaution spoiler).
    - Si `spoiler_limit_arc` est None / "Aucun" : aucun filtre.
    """
    if not spoiler_limit_arc:
        return results

    limit_idx = arc_limit_index(spoiler_limit_arc)
    if limit_idx is None:
        # Arc limite non reconnu → aucun filtre
        return results

    filtered: list[RetrievalResult] = []
    for result in results:
        section = result.section.lower()

        # 1. Sections non-histoire : toujours sures
        if _is_safe_section(section):
            filtered.append(result)
            continue

        # 2. Sections histoire : verifier l'arc
        chunk_arc_idx = _arc_index_from_section(section)
        if chunk_arc_idx is not None and chunk_arc_idx <= limit_idx:
            filtered.append(result)
        # else: arc non reconnu ou > limite → exclu (fail-closed)

    return filtered
