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

    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dim: int = 1024

    reranker_model: str = "BAAI/bge-reranker-large"

    dense_top_n: int = 50
    sparse_top_n: int = 50
    rrf_k: int = 60
    fused_top_n: int = 20
    final_top_k: int = 5


settings = Settings()