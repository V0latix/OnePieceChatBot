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
from rag.graph_ranker import GraphRanker
from rag.reranker import CrossEncoderReranker, RRFReranker
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


def run_evaluation(top_k: int = 5, verbose: bool = False, sleep: float = 0.0, limit: int | None = None) -> None:
    configure_logging("WARNING")
    logger = get_logger(__name__)

    settings = get_settings()
    golden = eval_common.load_golden(settings.data_dir / "eval" / "golden.jsonl")
    if limit:
        golden = golden[:limit]
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
    graph_ranker = (
        GraphRanker(settings.graph_data_dir / "triplets.jsonl") if settings.graph_ppr else None
    )
    retriever = HybridRetriever(
        settings=settings, embedder=embedder, vector_store=vector_store, graph_ranker=graph_ranker
    )
    reranker = RRFReranker(k=settings.rerank_rrf_k, graph_boost=settings.rerank_graph_boost)
    cross_encoder = (
        CrossEncoderReranker(settings.cross_encoder_model)
        if settings.rerank_cross_encoder
        else None
    )
    entity_extractor = EntityExtractor.from_raw_documents(settings.raw_data_dir)
    query_transformer = None
    if settings.hyde:
        from rag.generator import AnswerGenerator
        from rag.prompt_builder import PromptBuilder
        from rag.query_transformer import QueryTransformer

        query_transformer = QueryTransformer(AnswerGenerator(settings, PromptBuilder()))
    ce_state = "ON" if cross_encoder else "OFF"
    ppr_state = "ON" if graph_ranker else "OFF"
    hyde_state = "ON" if query_transformer else "OFF"
    print(f"OK ({time.time() - t0:.1f}s)  [cross-encoder: {ce_state} | PPR: {ppr_state} | HyDE: {hyde_state}]\n")

    results: list[EvalResult] = []
    seed_hits = 0  # questions dont l'extraction seed >=1 entite attendue

    for i, gold in enumerate(golden, 1):
        question = gold["question"]
        expected = [e.lower() for e in gold["expected_entities"]]
        primary = gold["primary"].lower()

        entities = entity_extractor.extract(question)
        if any(exp in ent.lower() or ent.lower() in exp for ent in entities for exp in expected):
            seed_hits += 1
        embed_text = query_transformer.hyde(question) if query_transformer else None
        raw = retriever.retrieve(question=question, entities=entities, top_k=top_k * 3, embed_text=embed_text)
        reranked = reranker.rerank(raw)
        if cross_encoder:
            reranked = cross_encoder.rerank(question, reranked, settings.rerank_candidates)
        reranked = reranked[:top_k]

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
        if sleep:
            time.sleep(sleep)  # espace les appels Groq (HyDE) pour menager le rate limit

    # Metriques globales
    n = len(results)
    hit_rate = sum(r.hit for r in results) / n
    recall_rate = sum(r.recall for r in results) / n
    avg_score = sum(r.best_score for r in results if r.hit) / max(sum(r.hit for r in results), 1)

    print(f"\n{'='*60}")
    print(f"  RESULTATS (n={n}, top-K={top_k})")
    print(f"{'='*60}")
    print(f"  Seed accuracy (extraction)    : {seed_hits / n:.1%}  ({seed_hits}/{n})")
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
    parser.add_argument("--sleep", type=float, default=0.0, help="Pause (s) entre questions (menage le rate limit Groq/HyDE)")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de questions")
    args = parser.parse_args()
    run_evaluation(top_k=args.top_k, verbose=args.verbose, sleep=args.sleep, limit=args.limit)


if __name__ == "__main__":
    main()
