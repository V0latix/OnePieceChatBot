"""Configuration centralisee de l'application."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parametres d'execution charges depuis l'environnement."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "onepiece-rag"
    log_level: str = "INFO"

    fandom_api_base: HttpUrl = "https://onepiece.fandom.com/api.php"
    scrape_request_delay_min: float = 1.0
    scrape_request_delay_max: float = 2.0
    scrape_max_retries: int = 5

    qdrant_url: str | None = Field(default=None, alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="op_chunks", alias="QDRANT_COLLECTION")

    neo4j_uri: str | None = Field(default=None, alias="NEO4J_URI")
    neo4j_user: str | None = Field(default=None, alias="NEO4J_USER")
    neo4j_password: str | None = Field(default=None, alias="NEO4J_PASSWORD")

    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    embedding_model: str = Field(default="BAAI/bge-large-en-v1.5", alias="EMBEDDING_MODEL")
    llm_model: str | None = Field(default=None, alias="LLM_MODEL")
    groq_model: str = Field(default="llama-3.1-70b-versatile", alias="GROQ_MODEL")
    ollama_model: str | None = Field(default=None, alias="OLLAMA_MODEL")
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP")
    retrieval_top_k: int = Field(default=5, alias="RETRIEVAL_TOP_K")

    rerank_vector_weight: float = Field(default=0.4, alias="RERANK_VECTOR_WEIGHT")
    rerank_graph_weight: float = Field(default=0.4, alias="RERANK_GRAPH_WEIGHT")
    rerank_keyword_weight: float = Field(default=0.2, alias="RERANK_KEYWORD_WEIGHT")

    data_dir: Path = Path("data")
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")
    chunk_data_dir: Path = Path("data/chunks")
    graph_data_dir: Path = Path("data/graph")
    scrape_state_path: Path = Path("data/raw/scrape_state.json")

    @model_validator(mode="after")
    def validate_ranges(self) -> "Settings":
        """Valide les parametres numeriques critiques."""
        if self.chunk_size <= 0:
            raise ValueError("CHUNK_SIZE doit etre strictement positif")
        if self.chunk_overlap < 0:
            raise ValueError("CHUNK_OVERLAP doit etre positif")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP doit rester inferieur a CHUNK_SIZE")
        if self.scrape_request_delay_min <= 0:
            raise ValueError("Le delai minimum de scraping doit etre > 0")
        if self.scrape_request_delay_max < self.scrape_request_delay_min:
            raise ValueError("Le delai max doit etre >= au delai min")
        if self.scrape_max_retries < 1:
            raise ValueError("Le nombre de retries doit etre >= 1")
        total = self.rerank_vector_weight + self.rerank_graph_weight + self.rerank_keyword_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"RERANK_*_WEIGHT doivent sommer a 1.0 (actuel: {total:.4f})")
        return self

    def ensure_directories(self) -> None:
        """Cree l'arborescence data si necessaire."""
        for directory in (
            self.data_dir,
            self.raw_data_dir,
            self.processed_data_dir,
            self.chunk_data_dir,
            self.graph_data_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retourne une instance singleton des settings."""
    settings = Settings()
    settings.ensure_directories()
    return settings
