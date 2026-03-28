"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration sourced from .env at the project root."""

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    database_url: str = "sqlite:///./notevault.db"
    chroma_persist_dir: str = "./chroma_data"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    vault_path: str = str(Path.home() / "NoteVault")

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the app settings."""
    return Settings()
