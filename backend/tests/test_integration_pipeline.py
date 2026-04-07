"""Integration tests for the LightRAG-based NoteGuy pipeline.

These tests exercise the full note → LightRAG ingestion → AI query flow
with mocked LLM and embedding providers so no external services are needed.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


# ── Deterministic embedding helpers ───────────────────────────────────────

EMBED_DIM = 64


def _deterministic_vector(text: str) -> list[float]:
    """Generate a deterministic embedding vector from text via hashing."""
    digest = hashlib.sha256(text.encode()).digest()
    return [(b - 128) / 128.0 for b in digest[:EMBED_DIM]]


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def integration_modules(monkeypatch, tmp_path):
    """Reload backend modules with per-test temp settings and mocked AI services."""
    db_path = tmp_path / "test.db"
    vault_path = tmp_path / "vault"
    lightrag_dir = tmp_path / "lightrag_data"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("VAULT_PATH", str(vault_path))
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
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
        main=main_module,
    )


@pytest.fixture()
def int_client(integration_modules):
    """FastAPI test client with mocked LightRAG services."""
    with TestClient(integration_modules.main.app) as c:
        yield c


def _disable_side_effects(monkeypatch, mods):
    """Disable git and ingestion background tasks for deterministic tests."""
    monkeypatch.setattr(mods.notes, "_mark_dirty", lambda *a, **kw: None)
    monkeypatch.setattr(mods.notes, "_bg_remove_chunks", lambda *a, **kw: None)
    monkeypatch.setattr(mods.notes, "_bg_git_commit", lambda *a, **kw: None)
    monkeypatch.setattr(mods.notes, "_bg_git_commit_batched", lambda *a, **kw: None)
    monkeypatch.setattr(mods.notes, "_bg_git_move", lambda *a, **kw: None)
    monkeypatch.setattr(mods.notes, "_bg_git_delete", lambda *a, **kw: None)


# ── Tests: Note CRUD still works ──────────────────────────────────────────


def test_create_and_list_notes(int_client, integration_modules, monkeypatch):
    """Creating a note and listing should work end-to-end."""
    _disable_side_effects(monkeypatch, integration_modules)

    resp = int_client.post(
        "/api/notes",
        json={"title": "Test Note", "content": "Hello world"},
    )
    assert resp.status_code == 201
    note_id = resp.json()["id"]

    list_resp = int_client.get("/api/notes")
    assert list_resp.status_code == 200
    assert any(n["id"] == note_id for n in list_resp.json())


# ── Tests: Chat endpoint with mocked LightRAG ────────────────────────────


def test_chat_endpoint_returns_answer(int_client, integration_modules, monkeypatch):
    """Chat POST should return an answer from mocked LightRAG query."""
    _disable_side_effects(monkeypatch, integration_modules)

    mock_query = AsyncMock(return_value="LightRAG says hello.")
    monkeypatch.setattr("app.ai.lightrag_service.query", mock_query)
    monkeypatch.setattr("app.ingestion_tracker.ensure_all_indexed", AsyncMock())

    resp = int_client.post("/api/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "LightRAG says hello."
    assert "sources" in body


def test_chat_stream_returns_sse(int_client, integration_modules, monkeypatch):
    """Chat stream should return SSE-formatted events."""
    _disable_side_effects(monkeypatch, integration_modules)

    async def _fake_stream(*_args, **_kw):
        yield 'data: {"type": "text_delta", "delta": "Hello"}\n\n'
        yield 'data: {"type": "done"}\n\n'

    monkeypatch.setattr("app.ai.lightrag_service.query_stream", _fake_stream)
    monkeypatch.setattr("app.ingestion_tracker.ensure_all_indexed", AsyncMock())

    resp = int_client.post(
        "/api/chat/stream",
        json={"message": "Hi stream", "conversation_history": []},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert '"type": "text_delta"' in body or '"type":"text_delta"' in body
    assert '"type": "done"' in body or '"type":"done"' in body


# ── Tests: AI query endpoints ─────────────────────────────────────────────


def test_ai_query_endpoint(int_client, integration_modules, monkeypatch):
    """AI query POST should return a response from mocked LightRAG."""
    _disable_side_effects(monkeypatch, integration_modules)

    from app.ai import lightrag_service

    monkeypatch.setattr(lightrag_service, "query", AsyncMock(return_value="Graph answer."))
    monkeypatch.setattr("app.ingestion_tracker.ensure_all_indexed", AsyncMock())

    resp = int_client.post(
        "/api/ai/query",
        json={"question": "What is Python?", "mode": "hybrid"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Graph answer."
    assert body["mode"] == "hybrid"


def test_ai_query_stream_endpoint(int_client, integration_modules, monkeypatch):
    """AI streaming query should return SSE events."""
    _disable_side_effects(monkeypatch, integration_modules)

    from app.ai import lightrag_service

    async def _fake_stream(**_kw):
        yield 'data: {"type": "text_delta", "delta": "chunk1"}\n\n'
        yield 'data: {"type": "done"}\n\n'

    monkeypatch.setattr(lightrag_service, "query_stream", _fake_stream)
    monkeypatch.setattr("app.ingestion_tracker.ensure_all_indexed", AsyncMock())

    resp = int_client.post(
        "/api/ai/query/stream",
        json={"question": "Explain RAG", "mode": "hybrid"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "text_delta" in resp.text
    assert "done" in resp.text


# ── Tests: Context endpoint ───────────────────────────────────────────────


def test_context_endpoint_returns_folder_info(
    int_client, integration_modules, monkeypatch
):
    """Context endpoint should return folder metadata and note count."""
    _disable_side_effects(monkeypatch, integration_modules)

    folder_resp = int_client.post("/api/folders", json={"name": "work"})
    assert folder_resp.status_code == 201
    folder_id = folder_resp.json()["id"]

    int_client.post(
        "/api/notes",
        json={"title": "Meeting Notes", "content": "Discussed Q2 plans.", "folder_id": folder_id},
    )
    int_client.post(
        "/api/notes",
        json={"title": "Todo List", "content": "Ship feature X.", "folder_id": folder_id},
    )

    ctx_resp = int_client.get(f"/api/context/{folder_id}")
    assert ctx_resp.status_code == 200
    ctx = ctx_resp.json()
    assert ctx["folder_name"] == "work"
    assert ctx["note_count"] == 2
    assert ctx["suggested_scope"] == "work"


# ── Tests: Ingestion endpoints ────────────────────────────────────────────


def test_ingest_note_endpoint(int_client, integration_modules, monkeypatch):
    """POST /api/ingest/note/{id} should accept valid note IDs."""
    _disable_side_effects(monkeypatch, integration_modules)

    resp = int_client.post(
        "/api/notes",
        json={"title": "Ingest Test", "content": "Content to ingest."},
    )
    note_id = resp.json()["id"]

    # Mock the background ingestion so it doesn't call real LightRAG
    monkeypatch.setattr(
        integration_modules.ingestion, "_bg_ingest_note", lambda *a, **kw: None
    )

    ingest_resp = int_client.post(f"/api/ingest/note/{note_id}")
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["status"] == "queued"

    bad_resp = int_client.post("/api/ingest/note/nonexistent-id")
    assert bad_resp.status_code == 404


def test_ingest_all_endpoint(int_client, integration_modules, monkeypatch):
    """POST /api/ingest/all should return queued status."""
    monkeypatch.setattr(
        integration_modules.ingestion, "_bg_ingest_all", lambda *a, **kw: None
    )

    ingest_resp = int_client.post("/api/ingest/all")
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["status"] == "queued"


def test_upload_markdown(int_client, integration_modules, monkeypatch):
    """Uploading a markdown file should create a note."""
    _disable_side_effects(monkeypatch, integration_modules)
    monkeypatch.setattr(
        integration_modules.ingestion, "_bg_ingest_note", lambda *a, **kw: None
    )

    upload_resp = int_client.post(
        "/api/ingest/upload",
        files={
            "file": (
                "docker-guide.md",
                b"# Docker\n\nContainers package applications.",
                "text/markdown",
            )
        },
    )
    assert upload_resp.status_code == 200
    payload = upload_resp.json()
    assert payload["status"] == "created"
    assert payload["title"] == "docker-guide"

    note_resp = int_client.get(f"/api/notes/{payload['note_id']}")
    assert note_resp.status_code == 200
    assert note_resp.json()["content"].startswith("# Docker")


# ── Tests: AI status and KG stats ─────────────────────────────────────────


def test_ai_status_endpoint(int_client, integration_modules, monkeypatch):
    """AI status should return engine info and capabilities."""
    monkeypatch.setattr("app.ai.raganything_service.is_available", lambda: False)

    resp = int_client.get("/api/ai/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["engine"] == "lightrag"
    assert len(body["capabilities"]) > 0
    assert "config" in body


# ── Tests: Error handling ─────────────────────────────────────────────────


def test_ai_query_error_returns_502(int_client, integration_modules, monkeypatch):
    """AI query should return HTTP 502 when LightRAG query fails."""
    from app.ai import lightrag_service

    monkeypatch.setattr(
        lightrag_service, "query",
        AsyncMock(side_effect=RuntimeError("Embedding service unreachable")),
    )
    monkeypatch.setattr("app.ingestion_tracker.ensure_all_indexed", AsyncMock())

    resp = int_client.post(
        "/api/ai/query",
        json={"question": "test", "mode": "hybrid"},
    )
    assert resp.status_code == 502
    assert "Embedding service unreachable" in resp.json()["detail"]


def test_chat_error_returns_502(int_client, integration_modules, monkeypatch):
    """Chat endpoint should return HTTP 502 when LightRAG query fails."""
    monkeypatch.setattr(
        "app.ai.lightrag_service.query",
        AsyncMock(side_effect=RuntimeError("LLM unreachable")),
    )
    monkeypatch.setattr("app.ingestion_tracker.ensure_all_indexed", AsyncMock())

    resp = int_client.post("/api/chat", json={"message": "test"})
    assert resp.status_code == 502


def test_stream_error_sends_sse_error_event(int_client, integration_modules, monkeypatch):
    """Streaming query should send an SSE error event instead of crashing."""
    from app.ai import lightrag_service

    async def _error_stream(**_kw):
        yield 'data: {"type": "error", "message": "Query failed"}\n\n'

    monkeypatch.setattr(lightrag_service, "query_stream", _error_stream)
    monkeypatch.setattr("app.ingestion_tracker.ensure_all_indexed", AsyncMock())

    resp = int_client.post(
        "/api/ai/query/stream",
        json={"question": "test", "mode": "hybrid"},
    )
    assert resp.status_code == 200
    assert '"type": "error"' in resp.text or '"type":"error"' in resp.text
