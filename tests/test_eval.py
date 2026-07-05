"""Self-check offline du harness d'eval (loader golden + parsing score juge)."""

from __future__ import annotations

import sys
from pathlib import Path

# eval_common vit dans scripts/ (importe par 06/07 via sys.path auto)
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import eval_common

GOLDEN = Path(__file__).parent.parent / "data" / "eval" / "golden.jsonl"


def test_load_golden_non_empty_and_schema():
    rows = eval_common.load_golden(GOLDEN)
    assert rows, "golden set vide"
    for row in rows:
        for key in ("question", "expected_entities", "primary", "category"):
            assert key in row, f"cle manquante {key} dans {row}"
        assert row["expected_entities"], "expected_entities vide"
        # sanity : l'entite principale doit figurer dans les entites attendues
        assert any(
            row["primary"].lower() in e.lower() or e.lower() in row["primary"].lower()
            for e in row["expected_entities"]
        ), f"primary '{row['primary']}' absent de expected_entities"


def test_parse_score():
    assert eval_common.parse_score("0.8") == 0.8
    assert eval_common.parse_score("Score: 0.7/1") == 0.7
    assert eval_common.parse_score("1.5") == 1.0  # clamp haut
    assert eval_common.parse_score("-0.2") == 0.0  # clamp bas
    assert eval_common.parse_score("n/a") == 0.0  # aucun nombre -> fallback
    assert eval_common.parse_score("") == 0.0
