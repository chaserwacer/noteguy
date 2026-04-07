"""Unit tests for embedding providers — Ollama, OpenAI, and Fallback."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.embeddings import (
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    _normalize_provider_name,
    get_embedding_model_name,
    get_embedding_provider,
)
from app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_and_provider_cache():
    """Ensure env-driven settings are fresh for every test."""
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()


# ── Provider name normalization ─────────────────────────────────────────────


class TestNormalizeProviderName:
    def test_strips_whitespace(self):
        assert _normalize_provider_name("  ollama  ") == "ollama"

    def test_lowercases(self):
        assert _normalize_provider_name("OpenAI") == "openai"

    def test_combined(self):
        assert _normalize_provider_name("  Ollama ") == "ollama"


class TestEmbeddingConfigHelpers:
    def test_get_embedding_model_name_ollama(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
        monkeypatch.setenv("EMBEDDING_OLLAMA_MODEL", "all-minilm")
        monkeypatch.setattr("app.config._load_user_overrides", lambda: {})
        # Clear via the live module reference (survives reloads from other tests)
        import app.config
        app.config.get_settings.cache_clear()
        assert get_embedding_model_name() == "all-minilm"

    def test_get_embedding_model_name_openai(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
        monkeypatch.setenv("EMBEDDING_OPENAI_MODEL", "text-embedding-3-large")
        monkeypatch.setattr("app.config._load_user_overrides", lambda: {})
        import app.config
        app.config.get_settings.cache_clear()
        assert get_embedding_model_name() == "text-embedding-3-large"


# ── Ollama provider ────────────────────────────────────────────────────────


class TestOllamaEmbeddingProvider:
    def _make_provider(self, base_url="http://localhost:11434", model="all-minilm", timeout=5.0):
        return OllamaEmbeddingProvider(base_url=base_url, model=model, timeout_seconds=timeout)

    def test_embed_returns_vectors(self):
        """Successful embedding request returns the expected vectors."""
        provider = self._make_provider()
        fake_response = httpx.Response(
            200,
            json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]},
            request=httpx.Request("POST", "http://localhost:11434/api/embed"),
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = fake_response
            mock_client_cls.return_value = mock_client

            result = provider.embed(["hello", "world"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_embed_empty_list(self):
        """Empty input returns empty output without making HTTP call."""
        provider = self._make_provider()
        assert provider.embed([]) == []

    def test_embed_raises_on_connection_error(self):
        """Connection failure raises RuntimeError."""
        provider = self._make_provider()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("refused")
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="not running or unreachable"):
                provider.embed(["test"])

    def test_embed_raises_on_timeout(self):
        """Timeout raises RuntimeError."""
        provider = self._make_provider(timeout=1.0)
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.TimeoutException("timed out")
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="timed out"):
                provider.embed(["test"])

    def test_embed_raises_on_http_error(self):
        """HTTP 400/500 raises RuntimeError with status code."""
        provider = self._make_provider()
        request = httpx.Request("POST", "http://localhost:11434/api/embed")
        response = httpx.Response(400, request=request)
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="status 400"):
                provider.embed(["test"])

    def test_embed_raises_on_missing_embeddings_key(self):
        """Response without 'embeddings' key raises ValueError."""
        provider = self._make_provider()
        fake_response = httpx.Response(
            200,
            json={"data": "something"},
            request=httpx.Request("POST", "http://localhost:11434/api/embed"),
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = fake_response
            mock_client_cls.return_value = mock_client

            with pytest.raises(ValueError, match="missing embeddings list"):
                provider.embed(["test"])

    def test_embed_raises_on_length_mismatch(self):
        """Mismatched embedding count raises ValueError."""
        provider = self._make_provider()
        fake_response = httpx.Response(
            200,
            json={"embeddings": [[0.1]]},  # 1 embedding for 2 texts
            request=httpx.Request("POST", "http://localhost:11434/api/embed"),
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = fake_response
            mock_client_cls.return_value = mock_client

            with pytest.raises(ValueError, match="length does not match"):
                provider.embed(["a", "b"])

    def test_embed_raises_on_invalid_vector(self):
        """Non-numeric vector values raise ValueError."""
        provider = self._make_provider()
        fake_response = httpx.Response(
            200,
            json={"embeddings": [["not", "numbers"]]},
            request=httpx.Request("POST", "http://localhost:11434/api/embed"),
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = fake_response
            mock_client_cls.return_value = mock_client

            with pytest.raises(ValueError, match="numeric values"):
                provider.embed(["test"])

    def test_embed_query_delegates_to_embed(self):
        """embed_query returns the first vector from embed([text])."""
        provider = self._make_provider()
        fake_response = httpx.Response(
            200,
            json={"embeddings": [[0.5, 0.6]]},
            request=httpx.Request("POST", "http://localhost:11434/api/embed"),
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = fake_response
            mock_client_cls.return_value = mock_client

            result = provider.embed_query("test")
        assert result == [0.5, 0.6]

    def test_trailing_slash_stripped_from_base_url(self):
        """Base URL trailing slash is stripped to avoid double-slash in endpoint."""
        provider = self._make_provider(base_url="http://localhost:11434/")
        assert provider._base_url == "http://localhost:11434"


# ── OpenAI provider ────────────────────────────────────────────────────────


class TestOpenAIEmbeddingProvider:
    def test_embed_calls_openai_api(self):
        mock_embedding_1 = MagicMock()
        mock_embedding_1.embedding = [0.1, 0.2]
        mock_embedding_2 = MagicMock()
        mock_embedding_2.embedding = [0.3, 0.4]
        mock_response = MagicMock()
        mock_response.data = [mock_embedding_1, mock_embedding_2]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.embeddings.create.return_value = mock_response
            mock_openai.return_value = mock_client

            provider = OpenAIEmbeddingProvider(api_key="test-key", model="text-embedding-3-small")
            result = provider.embed(["hello", "world"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input=["hello", "world"]
        )

    def test_embed_query_returns_single_vector(self):
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.5, 0.6]
        mock_response = MagicMock()
        mock_response.data = [mock_embedding]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.embeddings.create.return_value = mock_response
            mock_openai.return_value = mock_client

            provider = OpenAIEmbeddingProvider(api_key="test-key", model="text-embedding-3-small")
            result = provider.embed_query("hello")

        assert result == [0.5, 0.6]
