"""Tests complets du filtre anti-spoiler (fail-closed semantics)."""

from __future__ import annotations

import pytest

from rag.retriever import RetrievalResult
from rag.spoiler_filter import (
    _arc_index_from_section,
    _is_safe_section,
    arc_limit_index,
    filter_by_spoiler_limit,
)


def _result(section: str, entity: str = "X") -> RetrievalResult:
    return RetrievalResult(
        chunk_id=f"{entity}__{section}",
        entity_name=entity,
        entity_type="character",
        section=section,
        content="...",
        source_url="",
        final_score=0.5,
    )


# ---------------------------------------------------------------------------
# arc_limit_index
# ---------------------------------------------------------------------------

class TestArcLimitIndex:
    def test_aucun_returns_none(self):
        assert arc_limit_index("Aucun") is None

    def test_empty_returns_none(self):
        assert arc_limit_index("") is None

    def test_none_returns_none(self):
        assert arc_limit_index(None) is None  # type: ignore[arg-type]

    def test_known_arcs_have_correct_order(self):
        east_blue = arc_limit_index("East Blue")
        alabasta = arc_limit_index("Alabasta")
        marineford = arc_limit_index("Marineford")
        wano = arc_limit_index("Wano")
        assert east_blue < alabasta < marineford < wano

    def test_unknown_arc_returns_none(self):
        assert arc_limit_index("Arc Inconnu") is None


# ---------------------------------------------------------------------------
# _arc_index_from_section
# ---------------------------------------------------------------------------

class TestArcIndexFromSection:
    def test_marineford_section(self):
        idx = _arc_index_from_section("history.marineford_arc")
        assert idx == arc_limit_index("Marineford")

    def test_wano_section(self):
        idx = _arc_index_from_section("history.wano_country_arc")
        assert idx == arc_limit_index("Wano")

    def test_alabasta_section(self):
        idx = _arc_index_from_section("history.alabasta_arc")
        assert idx == arc_limit_index("Alabasta")

    def test_unknown_section_returns_none(self):
        assert _arc_index_from_section("history.flashback_childhood") is None

    def test_generic_section_returns_none(self):
        assert _arc_index_from_section("abilities") is None

    def test_case_insensitive(self):
        assert _arc_index_from_section("History.Marineford_Arc") == arc_limit_index("Marineford")


# ---------------------------------------------------------------------------
# _is_safe_section
# ---------------------------------------------------------------------------

class TestIsSafeSection:
    @pytest.mark.parametrize("section", [
        "overview",
        "abilities",
        "personality",
        "appearance",
        "relationships",
        "site_navigation",
        "trivia",
        "gallery",
        "abilities.combat",
        "personality.traits",
    ])
    def test_safe_sections_identified(self, section: str):
        assert _is_safe_section(section) is True

    @pytest.mark.parametrize("section", [
        "history.marineford_arc",
        "history.wano_arc",
        "history.alabasta",
        "history.childhood",
    ])
    def test_history_sections_not_safe(self, section: str):
        assert _is_safe_section(section) is False


# ---------------------------------------------------------------------------
# filter_by_spoiler_limit — comportement global
# ---------------------------------------------------------------------------

class TestFilterBySpoilerLimit:

    def test_no_limit_returns_all(self):
        results = [
            _result("history.wano_arc"),
            _result("history.marineford_arc"),
            _result("abilities"),
        ]
        assert filter_by_spoiler_limit(results, None) == results
        assert filter_by_spoiler_limit(results, "Aucun") == results

    def test_safe_sections_always_kept(self):
        results = [_result("abilities"), _result("personality"), _result("overview")]
        filtered = filter_by_spoiler_limit(results, "East Blue")
        assert len(filtered) == 3

    def test_known_arc_at_or_before_limit_kept(self):
        results = [
            _result("history.arlong_park_arc"),      # East Blue → kept
            _result("history.east_blue"),             # East Blue → kept
        ]
        filtered = filter_by_spoiler_limit(results, "Alabasta")
        assert len(filtered) == 2

    def test_known_arc_after_limit_excluded(self):
        results = [
            _result("history.marineford_arc"),        # Marineford > Alabasta → excluded
            _result("history.wano_country_arc"),      # Wano > Alabasta → excluded
        ]
        filtered = filter_by_spoiler_limit(results, "Alabasta")
        assert len(filtered) == 0

    def test_fail_closed_unknown_history_section_excluded(self):
        """Sections history.* non reconnues sont exclues (fail-closed)."""
        results = [_result("history.flashback_unknown_arc")]
        filtered = filter_by_spoiler_limit(results, "Alabasta")
        assert len(filtered) == 0

    def test_mixed_results(self):
        results = [
            _result("overview"),                      # safe → kept
            _result("abilities.combat"),              # safe → kept
            _result("history.alabasta"),              # Alabasta == limit → kept
            _result("history.sabaody_archipelago"),   # Sabaody > Alabasta → excluded
            _result("history.marineford_arc"),        # Marineford > Alabasta → excluded
            _result("history.flashback_unknown"),     # unknown history → excluded (fail-closed)
        ]
        filtered = filter_by_spoiler_limit(results, "Alabasta")
        assert len(filtered) == 3
        kept_sections = {r.section for r in filtered}
        assert "overview" in kept_sections
        assert "abilities.combat" in kept_sections
        assert "history.alabasta" in kept_sections

    def test_unknown_limit_arc_returns_all(self):
        """Arc limite non reconnu → aucun filtre applique."""
        results = [_result("history.wano_arc"), _result("history.marineford_arc")]
        assert filter_by_spoiler_limit(results, "Arc Inconnu") == results

    def test_empty_results(self):
        assert filter_by_spoiler_limit([], "Marineford") == []

    def test_wano_limit_keeps_all_previous_arcs(self):
        results = [
            _result("history.east_blue"),
            _result("history.alabasta"),
            _result("history.marineford_arc"),
            _result("history.dressrosa"),
            _result("history.wano_country_arc"),
        ]
        filtered = filter_by_spoiler_limit(results, "Wano")
        assert len(filtered) == 5

    def test_egghead_after_wano_excluded_when_wano_limit(self):
        results = [
            _result("history.wano_country_arc"),
            _result("history.egghead_arc"),
        ]
        filtered = filter_by_spoiler_limit(results, "Wano")
        assert len(filtered) == 1
        assert filtered[0].section == "history.wano_country_arc"
