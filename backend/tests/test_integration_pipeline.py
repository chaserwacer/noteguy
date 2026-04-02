"""Integration tests for the full NoteGuy pipeline.

These tests exercise the real embedding adapter → ChromaDB → RAG → chat flow
with a deterministic fake embedding provider and mocked LLM responses.
Unlike the existing tests that mock at the function level, these ensure the
actual wiring between components works end-to-end.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import chromadb
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# ── Deterministic embedding provider ────────────────────────────────────────

EMBED_DIM = 64


def _deterministic_vector(text: str) -> list[float]:
    """Generate a deterministic embedding vector from text via hashing."""
    digest = hashlib.sha256(text.encode()).digest()
    return [(b - 128) / 128.0 for b in digest[:EMBED_DIM]]


class FakeEmbeddingProvider:
    """Deterministic embedding provider for integration tests."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_deterministic_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return _deterministic_vector(text)


class FakeEmbeddingAdapter:
    """ChromaDB-compatible embedding adapter using deterministic vectors."""

    def __call__(self, input):
        if isinstance(input, str):
            return [_deterministic_vector(input)]
        return [_deterministic_vector(t) for t in input]

    def embed_query(self, query=None, *, input=None, **_kwargs):
        text = input if input is not None else query
        if isinstance(text, list):
            return [_deterministic_vector(t) for t in text]
        return _deterministic_vector(text)

    def name(self) -> str:
        return "test-embedding-adapter"


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def integration_modules(monkeypatch, tmp_path):
    """Reload backend modules with real ChromaDB + fake embeddings + mocked LLM."""
    db_path = tmp_path / "test.db"
    vault_path = tmp_path / "vault"
    chroma_path = tmp_path / "chroma_data"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("VAULT_PATH", str(vault_path))
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma_path))
    monkeypatch.setenv("CHROMA_TENANT", "default_tenant")
    monkeypatch.setenv("CHROMA_DATABASE", "default_database")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    import app.config as config_module
    import app.database as database_module
    import app.git_service as git_service_module
    import app.embeddings as embeddings_module
    import app.vector_store as vector_store_module
    import app.notes as notes_module
    import app.history as history_module
    import app.chat as chat_module
    import app.rag as rag_module
    import app.ingestion as ingestion_module
    import app.context as context_module
    import app.main as main_module

    for module in (
        config_module,
        database_module,
        git_service_module,
        embeddings_module,
        vector_store_module,
        notes_module,
        history_module,
        chat_module,
        rag_module,
        ingestion_module,
        context_module,
        main_module,
    ):
        importlib.reload(module)

    config_module.get_settings.cache_clear()
    embeddings_module.get_embedding_provider.cache_clear()
    vector_store_module.get_collection.cache_clear()
    git_service_module._git_service = None

    # Build a real ChromaDB collection with our fake embedding adapter.
    # Use a unique name per test to prevent cross-test pollution.
    import uuid
    chroma_client = chromadb.Client()
    collection = chroma_client.get_or_create_collection(
        name=f"noteguy_test_{uuid.uuid4().hex[:8]}",
        embedding_function=FakeEmbeddingAdapter(),
    )

    def _get_test_collection():
        return collection

    # Patch get_collection on every module that imports it
    monkeypatch.setattr(vector_store_module, "get_collection", _get_test_collection)
    monkeypatch.setattr(rag_module, "get_collection", _get_test_collection)
    monkeypatch.setattr(ingestion_module, "get_collection", _get_test_collection)

    return SimpleNamespace(
        config=config_module,
        database=database_module,
        git_service=git_service_module,
        embeddings=embeddings_module,
        vector_store=vector_store_module,
        notes=notes_module,
        history=history_module,
        chat=chat_module,
        rag=rag_module,
        ingestion=ingestion_module,
        context=context_module,
        main=main_module,
        collection=collection,
    )


@pytest.fixture()
def int_client(integration_modules):
    """FastAPI test client wired to real ChromaDB + fake embeddings."""
    with TestClient(integration_modules.main.app) as c:
        yield c


def _disable_git_side_effects(monkeypatch, mods):
    """Disable git background tasks to avoid needing a real git repo."""
    monkeypatch.setattr(mods.notes, "_bg_git_commit", lambda *a, **kw: None)
    monkeypatch.setattr(mods.notes, "_bg_git_commit_batched", lambda *a, **kw: None)
    monkeypatch.setattr(mods.notes, "_bg_git_move", lambda *a, **kw: None)
    monkeypatch.setattr(mods.notes, "_bg_git_delete", lambda *a, **kw: None)


# ── Test: Full ingest → search pipeline ─────────────────────────────────────


def test_ingest_and_search_returns_relevant_chunks(
    int_client, integration_modules, monkeypatch
):
    """Create a note, ingest it, and verify vector search returns it."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)

    resp = int_client.post(
        "/api/notes",
        json={
            "title": "Python Basics",
            "content": "# Python\n\nPython is a programming language.\n\nIt supports object-oriented programming.",
        },
    )
    assert resp.status_code == 201
    note_id = resp.json()["id"]

    mods.database.init_db()
    with Session(mods.database.engine) as session:
        chunk_count = mods.ingestion.ingest_note_sync(note_id, session)
    assert chunk_count > 0

    search_resp = int_client.post(
        "/api/search",
        json={"query": "Python programming language", "top_k": 5},
    )
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) > 0
    assert any(r["note_id"] == note_id for r in results)
    for r in results:
        assert "content" in r
        assert "note_title" in r
        assert "note_id" in r
        assert "folder_path" in r
        assert "score" in r
        assert 0 <= r["score"] <= 1


def test_ingest_multiple_notes_search_returns_both(
    int_client, integration_modules, monkeypatch
):
    """Ingest two notes, search should find both."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)

    note1_resp = int_client.post(
        "/api/notes",
        json={
            "title": "Cooking Recipes",
            "content": "# Pasta\n\nBoil water and add spaghetti. Cook for 10 minutes.",
        },
    )
    note2_resp = int_client.post(
        "/api/notes",
        json={
            "title": "Machine Learning",
            "content": "# Neural Networks\n\nDeep learning uses neural networks with multiple layers.",
        },
    )
    note1_id = note1_resp.json()["id"]
    note2_id = note2_resp.json()["id"]

    mods.database.init_db()
    with Session(mods.database.engine) as session:
        mods.ingestion.ingest_note_sync(note1_id, session)
        mods.ingestion.ingest_note_sync(note2_id, session)

    search_resp = int_client.post(
        "/api/search", json={"query": "food cooking pasta", "top_k": 10}
    )
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) >= 2


# ── Test: Full chat pipeline (ingest → retrieve → LLM answer) ──────────────


def test_chat_endpoint_with_real_vector_search(
    int_client, integration_modules, monkeypatch
):
    """Chat endpoint should retrieve context from ChromaDB and call the LLM."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)

    resp = int_client.post(
        "/api/notes",
        json={
            "title": "Project Architecture",
            "content": "# Architecture\n\nThe backend uses FastAPI with SQLModel for the database layer.",
        },
    )
    note_id = resp.json()["id"]

    mods.database.init_db()
    with Session(mods.database.engine) as session:
        mods.ingestion.ingest_note_sync(note_id, session)

    # Mock the OpenAI LLM call
    mock_choice = MagicMock()
    mock_choice.message.content = "The backend uses FastAPI."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    monkeypatch.setattr(mods.rag, "openai", MagicMock())
    monkeypatch.setattr(mods.rag.openai, "OpenAI", lambda **kw: mock_client)

    chat_resp = int_client.post(
        "/api/chat",
        json={"message": "What framework does the backend use?", "provider": "openai"},
    )
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert "answer" in body
    assert "sources" in body
    assert body["answer"] == "The backend uses FastAPI."
    assert note_id in body["sources"]

    # Verify the LLM was called with context from our note
    call_args = mock_client.chat.completions.create.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert "FastAPI" in user_msg


def test_chat_stream_endpoint_with_real_vector_search(
    int_client, integration_modules, monkeypatch
):
    """Streaming chat should retrieve real context and stream mocked LLM tokens."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)

    resp = int_client.post(
        "/api/notes",
        json={
            "title": "Database Guide",
            "content": "# SQLite\n\nSQLite is a lightweight embedded database engine.",
        },
    )
    note_id = resp.json()["id"]

    mods.database.init_db()
    with Session(mods.database.engine) as session:
        mods.ingestion.ingest_note_sync(note_id, session)

    mock_stream = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="SQLite "))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="is "))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="lightweight."))]),
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_stream

    monkeypatch.setattr(mods.rag, "openai", MagicMock())
    monkeypatch.setattr(mods.rag.openai, "OpenAI", lambda **kw: mock_client)

    stream_resp = int_client.post(
        "/api/chat/stream",
        json={"message": "What is SQLite?", "provider": "openai"},
    )
    assert stream_resp.status_code == 200
    assert stream_resp.headers["content-type"].startswith("text/event-stream")

    body = stream_resp.text
    assert '"type":"text_delta"' in body or '"type": "text_delta"' in body
    assert '"type":"source_notes"' in body or '"type": "source_notes"' in body
    assert '"type":"done"' in body or '"type": "done"' in body

    call_args = mock_client.chat.completions.create.call_args
    system = call_args.kwargs["messages"][0]["content"]
    assert "SQLite" in system


def test_chat_with_openai_provider(
    int_client, integration_modules, monkeypatch
):
    """Chat endpoint should work with the OpenAI provider too."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)

    resp = int_client.post(
        "/api/notes",
        json={"title": "Rust Guide", "content": "# Rust\n\nRust is a systems programming language."},
    )
    note_id = resp.json()["id"]

    mods.database.init_db()
    with Session(mods.database.engine) as session:
        mods.ingestion.ingest_note_sync(note_id, session)

    mock_choice = MagicMock()
    mock_choice.message.content = "Rust is a systems language."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    monkeypatch.setattr(mods.rag, "openai", MagicMock())
    monkeypatch.setattr(mods.rag.openai, "OpenAI", lambda **kw: mock_client)

    chat_resp = int_client.post(
        "/api/chat",
        json={"message": "What is Rust?", "provider": "openai"},
    )
    assert chat_resp.status_code == 200
    assert chat_resp.json()["answer"] == "Rust is a systems language."
    assert note_id in chat_resp.json()["sources"]


# ── Test: Folder-scoped search ──────────────────────────────────────────────


def test_folder_scoped_search(int_client, integration_modules, monkeypatch):
    """Search with folder_scope filters results to the specified folder subtree."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)

    folder_resp = int_client.post("/api/folders", json={"name": "school"})
    assert folder_resp.status_code == 201
    folder_id = folder_resp.json()["id"]

    in_folder = int_client.post(
        "/api/notes",
        json={
            "title": "Math Notes",
            "content": "# Calculus\n\nIntegrals and derivatives are fundamental.",
            "folder_id": folder_id,
        },
    )
    outside_folder = int_client.post(
        "/api/notes",
        json={
            "title": "Cooking Tips",
            "content": "# Calculus of Cooking\n\nMeasuring ingredients precisely matters.",
        },
    )
    in_id = in_folder.json()["id"]
    out_id = outside_folder.json()["id"]

    mods.database.init_db()
    with Session(mods.database.engine) as session:
        mods.ingestion.ingest_note_sync(in_id, session)
        mods.ingestion.ingest_note_sync(out_id, session)

    scoped_resp = int_client.post(
        "/api/search",
        json={"query": "calculus", "folder_scope": "school", "top_k": 10},
    )
    assert scoped_resp.status_code == 200
    scoped_note_ids = {r["note_id"] for r in scoped_resp.json()}
    assert in_id in scoped_note_ids
    assert out_id not in scoped_note_ids

    unscoped_resp = int_client.post(
        "/api/search", json={"query": "calculus", "top_k": 10}
    )
    unscoped_note_ids = {r["note_id"] for r in unscoped_resp.json()}
    assert in_id in unscoped_note_ids
    assert out_id in unscoped_note_ids


# ── Test: Context endpoint ──────────────────────────────────────────────────


def test_context_endpoint_returns_folder_info(
    int_client, integration_modules, monkeypatch
):
    """Context endpoint should return folder metadata and note count."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)

    folder_resp = int_client.post("/api/folders", json={"name": "work"})
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


# ── Test: Re-ingestion replaces old chunks ──────────────────────────────────


def test_reingest_replaces_old_chunks(
    int_client, integration_modules, monkeypatch
):
    """Re-ingesting a note should replace old chunks, not duplicate them."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)

    resp = int_client.post(
        "/api/notes",
        json={"title": "Evolving Note", "content": "# Version 1\n\nOriginal content here."},
    )
    note_id = resp.json()["id"]

    mods.database.init_db()
    with Session(mods.database.engine) as session:
        count1 = mods.ingestion.ingest_note_sync(note_id, session)

    int_client.patch(
        f"/api/notes/{note_id}",
        json={"content": "# Version 2\n\nCompletely new content."},
    )

    with Session(mods.database.engine) as session:
        count2 = mods.ingestion.ingest_note_sync(note_id, session)

    # Collection should not have duplicated chunks
    collection = mods.collection
    all_chunks = collection.get(where={"note_id": note_id})
    assert len(all_chunks["ids"]) == count2


# ── Test: Delete note removes vector chunks ─────────────────────────────────


def test_delete_note_removes_chunks_from_vector_store(
    int_client, integration_modules, monkeypatch
):
    """Deleting a note should remove its chunks from ChromaDB."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)
    monkeypatch.setattr(
        mods.notes,
        "_bg_remove_chunks",
        lambda nid: mods.ingestion.remove_note_chunks(nid),
    )

    resp = int_client.post(
        "/api/notes",
        json={"title": "Temp Note", "content": "# Temporary\n\nThis will be deleted."},
    )
    note_id = resp.json()["id"]

    mods.database.init_db()
    with Session(mods.database.engine) as session:
        mods.ingestion.ingest_note_sync(note_id, session)

    collection = mods.collection
    before = collection.get(where={"note_id": note_id})
    assert len(before["ids"]) > 0

    del_resp = int_client.delete(f"/api/notes/{note_id}")
    assert del_resp.status_code == 204

    after = collection.get(where={"note_id": note_id})
    assert len(after["ids"]) == 0


# ── Test: Chat with no indexed notes ────────────────────────────────────────


def test_chat_with_empty_vector_store(
    int_client, integration_modules, monkeypatch
):
    """Chat should still work (no crash) when vector store has no documents."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)

    mock_choice = MagicMock()
    mock_choice.message.content = "I don't have enough context."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    monkeypatch.setattr(mods.rag, "openai", MagicMock())
    monkeypatch.setattr(mods.rag.openai, "OpenAI", lambda **kw: mock_client)

    chat_resp = int_client.post(
        "/api/chat",
        json={"message": "Tell me something", "provider": "openai"},
    )
    assert chat_resp.status_code == 200
    assert "answer" in chat_resp.json()


# ── Test: Upload and ingest pipeline ────────────────────────────────────────


def test_upload_markdown_and_search(
    int_client, integration_modules, monkeypatch
):
    """Uploading a markdown file should create a note searchable after ingestion."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)

    upload_resp = int_client.post(
        "/api/ingest/upload",
        files={"file": ("docker-guide.md", b"# Docker\n\nContainers package applications.", "text/markdown")},
    )
    assert upload_resp.status_code == 200
    payload = upload_resp.json()
    assert payload["status"] == "created"
    note_id = payload["note_id"]

    mods.database.init_db()
    with Session(mods.database.engine) as session:
        count = mods.ingestion.ingest_note_sync(note_id, session)
    assert count > 0

    search_resp = int_client.post(
        "/api/search", json={"query": "Docker containers", "top_k": 5}
    )
    assert search_resp.status_code == 200
    assert any(r["note_id"] == note_id for r in search_resp.json())


# ── Test: Stream with conversation history ──────────────────────────────────


def test_stream_with_conversation_history(
    int_client, integration_modules, monkeypatch
):
    """Streaming chat should forward conversation history to the LLM."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)

    resp = int_client.post(
        "/api/notes",
        json={"title": "API Docs", "content": "# REST API\n\nUse GET for reads, POST for writes."},
    )
    note_id = resp.json()["id"]

    mods.database.init_db()
    with Session(mods.database.engine) as session:
        mods.ingestion.ingest_note_sync(note_id, session)

    mock_stream = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Use "))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="GET."))]),
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_stream

    monkeypatch.setattr(mods.rag, "openai", MagicMock())
    monkeypatch.setattr(mods.rag.openai, "OpenAI", lambda **kw: mock_client)

    stream_resp = int_client.post(
        "/api/chat/stream",
        json={
            "message": "How do I read data?",
            "conversation_history": [
                {"role": "user", "content": "What is REST?"},
                {"role": "assistant", "content": "REST is an architectural style."},
            ],
            "provider": "openai",
        },
    )
    assert stream_resp.status_code == 200

    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    assert len(messages) == 4
    assert messages[1]["content"] == "What is REST?"
    assert messages[2]["content"] == "REST is an architectural style."
    assert messages[3]["content"] == "How do I read data?"


# ── Test: Ingest endpoint queues background task ────────────────────────────


def test_ingest_note_endpoint(int_client, integration_modules, monkeypatch):
    """POST /api/ingest/note/{id} should accept valid note IDs."""
    mods = integration_modules
    _disable_git_side_effects(monkeypatch, mods)
    monkeypatch.setattr(mods.notes, "_schedule_ingest", lambda *a, **kw: None)

    resp = int_client.post(
        "/api/notes",
        json={"title": "Ingest Test", "content": "Content to ingest."},
    )
    note_id = resp.json()["id"]

    ingest_resp = int_client.post(f"/api/ingest/note/{note_id}")
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["status"] == "queued"

    # Non-existent note should 404
    bad_resp = int_client.post("/api/ingest/note/nonexistent-id")
    assert bad_resp.status_code == 404


def test_ingest_all_endpoint(int_client, integration_modules, monkeypatch):
    """POST /api/ingest/all should return queued status."""
    ingest_resp = int_client.post("/api/ingest/all")
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["status"] == "queued"
