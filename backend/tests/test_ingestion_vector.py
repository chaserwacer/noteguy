"""Tests for ingestion and Chroma startup resilience."""

from __future__ import annotations

from types import SimpleNamespace

from sqlmodel import Session

from app.models import Note


class _FakeCollection:
    """Minimal fake Chroma collection used by ingestion tests."""

    def __init__(self) -> None:
        self.deleted_ids: list[list[str]] = []
        self.upsert_calls: list[dict] = []

    def get(self, where=None):
        return {"ids": []}

    def delete(self, ids):
        self.deleted_ids.append(ids)

    def upsert(self, ids, documents, metadatas):
        self.upsert_calls.append(
            {"ids": ids, "documents": documents, "metadatas": metadatas}
        )


def test_ingest_note_sync_upserts_chunks_with_metadata(app_modules, monkeypatch) -> None:
    """ingest_note_sync should create vector chunks with note metadata."""
    fake_collection = _FakeCollection()
    monkeypatch.setattr(app_modules.ingestion, "get_collection", lambda: fake_collection)
    app_modules.database.init_db()

    with Session(app_modules.database.engine) as session:
        note = Note(
            title="Vector test",
            content="# Heading\n\nParagraph one.\n\nParagraph two.",
        )
        session.add(note)
        session.commit()
        session.refresh(note)

        chunk_count = app_modules.ingestion.ingest_note_sync(note.id, session)

    assert chunk_count > 0
    assert len(fake_collection.upsert_calls) == 1

    upsert_payload = fake_collection.upsert_calls[0]
    assert len(upsert_payload["ids"]) == chunk_count
    assert len(upsert_payload["documents"]) == chunk_count
    assert len(upsert_payload["metadatas"]) == chunk_count
    assert all(meta["note_id"] == note.id for meta in upsert_payload["metadatas"])


def test_create_persistent_client_recovers_from_incompatible_store(tmp_path, app_modules, monkeypatch) -> None:
    """Vector store startup should back up incompatible persisted data and recover."""
    persist_dir = tmp_path / "chroma_data"
    persist_dir.mkdir(parents=True, exist_ok=True)
    (persist_dir / "chroma.sqlite3").write_text("corrupt", encoding="utf-8")

    settings_stub = SimpleNamespace(
        chroma_persist_dir=str(persist_dir),
        chroma_tenant="default_tenant",
        chroma_database="default_database",
    )

    monkeypatch.setattr(app_modules.vector_store, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(
        app_modules.vector_store.SharedSystemClient,
        "clear_system_cache",
        lambda: None,
    )

    fake_client = object()
    call_count = {"value": 0}

    def _fake_persistent_client(*_args, **_kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise RuntimeError("sqlite panic: out of range for slice")
        return fake_client

    monkeypatch.setattr(
        app_modules.vector_store.chromadb,
        "PersistentClient",
        _fake_persistent_client,
    )

    recovered = app_modules.vector_store._create_persistent_client()

    assert recovered is fake_client
    assert call_count["value"] == 2
    assert persist_dir.exists()
    assert any(candidate.is_dir() for candidate in tmp_path.glob("chroma_data_backup_*"))


def test_embedding_adapter_supports_query_and_input_keywords(app_modules, monkeypatch) -> None:
    """Embedding adapter should support both legacy and current Chroma query signatures."""

    class _FakeProvider:
        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[float(len(text))] for text in texts]

        def embed_query(self, text: str) -> list[float]:
            return [float(len(text))]

    monkeypatch.setattr(
        app_modules.vector_store,
        "get_embedding_provider",
        lambda: _FakeProvider(),
    )

    adapter = app_modules.vector_store._build_embedding_function()

    assert adapter(["ab", "abcd"]) == [[2.0], [4.0]]
    assert adapter("abc") == [[3.0]]
    assert adapter.embed_query("hello") == [5.0]
    assert adapter.embed_query(query="hello") == [5.0]
    assert adapter.embed_query(input="hello") == [5.0]