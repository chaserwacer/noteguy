"""Dirty-note tracker — debounces LightRAG ingestion for frequently edited notes.

Instead of re-indexing into the knowledge graph on every save, notes are marked
"dirty" and ingested only after a configurable period of edit inactivity.  AI
query endpoints force-flush any outstanding dirty notes before executing so the
user always gets up-to-date results.

Flow:
    1. Note update  →  mark_dirty(note_id)         (instant, no I/O)
    2. Background sweep (every SWEEP_INTERVAL_S)    →  ingests notes idle > INACTIVITY_S
    3. AI query      →  ensure_all_indexed()        →  flushes remaining dirty notes first
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Set

logger = logging.getLogger(__name__)

# ── Tunables ─────────────────────────────────────────────────────────────────

# Seconds a note must be idle (no new edits) before the sweep ingests it.
INACTIVITY_S: float = 3600

# How often the background sweep runs (seconds).
SWEEP_INTERVAL_S: float = 120


# ── Tracker ──────────────────────────────────────────────────────────────────


class DirtyNoteTracker:
    """Thread-safe set of notes awaiting re-ingestion."""

    def __init__(self) -> None:
        # note_id → monotonic timestamp of last edit
        self._dirty: dict[str, float] = {}
        self._lock = threading.Lock()
        self._sweep_task: asyncio.Task | None = None

    # -- mutators (called from sync note endpoints) --

    def mark_dirty(self, note_id: str) -> None:
        """Record that *note_id* has changed and needs re-ingestion."""
        with self._lock:
            self._dirty[note_id] = time.monotonic()

    def clear(self, note_id: str) -> None:
        """Remove a single note from the dirty set (e.g. after deletion)."""
        with self._lock:
            self._dirty.pop(note_id, None)

    # -- queries --

    def is_dirty(self, note_id: str) -> bool:
        with self._lock:
            return note_id in self._dirty

    @property
    def dirty_count(self) -> int:
        with self._lock:
            return len(self._dirty)

    # -- bulk pop helpers --

    def pop_all(self) -> Set[str]:
        """Atomically remove and return *all* dirty note IDs."""
        with self._lock:
            ids = set(self._dirty)
            self._dirty.clear()
            return ids

    def pop_stale(self, threshold: float = INACTIVITY_S) -> Set[str]:
        """Remove and return note IDs idle longer than *threshold* seconds."""
        now = time.monotonic()
        with self._lock:
            stale = {
                nid
                for nid, ts in self._dirty.items()
                if now - ts >= threshold
            }
            for nid in stale:
                del self._dirty[nid]
            return stale


# ── Module-level singleton ───────────────────────────────────────────────────

_tracker = DirtyNoteTracker()


def get_tracker() -> DirtyNoteTracker:
    return _tracker


def mark_dirty(note_id: str) -> None:
    """Convenience shortcut used by note endpoints."""
    _tracker.mark_dirty(note_id)


# ── Flush helpers (async — called from query endpoints / sweep) ──────────────


async def _ingest_notes(note_ids: Set[str]) -> int:
    """Insert the given notes into LightRAG. Returns count ingested."""
    if not note_ids:
        return 0

    from app.ai.lightrag_service import insert_notes_batch
    from app.database import engine
    from app.models import Note
    from sqlmodel import Session

    with Session(engine) as session:
        payload = []
        for nid in note_ids:
            note = session.get(Note, nid)
            if note and note.content and note.content.strip():
                payload.append(
                    {
                        "note_id": note.id,
                        "title": note.title,
                        "content": note.content,
                    }
                )

    if not payload:
        return 0

    result = await insert_notes_batch(payload)
    count = int(result.get("indexed", 0))
    logger.info("Flushed %d dirty note(s) into LightRAG", count)
    return count


async def flush_stale_notes() -> int:
    """Ingest notes that have been idle longer than the threshold."""
    stale = _tracker.pop_stale()
    return await _ingest_notes(stale)


async def ensure_all_indexed() -> int:
    """Flush *every* dirty note — call before any RAG query."""
    ids = _tracker.pop_all()
    if not ids:
        return 0
    logger.info("Pre-query flush: ingesting %d dirty note(s)", len(ids))
    return await _ingest_notes(ids)


# ── Background sweep loop ───────────────────────────────────────────────────


async def _sweep_loop() -> None:
    """Periodically ingest notes idle longer than INACTIVITY_S."""
    while True:
        try:
            await asyncio.sleep(SWEEP_INTERVAL_S)
            await flush_stale_notes()
        except asyncio.CancelledError:
            # App is shutting down — flush whatever remains
            remaining = _tracker.pop_all()
            if remaining:
                try:
                    await _ingest_notes(remaining)
                except Exception:
                    logger.warning("Failed to flush dirty notes on shutdown")
            raise
        except Exception:
            logger.exception("Error in ingestion sweep loop")


def start_sweep() -> asyncio.Task:
    """Start the background sweep task (call once at app startup)."""
    task = asyncio.ensure_future(_sweep_loop())
    _tracker._sweep_task = task
    return task


async def stop_sweep() -> None:
    """Cancel the sweep and flush remaining dirty notes."""
    if _tracker._sweep_task:
        _tracker._sweep_task.cancel()
        try:
            await _tracker._sweep_task
        except asyncio.CancelledError:
            pass
        _tracker._sweep_task = None
