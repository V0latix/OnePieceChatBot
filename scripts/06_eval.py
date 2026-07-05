"""Evaluation de la qualite retrieval + generation du pipeline RAG One Piece.

Usage:
    python scripts/06_eval.py [--top-k 5] [--verbose]

Metriques calculees:
    - Retrieval Recall@K  : fraction des questions dont au moins une entite attendue est
                            recuperee dans les top-K resultats.
    - Retrieval Hit@K     : fraction des questions dont l'entite principale est dans les top-K.
    - Avg retrieval score : score moyen du meilleur resultat pour les questions avec hit.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Ajout du dossier src au path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import eval_common

from config.settings import get_settings
from processing.embedder import EmbeddingGenerator
from processing.vector_store import QdrantVectorStore
from rag.entity_extractor import EntityExtractor
from rag.reranker import RRFReranker
from rag.retriever import HybridRetriever
from utils.logger import configure_logging, get_logger


@dataclass
class EvalResult:
    question: str
    primary: str
    hit: bool           # L'entite principale est dans les top-K
    recall: bool        # Au moins une entite attendue est dans les top-K
    best_score: float
    retrieved_entities: list[str]


def run_evaluation(top_k: int = 5, verbose: bool = False) -> None:
    configure_logging("WARNING")
    logger = get_logger(__name__)

    settings = get_settings()
    golden = eval_common.load_golden(settings.data_dir / "eval" / "golden.jsonl")
    print(f"\n{'='*60}")
    print(f"  One Piece RAG — Evaluation retrieval (top-K={top_k})")
    print(f"  Questions: {len(golden)}")
    print(f"{'='*60}\n")

    # Initialisation du pipeline
    print("Chargement du pipeline...", end=" ", flush=True)
    t0 = time.time()
    embedder = EmbeddingGenerator(settings.embedding_model)
    vector_store = None
    if settings.qdrant_url and settings.qdrant_api_key:
        try:
            vector_store = QdrantVectorStore(
                settings.qdrant_url, settings.qdrant_api_key, settings.qdrant_collection
            )
        except Exception as exc:  # noqa: BLE001 - fallback index cosine local
            logger.warning("Qdrant injoignable (%s): eval sur index cosine local", exc)
    retriever = HybridRetriever(settings=settings, embedder=embedder, vector_store=vector_store)
    reranker = RRFReranker(k=settings.rerank_rrf_k, graph_boost=settings.rerank_graph_boost)
    entity_extractor = EntityExtractor.from_raw_documents(settings.raw_data_dir)
    print(f"OK ({time.time() - t0:.1f}s)\n")

    results: list[EvalResult] = []

    for i, gold in enumerate(golden, 1):
        question = gold["question"]
        expected = [e.lower() for e in gold["expected_entities"]]
        primary = gold["primary"].lower()

        entities = entity_extractor.extract(question)
        raw = retriever.retrieve(question=question, entities=entities, top_k=top_k * 3)
        reranked = reranker.rerank(raw)[:top_k]

        retrieved_names = [r.entity_name.lower() for r in reranked]
        retrieved_names += [r.content.lower()[:80] for r in reranked]  # contenu partiel

        hit = any(primary in name for name in retrieved_names)
        recall = any(
            any(exp in name for name in retrieved_names)
            for exp in expected
        )
        best_score = max((r.final_score for r in reranked), default=0.0)

        result = EvalResult(
            question=question,
            primary=gold["primary"],
            hit=hit,
            recall=recall,
            best_score=best_score,
            retrieved_entities=[r.entity_name for r in reranked[:3]],
        )
        results.append(result)

        status = "HIT" if hit else ("RECALL" if recall else "MISS")
        if verbose or not hit:
            print(f"[{i:02d}/{len(golden)}] {status:6s} | {question[:55]:<55} | top3: {result.retrieved_entities}")

    # Metriques globales
    n = len(results)
    hit_rate = sum(r.hit for r in results) / n
    recall_rate = sum(r.recall for r in results) / n
    avg_score = sum(r.best_score for r in results if r.hit) / max(sum(r.hit for r in results), 1)

    print(f"\n{'='*60}")
    print(f"  RESULTATS (n={n}, top-K={top_k})")
    print(f"{'='*60}")
    print(f"  Hit@{top_k}    (entite principale) : {hit_rate:.1%}  ({sum(r.hit for r in results)}/{n})")
    print(f"  Recall@{top_k} (au moins 1 attendue): {recall_rate:.1%}  ({sum(r.recall for r in results)}/{n})")
    print(f"  Score moyen (hits)            : {avg_score:.3f}")
    print(f"{'='*60}\n")

    misses = [r for r in results if not r.recall]
    if misses:
        print(f"Questions sans aucun resultat attendu ({len(misses)}):")
        for r in misses:
            print(f"  - {r.question}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluation du pipeline RAG One Piece")
    parser.add_argument("--top-k", type=int, default=5, help="Nombre de resultats a evaluer (defaut: 5)")
    parser.add_argument("--verbose", action="store_true", help="Afficher tous les resultats (pas seulement les echecs)")
    args = parser.parse_args()
    run_evaluation(top_k=args.top_k, verbose=args.verbose)


if __name__ == "__main__":
    main()
