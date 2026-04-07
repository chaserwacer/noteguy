"""API-level regression tests for core NoteGuy backend routes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock


def _disable_note_background_side_effects(monkeypatch, app_modules) -> None:
    """Disable async ingestion/git side effects for deterministic API tests."""
    monkeypatch.setattr(app_modules.notes, "_mark_dirty", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_modules.notes, "_bg_remove_chunks", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_modules.notes, "_bg_git_commit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_modules.notes, "_bg_git_commit_batched", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_modules.notes, "_bg_git_move", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_modules.notes, "_bg_git_delete", lambda *_args, **_kwargs: None)


def test_health_endpoint(client) -> None:
    """Health endpoint returns a stable liveness payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_notes_crud_happy_path(client, app_modules, monkeypatch) -> None:
    """Notes CRUD endpoint flow works end-to-end for a simple note."""
    _disable_note_background_side_effects(monkeypatch, app_modules)

    create_response = client.post(
        "/api/notes",
        json={"title": "Test Note", "content": "Hello world"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    note_id = created["id"]

    settings = app_modules.config.get_settings()
    note_path = Path(settings.vault_path) / f"{note_id}.md"
    assert note_path.exists()
    assert note_path.read_text(encoding="utf-8") == "Hello world"

    list_response = client.get("/api/notes")
    assert list_response.status_code == 200
    listed_ids = {item["id"] for item in list_response.json()}
    assert note_id in listed_ids

    get_response = client.get(f"/api/notes/{note_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Test Note"

    update_response = client.patch(
        f"/api/notes/{note_id}",
        json={"title": "Updated", "content": "Updated content"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated"

    delete_response = client.delete(f"/api/notes/{note_id}")
    assert delete_response.status_code == 204
    assert not note_path.exists()

    not_found_response = client.get(f"/api/notes/{note_id}")
    assert not_found_response.status_code == 404


def test_chat_endpoint_contract(client, app_modules, monkeypatch) -> None:
    """Chat POST accepts the frontend payload shape and returns expected response."""
    _disable_note_background_side_effects(monkeypatch, app_modules)

    # The chat module lazy-imports from lightrag_service, so patch at source
    monkeypatch.setattr(
        "app.ai.lightrag_service.query",
        AsyncMock(return_value="ok"),
    )
    monkeypatch.setattr(
        "app.ingestion_tracker.ensure_all_indexed",
        AsyncMock(),
    )

    chat_response = client.post(
        "/api/chat",
        json={"message": "Hi", "folder_id": "folder-1"},
    )
    assert chat_response.status_code == 200
    body = chat_response.json()
    assert body["answer"] == "ok"
    assert "sources" in body


def test_chat_stream_contract(client, app_modules, monkeypatch) -> None:
    """Chat stream returns SSE-formatted events."""
    _disable_note_background_side_effects(monkeypatch, app_modules)

    async def _fake_stream(*_args, **_kwargs):
        yield 'data: {"type":"text_delta","delta":"Hello"}\n\n'
        yield 'data: {"type":"done"}\n\n'

    monkeypatch.setattr("app.ai.lightrag_service.query_stream", _fake_stream)
    monkeypatch.setattr("app.ingestion_tracker.ensure_all_indexed", AsyncMock())

    stream_response = client.post(
        "/api/chat/stream",
        json={
            "message": "Hi stream",
            "conversation_history": [{"role": "user", "content": "previous"}],
            "folder_scope": "school/math",
            "active_note_id": "note-2",
        },
    )
    assert stream_response.status_code == 200
    assert stream_response.headers["content-type"].startswith("text/event-stream")
    body = stream_response.text
    assert '"type":"text_delta"' in body
    assert '"type":"done"' in body


def test_history_endpoint_contract(client, app_modules, monkeypatch) -> None:
    """History endpoint returns the frontend-expected version entry shape."""
    _disable_note_background_side_effects(monkeypatch, app_modules)

    create_response = client.post(
        "/api/notes",
        json={"title": "History note", "content": "v1"},
    )
    note_id = create_response.json()["id"]

    class _FakeGitService:
        def get_file_history(self, _path, max_count=50):
            return [
                {
                    "sha": "abc123",
                    "short_sha": "abc123",
                    "message": "[update] History note",
                    "author": "tester",
                    "timestamp": "2026-01-01T00:00:00+00:00",
                }
            ]

    monkeypatch.setattr(app_modules.history, "get_git_service", lambda: _FakeGitService())

    history_response = client.get(f"/api/notes/{note_id}/history")
    assert history_response.status_code == 200
    payload = history_response.json()
    assert len(payload) == 1
    assert set(payload[0]) == {"sha", "short_sha", "message", "author", "timestamp"}


def test_ingest_upload_accepts_markdown(client, app_modules, monkeypatch) -> None:
    """Ingest upload accepts .md files to match the frontend uploader contract."""
    _disable_note_background_side_effects(monkeypatch, app_modules)
    monkeypatch.setattr(app_modules.ingestion, "_bg_ingest_note", lambda *_args, **_kwargs: None)

    upload_response = client.post(
        "/api/ingest/upload",
        files={"file": ("meeting-notes.md", b"# Meeting\n\nAction item", "text/markdown")},
    )
    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["status"] == "created"
    assert payload["title"] == "meeting-notes"

    note_response = client.get(f"/api/notes/{payload['note_id']}")
    assert note_response.status_code == 200
    assert note_response.json()["content"].startswith("# Meeting")


def test_ai_docx_ingest_handles_multimodal_failure(client, app_modules, monkeypatch) -> None:
    """DOCX ingest keeps text indexing even when multimodal background parsing fails."""
    _disable_note_background_side_effects(monkeypatch, app_modules)

    monkeypatch.setattr("app.ingestion.docx_to_markdown", lambda _bytes: "# Parsed DOCX\n\nBody")
    insert_note_mock = AsyncMock(return_value={"status": "indexed"})
    monkeypatch.setattr("app.ai.lightrag_service.insert_note", insert_note_mock)
    monkeypatch.setattr("app.ai.raganything_service.is_available", lambda: True)
    monkeypatch.setattr(
        "app.ai.raganything_service.process_document",
        AsyncMock(side_effect=RuntimeError("LibreOffice conversion failed")),
    )

    response = client.post(
        "/api/ai/ingest/document",
        files={
            "file": (
                "example.docx",
                b"fake-docx-bytes",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "indexed"
    assert payload["title"] == "example"
    insert_note_mock.assert_awaited_once()