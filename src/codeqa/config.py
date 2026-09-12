from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"

    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: str

    qdrant_host: str
    qdrant_port: int = 6333

    embedding_model: str

    llm_provider: str
    llm_model: str | None = None

    reranker_enabled: bool = False

    class Config:
        env_file = ".env"