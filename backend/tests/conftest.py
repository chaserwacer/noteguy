"""Pytest fixtures for isolated backend API and service tests."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_modules(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Reload backend modules with per-test temp settings."""
    db_path = tmp_path / "test.db"
    vault_path = tmp_path / "vault"
    chroma_path = tmp_path / "chroma_data"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("VAULT_PATH", str(vault_path))
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma_path))
    monkeypatch.setenv("CHROMA_TENANT", "default_tenant")
    monkeypatch.setenv("CHROMA_DATABASE", "default_database")

    import app.config as config_module
    import app.database as database_module
    import app.git_service as git_service_module
    import app.vector_store as vector_store_module
    import app.notes as notes_module
    import app.history as history_module
    import app.chat as chat_module
    import app.ingestion as ingestion_module
    import app.main as main_module

    for module in (
        config_module,
        database_module,
        git_service_module,
        vector_store_module,
        notes_module,
        history_module,
        chat_module,
        ingestion_module,
        main_module,
    ):
        importlib.reload(module)

    config_module.get_settings.cache_clear()
    vector_store_module.get_collection.cache_clear()
    git_service_module._git_service = None

    return SimpleNamespace(
        config=config_module,
        database=database_module,
        git_service=git_service_module,
        vector_store=vector_store_module,
        notes=notes_module,
        history=history_module,
        chat=chat_module,
        ingestion=ingestion_module,
        main=main_module,
    )


@pytest.fixture()
def client(app_modules):
    """FastAPI test client with startup/shutdown lifecycle enabled."""
    with TestClient(app_modules.main.app) as test_client:
        yield test_client