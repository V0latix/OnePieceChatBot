"""Evaluation de la qualite de GENERATION du pipeline RAG (juge LLM leger).

Deux metriques sans reference (pas de reponse-or a fabriquer) :
    - faithfulness      : la reponse est-elle etayee par le contexte retrouve ?
    - answer_relevancy  : la reponse repond-elle bien a la question ?

Le juge reutilise le client Groq existant (`AnswerGenerator._generate_with_groq`).
Sans GROQ_API_KEY, l'evaluation est impossible (le juge est un LLM) -> on skip.

Usage:
    python scripts/07_eval_ragas.py [--limit N] [--sleep 0.0] [--verbose]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import eval_common

from api.dependencies import RAGService
from config.settings import get_settings

_FAITHFULNESS_INSTR = (
    "Note de 0 a 1 dans quelle mesure la REPONSE est entierement etayee par le "
    "CONTEXTE (1 = chaque affirmation est dans le contexte, 0 = inventee)."
)
_RELEVANCY_INSTR = (
    "Note de 0 a 1 dans quelle mesure la REPONSE repond directement a la QUESTION "
    "(1 = pertinente et complete, 0 = hors-sujet)."
)


def run(limit: int | None, sleep: float, verbose: bool) -> None:
    settings = get_settings()
    if not settings.groq_api_key:
        print("GROQ_API_KEY absent : le juge LLM est indisponible, evaluation ignoree.")
        return

    golden = eval_common.load_golden(settings.data_dir / "eval" / "golden.jsonl")
    if limit:
        golden = golden[:limit]

    print(f"\n{'='*60}")
    print(f"  One Piece RAG — Evaluation generation (juge Groq)")
    print(f"  Questions: {len(golden)}")
    print(f"{'='*60}\n")

    print("Chargement du pipeline...", end=" ", flush=True)
    t0 = time.time()
    service = RAGService(settings)
    gen = service.generator
    print(f"OK ({time.time() - t0:.1f}s)\n")

    faith_scores: list[float] = []
    relev_scores: list[float] = []

    for i, gold in enumerate(golden, 1):
        question = gold["question"]
        response = service.ask(question)
        answer = response.answer
        # ponytail: on relance search() pour le texte des chunks (ask() ne renvoie
        # que des citations sans contenu) — 2e retrieval par question, ok pour un eval.
        results = service.search(question)
        context = service.prompt_builder.build_context(results, top_k=settings.retrieval_top_k)

        faith = eval_common.judge_score(
            gen, _FAITHFULNESS_INSTR, f"CONTEXTE:\n{context}\n\nREPONSE:\n{answer}", model=settings.groq_fast_model
        )
        relev = eval_common.judge_score(
            gen, _RELEVANCY_INSTR, f"QUESTION:\n{question}\n\nREPONSE:\n{answer}", model=settings.groq_fast_model
        )
        if faith >= 0:
            faith_scores.append(faith)
        if relev >= 0:
            relev_scores.append(relev)

        if verbose:
            print(f"[{i:02d}/{len(golden)}] faith={faith:+.2f} relev={relev:+.2f} | {question[:50]}")
        if sleep:
            time.sleep(sleep)

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    print(f"\n{'='*60}")
    print(f"  RESULTATS (n={len(golden)})")
    print(f"{'='*60}")
    print(f"  Faithfulness moyen     : {mean(faith_scores):.3f}  ({len(faith_scores)} evalues)")
    print(f"  Answer relevancy moyen : {mean(relev_scores):.3f}  ({len(relev_scores)} evalues)")
    print(f"{'='*60}\n")
    skipped = len(golden) - min(len(faith_scores), len(relev_scores))
    if skipped:
        print(f"({skipped} question(s) non evaluables : juge injoignable/circuit ouvert)\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluation generation RAG One Piece (juge Groq)")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de questions (free tier Groq)")
    parser.add_argument("--sleep", type=float, default=0.0, help="Pause (s) entre questions pour menager le rate limit")
    parser.add_argument("--verbose", action="store_true", help="Afficher le detail par question")
    args = parser.parse_args()
    run(limit=args.limit, sleep=args.sleep, verbose=args.verbose)


if __name__ == "__main__":
    main()
