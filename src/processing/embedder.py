"""Generation d'embeddings locaux via sentence-transformers."""

from __future__ import annotations

from typing import Iterable

from sentence_transformers import SentenceTransformer

# Instruction de requete specifique a bge-large-en / bge-base-en. bge-m3 (multilingue)
# n'utilise AUCUN prefixe pour le dense — l'ajouter injecterait de l'anglais dans une
# question FR et degraderait le retrieval.
_QUERY_INSTRUCTION = "Represent this sentence for retrieval: "


def _query_prefix(model_name: str) -> str:
    """Prefixe de requete adapte au modele ("" pour bge-m3)."""
    return "" if "bge-m3" in model_name.lower() else _QUERY_INSTRUCTION


class EmbeddingGenerator:
    """Encapsule le modele d'embedding BGE."""

    QUERY_PREFIX = _QUERY_INSTRUCTION  # compat retro

    def __init__(self, model_name: str, device: str | None = None) -> None:
        self.model_name = model_name
        self.query_prefix = _query_prefix(model_name)
        self.model = self._load_model(model_name, device)

    def _load_model(self, model_name: str, device: str | None = None) -> SentenceTransformer:
        """Charge le modele, puis bascule en local-only si le reseau est indisponible."""
        try:
            return SentenceTransformer(model_name, device=device)
        except Exception:
            return SentenceTransformer(model_name, device=device, local_files_only=True)

    def embed_texts(self, texts: Iterable[str], is_query: bool = False) -> list[list[float]]:
        """Encode une collection de textes en vecteurs normalises."""
        text_list = list(texts)
        if is_query and self.query_prefix:
            text_list = [f"{self.query_prefix}{text}" for text in text_list]

        embeddings = self.model.encode(
            text_list,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Encode une requete utilisateur pour la recherche vectorielle."""
        return self.embed_texts([query], is_query=True)[0]
