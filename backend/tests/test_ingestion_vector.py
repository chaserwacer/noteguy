"""Tests for ingestion pipeline and LightRAG integration."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from sqlmodel import Session

from app.models import Note


@pytest.mark.asyncio
async def test_ingest_note_async_calls_lightrag(app_modules, monkeypatch) -> None:
    """ingest_note_async should delegate to LightRAG insert_note."""
    app_modules.database.init_db()

    mock_insert = AsyncMock(return_value={"status": "indexed", "doc_id": "test-id"})
    monkeypatch.setattr("app.ai.lightrag_service.insert_note", mock_insert)

    with Session(app_modules.database.engine) as session:
        note = Note(
            title="Vector test",
            content="# Heading\n\nParagraph one.\n\nParagraph two.",
        )
        session.add(note)
        session.commit()
        session.refresh(note)

        result = await app_modules.ingestion.ingest_note_async(note.id, session)

    assert result == 1
    mock_insert.assert_called_once()
    call_kwargs = mock_insert.call_args
    assert call_kwargs[1]["note_id"] == note.id
    assert call_kwargs[1]["title"] == "Vector test"


@pytest.mark.asyncio
async def test_ingest_note_async_skips_empty_content(app_modules, monkeypatch) -> None:
    """ingest_note_async should return 0 for notes with empty content."""
    app_modules.database.init_db()

    with Session(app_modules.database.engine) as session:
        note = Note(title="Empty", content="")
        session.add(note)
        session.commit()
        session.refresh(note)

        result = await app_modules.ingestion.ingest_note_async(note.id, session)

    assert result == 0


@pytest.mark.asyncio
async def test_remove_note_chunks_async_calls_lightrag_delete(app_modules, monkeypatch) -> None:
    """remove_note_chunks_async should delegate to LightRAG delete_document."""
    mock_delete = AsyncMock(return_value={"status": "deleted", "doc_id": "test-id"})
    monkeypatch.setattr("app.ai.lightrag_service.delete_document", mock_delete)

    await app_modules.ingestion.remove_note_chunks_async("test-id")

    mock_delete.assert_called_once_with("test-id")


@pytest.mark.asyncio
async def test_ingest_all_async_batches_notes(app_modules, monkeypatch) -> None:
    """ingest_all_async should batch-insert all notes with content."""
    app_modules.database.init_db()

    mock_batch = AsyncMock(return_value={"indexed": 2, "skipped": 0})
    monkeypatch.setattr("app.ai.lightrag_service.insert_notes_batch", mock_batch)

    with Session(app_modules.database.engine) as session:
        session.add(Note(title="Note A", content="Content A"))
        session.add(Note(title="Note B", content="Content B"))
        session.add(Note(title="Empty Note", content=""))
        session.commit()

        result = await app_modules.ingestion.ingest_all_async(session)

    assert result == 2
    mock_batch.assert_called_once()
    payload = mock_batch.call_args[0][0]
    assert len(payload) == 2  # empty note excluded
