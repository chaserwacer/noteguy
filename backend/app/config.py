"""Application configuration loaded from environment variables.

User-facing settings (AI provider, model, API key) can be overridden at
runtime via the settings API.  Overrides are persisted in a JSON file
next to the backend package so they survive restarts.
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

_USER_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "user_settings.json"


def _load_user_overrides() -> dict:
    """Read runtime overrides saved by the settings API."""
    if _USER_SETTINGS_PATH.exists():
        try:
            return json.loads(_USER_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_user_overrides(overrides: dict) -> None:
    """Persist runtime overrides and invalidate the cached settings."""
    existing = _load_user_overrides()
    existing.update(overrides)
    _USER_SETTINGS_PATH.write_text(
        json.dumps(existing, indent=2),
        encoding="utf-8",
    )
    # Bust the settings cache so the next call picks up new values.
    get_settings.cache_clear()


class Settings(BaseSettings):
    """Central configuration sourced from .env at the project root."""

    openai_api_key: str = ""
    database_url: str = "sqlite:///./noteguy.db"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    vault_path: str = str(Path.home() / "NoteGuy")

    # Ollama local inference
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # LLM provider selection — "openai" or "ollama"
    llm_provider: str = "openai"

    # Embeddings configuration — provider is "openai" or "ollama"
    embedding_provider: str = "openai"
    embedding_timeout_seconds: float = 8.0
    embedding_ollama_model: str = "all-minilm"
    embedding_openai_model: str = "text-embedding-3-large"
    embedding_dimension: int = 3072

    # LLM configuration
    llm_model: str = "gpt-4o"
    llm_max_tokens: int = 2048
    vision_model: str = "gpt-4o"

    # LightRAG configuration
    lightrag_working_dir: str = "./lightrag_data"
    lightrag_chunk_token_size: int = 1200
    lightrag_chunk_overlap_token_size: int = 100
    lightrag_top_k: int = 60
    lightrag_query_mode: str = "hybrid"

    # RAG-Anything configuration
    raganything_output_dir: str = "./raganything_output"
    raganything_parser: str = "mineru"
    raganything_enable_images: bool = True
    raganything_enable_tables: bool = True
    raganything_enable_equations: bool = True

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the app settings.

    Runtime overrides from ``user_settings.json`` take highest priority
    (init kwargs beat env vars in pydantic-settings).
    """
    return Settings(**_load_user_overrides())
