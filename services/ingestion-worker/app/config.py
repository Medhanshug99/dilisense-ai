from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "diligence"
    db_user: str = "diligence"
    db_password: str = "diligence_secret"

    redis_host: str = "redis"
    redis_port: int = 6379

    queue_name: str = "document-ingestion"

    # BGE-large-en-v1.5 outputs 1024-dim vectors
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dim: int = 1024

    # Child chunk ~200 tokens, parent groups ~4-6 children (~800-1200 tokens)
    child_tokens: int = 200
    child_overlap: int = 30
    parent_child_min: int = 4
    parent_child_max: int = 6


settings = Settings()
