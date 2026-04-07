"""Unit tests for embedding utility functions."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.embeddings import get_embedding_model_name
from app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_get_embedding_model_name_returns_configured_model(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-large")
    monkeypatch.setattr("app.config._load_user_overrides", lambda: {})
    import app.config
    app.config.get_settings.cache_clear()
    assert get_embedding_model_name() == "text-embedding-3-large"
