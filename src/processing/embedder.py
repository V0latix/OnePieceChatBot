"""Generation d'embeddings locaux via sentence-transformers."""

from __future__ import annotations

from typing import Iterable

from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """Encapsule le modele d'embedding BGE."""

    QUERY_PREFIX = "Represent this sentence for retrieval: "

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: Iterable[str], is_query: bool = False) -> list[list[float]]:
        """Encode une collection de textes en vecteurs normalises."""
        text_list = list(texts)
        if is_query:
            text_list = [f"{self.QUERY_PREFIX}{text}" for text in text_list]

        embeddings = self.model.encode(
            text_list,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Encode une requete utilisateur pour la recherche vectorielle."""
        return self.embed_texts([query], is_query=True)[0]
