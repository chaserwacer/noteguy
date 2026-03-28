"""Pluggable embedding provider abstraction.

Swap the concrete implementation by changing ``get_embedding_provider()``.
The rest of the pipeline only depends on the ``EmbeddingProvider`` protocol.
"""

from abc import ABC, abstractmethod
from functools import lru_cache

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
    """OpenAI text-embedding-3-small provider."""

    MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str):
        self._client = openai.OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self.MODEL, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Return the singleton embedding provider.

    Change this function to swap in a local model (e.g. sentence-transformers).
    """
    settings = get_settings()
    return OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
