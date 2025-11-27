from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/reskilling_rag"

    # Anthropic (Claude)
    anthropic_api_key: str = ""

    # OpenAI (embeddings)
    openai_api_key: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "reskilling-rag"
    pinecone_environment: str = "us-east-1"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Admin
    admin_secret: str = "change-me-in-production"

    # LLM Config
    llm_model: str = "claude-sonnet-4-20250514"
    llm_temperature: float = 0.0
    max_context_tokens: int = 4000

    # Cache
    cache_ttl_seconds: int = 86400  # 24 hours

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1024  # Match Pinecone index dimension

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
