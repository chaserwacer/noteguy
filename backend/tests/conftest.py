"""Pytest fixtures for isolated backend API and service tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


@pytest.fixture()
def app_modules(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Reload backend modules with per-test temp settings."""
    db_path = tmp_path / "test.db"
    vault_path = tmp_path / "vault"
    lightrag_dir = tmp_path / "lightrag_data"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("VAULT_PATH", str(vault_path))
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("LIGHTRAG_WORKING_DIR", str(lightrag_dir))

    import app.config as config_module
    import app.database as database_module
    import app.git_service as git_service_module
    import app.embeddings as embeddings_module
    import app.notes as notes_module
    import app.history as history_module
    import app.chat as chat_module
    import app.ingestion as ingestion_module
    import app.context as context_module
    import app.settings_api as settings_api_module
    import app.main as main_module

    for module in (
        config_module,
        database_module,
        git_service_module,
        embeddings_module,
        notes_module,
        history_module,
        chat_module,
        ingestion_module,
        context_module,
        settings_api_module,
        main_module,
    ):
        importlib.reload(module)

    config_module.get_settings.cache_clear()
    embeddings_module.get_embedding_provider.cache_clear()
    git_service_module._git_service = None

    return SimpleNamespace(
        config=config_module,
        database=database_module,
        git_service=git_service_module,
        embeddings=embeddings_module,
        notes=notes_module,
        history=history_module,
        chat=chat_module,
        ingestion=ingestion_module,
        context=context_module,
        settings_api=settings_api_module,
        main=main_module,
    )


@pytest.fixture()
def client(app_modules):
    """FastAPI test client with startup/shutdown lifecycle enabled."""
    with TestClient(app_modules.main.app) as test_client:
        yield test_client
