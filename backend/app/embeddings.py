"""Pluggable embedding provider abstraction.

Supports local Ollama embeddings and OpenAI embeddings behind one interface.
The active provider and fallback behavior are controlled via configuration.
"""

from abc import ABC, abstractmethod
from functools import lru_cache

import httpx
import openai

from app.config import get_settings


class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Return the embedding vector for a single query string."""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(self, api_key: str, model: str):
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama embedding provider using the local ``/api/embed`` endpoint."""

    def __init__(self, base_url: str, model: str, timeout_seconds: float):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        with httpx.Client(timeout=self._timeout_seconds) as client:
            response = client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": texts},
            )
            response.raise_for_status()
            payload = response.json()
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise ValueError("Ollama embedding response missing embeddings list")
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class FallbackEmbeddingProvider(EmbeddingProvider):
    """Primary provider with optional fallback on failure."""

    def __init__(
        self,
        primary: EmbeddingProvider,
        fallback: EmbeddingProvider | None,
    ):
        self._primary = primary
        self._fallback = fallback

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._primary.embed(texts)
        except Exception:
            if self._fallback is None:
                raise
            return self._fallback.embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


def _build_provider(provider_name: str) -> EmbeddingProvider:
    settings = get_settings()
    normalized = provider_name.strip().lower()
    if normalized == "ollama":
        return OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model=settings.embedding_ollama_model,
            timeout_seconds=settings.embedding_timeout_seconds,
        )
    if normalized == "openai":
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.embedding_openai_model,
        )
    raise ValueError(f"Unsupported embedding provider: {provider_name}")


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Return the singleton embedding provider with optional fallback."""
    settings = get_settings()
    primary = _build_provider(settings.embedding_provider)
    fallback = None
    if settings.embedding_allow_fallback:
        fallback_name = settings.embedding_fallback_provider.strip().lower()
        primary_name = settings.embedding_provider.strip().lower()
        if fallback_name != primary_name:
            fallback = _build_provider(fallback_name)
    return FallbackEmbeddingProvider(primary=primary, fallback=fallback)
