"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    environment: str = "development"
    log_level: str = "INFO"

    # External APIs
    huggingface_token: str = ""
    semantic_scholar_api_key: str = ""
    openreview_username: str = ""
    openreview_password: str = ""

    # Database
    database_url: str = "sqlite:///./marginalia.db"

    # Cache — Redis-compatible
    redis_url: str = ""
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""

    # Frontend
    next_public_api_url: str = "http://localhost:8000"

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://marginalia.vercel.app",
        "https://marginalia-ai.vercel.app",
        "https://slops-hackathon-project.vercel.app",
    ]

    # ML Model
    embedding_model: str = "all-MiniLM-L6-v2"


# Singleton
settings = Settings()
