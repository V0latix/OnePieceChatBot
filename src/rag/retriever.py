"""Retrieval hybride: vector search + keyword + signal graph."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from config.settings import Settings
from processing.embedder import EmbeddingGenerator
from processing.vector_store import QdrantVectorStore
from rag.graph_ranker import GraphRanker
from rag.noise import is_noise_categories as _is_noise_categories
from rag.noise import is_noise_entity as _is_noise_entity
from rag.noise import is_noise_section as _is_noise_section


_WORD_RE = re.compile(r"[a-zA-Z0-9']+")

# Parametres BM25 standards (Robertson/Sparck-Jones).
_BM25_K1 = 1.5
_BM25_B = 0.75


def _tokenize(text: str) -> list[str]:
    return [term.lower() for term in _WORD_RE.findall(text)]


def _graph_match(entities: list[str], entity_name: str) -> bool:
    """Match strict entite<->page pour le boost graphe.

    Evite que "Zoro" matche "Volume Zoro" (l'ancien `in` sous-chaine). On exige
    soit l'egalite exacte, soit qu'une entite multi-mots prefixe le titre
    (ex: "Roronoa Zoro" matche "Roronoa Zoro" mais pas "Volume Zoro").
    """
    name = entity_name.lower().strip()
    for entity in entities:
        alias = entity.lower().strip()
        if not alias:
            continue
        if name == alias:
            return True
        if " " in alias and name.startswith(alias):
            return True
    return False


class EmbeddedChunk(BaseModel):
    """Chunk local enrichi avec son embedding."""

    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    entity_id: str
    entity_name: str
    entity_type: str
    section: str
    content: str
    categories: list[str]
    related_entities: list[str]
    token_count: int
    source_url: str
    embedding: list[float]


class RetrievalResult(BaseModel):
    """Resultat normalise apres retrieval."""

    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    entity_name: str
    entity_type: str
    section: str
    content: str
    source_url: str
    vector_score: float = 0.0
    keyword_score: float = 0.0
    graph_score: float = 0.0
    final_score: float = 0.0
    rerank_score: float = 0.0  # score cross-encoder (2e etage), 0 si desactive


class HybridRetriever:
    """Retriever principal combine vectoriel, lexical et signal entite."""

    def __init__(
        self,
        settings: Settings,
        embedder: EmbeddingGenerator,
        vector_store: QdrantVectorStore | None = None,
        local_embeddings_path: Path | None = None,
        graph_ranker: "GraphRanker | None" = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder
        self.vector_store = vector_store
        # PPR optionnel : injecte un graph_score continu (proximite graphe) au lieu du binaire.
        self.graph_ranker = graph_ranker
        self.local_embeddings_path = local_embeddings_path or settings.chunk_data_dir / "chunks_with_embeddings.jsonl"
        self.local_index = self._load_local_index()
        self._build_bm25_stats()

    def _load_local_index(self) -> list[EmbeddedChunk]:
        if not self.local_embeddings_path.exists():
            return []

        entries: list[EmbeddedChunk] = []
        with self.local_embeddings_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entries.append(EmbeddedChunk.model_validate_json(line))
        return entries

    def _build_bm25_stats(self) -> None:
        """Precalcule IDF / longueur moyenne du corpus local pour le BM25.

        Le corpus local (chunks_with_embeddings.jsonl) est le corpus complet, donc
        l'IDF y est bien defini. Les chunks Qdrant absents du local retombent sur
        un IDF calcule avec df=0 (terme suppose rare), ce qui reste coherent.
        """
        doc_freq: Counter[str] = Counter()
        total_len = 0
        for chunk in self.local_index:
            terms = set(_tokenize(chunk.content))
            doc_freq.update(terms)
            total_len += sum(1 for _ in _WORD_RE.finditer(chunk.content))
        self._bm25_n = max(len(self.local_index), 1)
        self._bm25_avgdl = (total_len / self._bm25_n) if self.local_index else 1.0
        self._bm25_idf = {
            term: self._idf(df) for term, df in doc_freq.items()
        }

    def _idf(self, df: int) -> float:
        return math.log((self._bm25_n - df + 0.5) / (df + 0.5) + 1.0)

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    def _keyword_score(self, query_terms: set[str], content: str) -> float:
        """Score BM25 (TF+IDF) du chunk pour les termes de la question.

        Remplace l'ancien ratio de recouvrement d'ensembles : gere la frequence
        des termes (TF sature) et leur rarete (IDF). Score brut non normalise ;
        c'est la fusion RRF qui reclasse par rang, l'echelle absolue importe peu.
        """
        if not query_terms:
            return 0.0
        tokens = _tokenize(content)
        if not tokens:
            return 0.0
        tf = Counter(tokens)
        dl = len(tokens)
        score = 0.0
        for term in query_terms:
            freq = tf.get(term, 0)
            if freq == 0:
                continue
            idf = self._bm25_idf.get(term, self._idf(0))
            denom = freq + _BM25_K1 * (1 - _BM25_B + _BM25_B * dl / self._bm25_avgdl)
            score += idf * (freq * (_BM25_K1 + 1)) / denom
        return score

    def _local_vector_search(
        self,
        query_embedding: list[float],
        filter_type: str | None,
        top_k: int,
    ) -> list[RetrievalResult]:
        scored: list[RetrievalResult] = []

        for chunk in self.local_index:
            if filter_type and chunk.entity_type != filter_type:
                continue
            if (
                _is_noise_section(chunk.section)
                or _is_noise_entity(chunk.entity_name)
                or _is_noise_categories(chunk.categories)
            ):
                continue
            similarity = self._cosine_similarity(query_embedding, chunk.embedding)
            scored.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    entity_name=chunk.entity_name,
                    entity_type=chunk.entity_type,
                    section=chunk.section,
                    content=chunk.content,
                    source_url=chunk.source_url,
                    vector_score=similarity,
                )
            )

        scored.sort(key=lambda row: row.vector_score, reverse=True)
        return scored[:top_k]

    def _remote_vector_search(
        self,
        query_embedding: list[float],
        filter_type: str | None,
        top_k: int,
    ) -> list[RetrievalResult]:
        if self.vector_store is None:
            return []

        try:
            rows = self.vector_store.search(
                query_embedding=query_embedding,
                match_count=top_k,
                filter_type=filter_type,
            )
        except Exception:
            return []

        return [
            RetrievalResult(
                chunk_id=row.id,
                entity_name=row.entity_name,
                entity_type=row.entity_type,
                section=row.section,
                content=row.content,
                source_url=row.source_url,
                vector_score=float(row.similarity),
            )
            for row in rows
            if not (
                _is_noise_section(row.section)
                or _is_noise_entity(row.entity_name)
                or _is_noise_categories(row.categories)
            )
        ]

    def _vector_search(self, embedding: list[float], filter_type: str | None, candidate_k: int) -> list[RetrievalResult]:
        """Recherche dense : Qdrant distant, avec repli sur l'index cosinus local."""
        results = self._remote_vector_search(embedding, filter_type, candidate_k)
        if not results:
            results = self._local_vector_search(embedding, filter_type, candidate_k)
        return results

    def _dual_vector_search(
        self, question: str, hyde_text: str, filter_type: str | None, candidate_k: int
    ) -> list[RetrievalResult]:
        """Union de deux recherches denses (question + passage HyDE), max-cosinus par chunk.

        Le score reste un cosinus (meme echelle) -> la confiance (moyenne des vector_score)
        et le RRF du reranker restent valides.
        """
        merged: dict[str, RetrievalResult] = {}
        for text in (question, hyde_text):
            for result in self._vector_search(self.embedder.embed_query(text), filter_type, candidate_k):
                existing = merged.get(result.chunk_id)
                if existing is None or result.vector_score > existing.vector_score:
                    merged[result.chunk_id] = result
        return list(merged.values())

    def retrieve(
        self,
        question: str,
        entities: list[str] | None = None,
        filter_type: str | None = None,
        top_k: int | None = None,
        embed_text: str | None = None,
    ) -> list[RetrievalResult]:
        """Execute la recherche hybride pour une question.

        `embed_text` (ex: passage HyDE) sert UNIQUEMENT a la recherche dense ; le
        keyword/BM25 et le signal graphe restent sur la `question` originale.
        """
        top_k = top_k or self.settings.retrieval_top_k
        entities = entities or []

        # Sur-echantillonne dans les deux chemins : le filtrage bruit/categorie
        # s'applique APRES le fetch, donc il faut de la marge pour qu'il reste
        # assez de bons resultats a reranker.
        candidate_k = max(top_k * 3, top_k)
        if self.settings.hyde_dual and embed_text and embed_text != question:
            # Fusion HyDE : recherche dense sur la question ET sur le passage HyDE,
            # union par max-cosinus (recupere ce que chaque requete trouve seule).
            vector_results = self._dual_vector_search(question, embed_text, filter_type, candidate_k)
        else:
            query_embedding = self.embedder.embed_query(embed_text or question)
            vector_results = self._vector_search(query_embedding, filter_type, candidate_k)

        query_terms = set(term.lower() for term in _WORD_RE.findall(question) if len(term) >= 3)

        # PPR : score graphe continu (proximite) si un ranker est branche et seede.
        ppr_scores: dict[str, float] = {}
        if self.graph_ranker is not None and entities:
            ppr_scores = self.graph_ranker.personalized_scores(entities)

        def _graph_score(entity_name: str) -> float:
            if ppr_scores:
                return ppr_scores.get(entity_name, 0.0)
            # Fallback binaire (PPR off ou aucun seed dans le graphe).
            return 1.0 if entities and _graph_match(entities, entity_name) else 0.0

        combined: dict[str, RetrievalResult] = {}
        for result in vector_results:
            result.keyword_score = self._keyword_score(query_terms, result.content)
            result.graph_score = _graph_score(result.entity_name)
            combined[result.chunk_id] = result

        # Ajout lexical pur si l'index local existe.
        for chunk in self.local_index:
            if (
                _is_noise_section(chunk.section)
                or _is_noise_entity(chunk.entity_name)
                or _is_noise_categories(chunk.categories)
            ):
                continue
            keyword_score = self._keyword_score(query_terms, chunk.content)
            if keyword_score <= 0:
                continue
            existing = combined.get(chunk.chunk_id)
            if existing:
                existing.keyword_score = max(existing.keyword_score, keyword_score)
                continue
            combined[chunk.chunk_id] = RetrievalResult(
                chunk_id=chunk.chunk_id,
                entity_name=chunk.entity_name,
                entity_type=chunk.entity_type,
                section=chunk.section,
                content=chunk.content,
                source_url=chunk.source_url,
                keyword_score=keyword_score,
                graph_score=_graph_score(chunk.entity_name),
            )

        results = list(combined.values())
        return results
