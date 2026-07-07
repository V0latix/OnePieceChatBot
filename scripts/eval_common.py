"""Helpers partages entre 06_eval.py (retrieval) et 07_eval_ragas.py (generation).

Python ajoute automatiquement le dossier du script courant a sys.path, donc les
scripts lances via `python scripts/0X_...py` peuvent faire `import eval_common`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_REQUIRED_KEYS = ("question", "expected_entities", "primary", "category")
_FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+")


def load_golden(path: str | Path) -> list[dict[str, Any]]:
    """Charge le golden set JSONL. Ignore lignes vides et commentaires '#'."""
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            row = json.loads(line)
            missing = [k for k in _REQUIRED_KEYS if k not in row]
            if missing:
                raise ValueError(f"golden ligne {lineno}: cles manquantes {missing}")
            rows.append(row)
    if not rows:
        raise ValueError(f"golden set vide: {path}")
    return rows


def parse_score(text: str) -> float:
    """Extrait le premier flottant d'une reponse LLM et le borne a [0, 1].

    Le juge est cense repondre juste un nombre, mais tolere "Score: 0.7/1" etc.
    Retourne 0.0 si aucun nombre trouve (fallback prudent).
    """
    match = _FLOAT_RE.search(text or "")
    if not match:
        return 0.0
    return max(0.0, min(1.0, float(match.group())))


def judge_score(generator: Any, instruction: str, payload: str, model: str | None = None) -> float:
    """Note 0-1 via le juge Groq, en reutilisant le client existant.

    `generator` = AnswerGenerator ; on appelle son `_generate_with_groq(messages)`
    (circuit breaker inclus). En cas d'echec (pas de cle, breaker ouvert), retourne
    -1.0 pour signaler "non evaluable" (a distinguer d'un vrai 0.0).
    """
    # ponytail: juge LLM one-shot 0-1 — remplacer par ragas si le signal est trop bruite.
    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un evaluateur strict. Reponds UNIQUEMENT par un nombre entre "
                "0 et 1 (ex: 0.8), sans texte."
            ),
        },
        {"role": "user", "content": f"{instruction}\n\n{payload}"},
    ]
    try:
        raw = generator._generate_with_groq(messages, model=model)
    except Exception:
        return -1.0
    return parse_score(raw)


if __name__ == "__main__":  # self-check rapide sans reseau
    assert parse_score("0.8") == 0.8
    assert parse_score("Score: 0.7/1") == 0.7
    assert parse_score("1.5") == 1.0
    assert parse_score("n/a") == 0.0
    print("eval_common self-check OK")
