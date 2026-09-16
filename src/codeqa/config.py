from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Application
    app_name: str = "CodeQA"
    environment: str = "development"
    debug: bool = True

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "codeqa"
    postgres_user: str = "codeqa"
    postgres_password: str = "codeqa"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "codeqa_chunks"

    # Ingestion
    max_file_size_mb: int = 1
    max_repo_chunks: int = 100_000
    cache_dir: str = ".cache/codeqa"

    # Embeddings
    embedding_model: str = "jinaai/jina-embeddings-v2-base-code"
    embedding_batch_size: int = 32

    # LLM
    llm_provider: str = "groq"
    llm_model: str = ""

    # RAG
    retrieval_top_k: int = 30
    final_context_k: int = 6
    max_context_tokens: int = 6000

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """Build the PostgreSQL connection URL."""

        return (
            f"postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}"
            f"/{self.postgres_db}"
        )

    @property
    def qdrant_url(self) -> str:
        """Build the Qdrant connection URL."""

        return f"http://{self.qdrant_host}:{self.qdrant_port}"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()