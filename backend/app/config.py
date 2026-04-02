"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration sourced from .env at the project root."""

    # Retained only for backward compatibility with existing .env files.
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    database_url: str = "sqlite:///./noteguy.db"
    chroma_persist_dir: str = "./chroma_data"
    chroma_tenant: str = "default_tenant"
    chroma_database: str = "default_database"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    vault_path: str = str(Path.home() / "NoteGuy")

    # Ollama local inference
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Embeddings configuration
    embedding_provider: str = "ollama"
    embedding_fallback_provider: str = "openai"
    embedding_allow_fallback: bool = True
    embedding_timeout_seconds: float = 8.0
    embedding_ollama_model: str = "all-minilm"
    embedding_openai_model: str = "text-embedding-3-small"

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the app settings."""
    return Settings()
