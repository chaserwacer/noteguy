"""Pluggable embedding provider abstraction.

Supports local Ollama embeddings and OpenAI embeddings behind one interface.
The active provider is controlled via the ``embedding_provider`` setting.
There is no fallback — if the chosen provider fails the error is surfaced.
"""

from abc import ABC, abstractmethod
from functools import lru_cache
import logging

import httpx
import openai

from app.config import get_settings

logger = logging.getLogger(__name__)


def _normalize_provider_name(provider_name: str) -> str:
    """Return a canonical provider name for comparisons and dispatch."""
    return provider_name.strip().lower()


def get_primary_embedding_provider_name() -> str:
    """Return the configured primary embedding provider name."""
    settings = get_settings()
    return _normalize_provider_name(settings.embedding_provider)


def get_embedding_model_name(provider_name: str | None = None) -> str:
    """Return the configured embedding model name for the selected provider."""
    settings = get_settings()
    normalized = _normalize_provider_name(provider_name or settings.embedding_provider)
    if normalized == "ollama":
        return settings.embedding_ollama_model
    if normalized == "openai":
        return settings.embedding_openai_model
    raise ValueError(f"Unsupported embedding provider: {provider_name}")



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
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(
                    f"{self._base_url}/api/embed",
                    json={"model": self._model, "input": texts},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.ConnectError as exc:
            raise RuntimeError(
                "Ollama embedding service is not running or unreachable"
            ) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"Ollama embedding request timed out after {self._timeout_seconds} seconds"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama embedding request failed with status {exc.response.status_code}"
            ) from exc
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise ValueError("Ollama embedding response missing embeddings list")
        if len(embeddings) != len(texts):
            raise ValueError(
                "Ollama embedding response length does not match input text count"
            )
        for embedding in embeddings:
            if not isinstance(embedding, list) or not embedding:
                raise ValueError("Ollama embedding response contains invalid vectors")
            if not all(isinstance(value, (int, float)) for value in embedding):
                raise ValueError(
                    "Ollama embedding response vectors must contain numeric values"
                )
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


def _build_provider(provider_name: str) -> EmbeddingProvider:
    settings = get_settings()
    normalized = _normalize_provider_name(provider_name)
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
    """Return the singleton embedding provider (no fallback)."""
    settings = get_settings()
    primary_name = _normalize_provider_name(settings.embedding_provider)
    return _build_provider(primary_name)
