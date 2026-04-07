"""Classification automatique des pages One Piece."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryRule:
    """Regle de mapping entre mot-cle categorie et type cible."""

    keyword: str
    entity_type: str


class PageCategorizer:
    """Categorise une page sur la base des categories et de l'infobox."""

    def __init__(self) -> None:
        self._rules = [
            CategoryRule("characters", "character"),
            CategoryRule("pirate crews", "crew"),
            CategoryRule("marine", "organization"),
            CategoryRule("world government", "organization"),
            CategoryRule("devil fruits", "devil_fruit"),
            CategoryRule("story arcs", "arc"),
            CategoryRule("locations", "location"),
            CategoryRule("fighting styles", "technique"),
            CategoryRule("races", "race"),
            CategoryRule("events", "event"),
            CategoryRule("objects", "object"),
        ]

    def detect_entity_type(
        self,
        title: str,
        categories: list[str],
        infobox: dict[str, str] | None = None,
    ) -> str:
        """Retourne le type d'entite le plus probable."""
        lowered_categories = " ".join(category.lower() for category in categories)

        for rule in self._rules:
            if rule.keyword in lowered_categories:
                return rule.entity_type

        infobox = infobox or {}
        infobox_keys = " ".join(infobox.keys()).lower()
        if "bounty" in infobox_keys or "epithet" in infobox_keys:
            return "character"
        if "devil_fruit" in infobox_keys:
            return "character"
        if "captain" in infobox_keys and "ship" in infobox_keys:
            return "crew"

        title_lower = title.lower()
        if "arc" in title_lower:
            return "arc"
        if "haki" in title_lower or "gear" in title_lower:
            return "technique"

        return "unknown"
