"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


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

    # Embeddings configuration
    embedding_provider: str = "openai"
    embedding_fallback_provider: str = "ollama"
    embedding_allow_fallback: bool = True
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
    """Return a cached singleton of the app settings."""
    return Settings()
