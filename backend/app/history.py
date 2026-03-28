"""History API routes — browse and restore note versions via git."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.git_service import get_git_service
from app.models import Note
from app.notes import _note_disk_path, _write_note_file

router = APIRouter(prefix="/api/notes", tags=["history"])


class VersionEntry(BaseModel):
    sha: str
    short_sha: str
    message: str
    author: str
    timestamp: str


class VersionContent(BaseModel):
    sha: str
    content: str


class DiffResponse(BaseModel):
    sha: str
    diff: str


class RestoreRequest(BaseModel):
    sha: str


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/{note_id}/history", response_model=list[VersionEntry])
def get_note_history(
    note_id: str,
    max_count: int = 50,
    session: Session = Depends(get_session),
):
    """Return the commit history for a note."""
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    gs = get_git_service()
    path = _note_disk_path(note, session)
    return gs.get_file_history(path, max_count=max_count)


@router.get("/{note_id}/versions/{sha}", response_model=VersionContent)
def get_note_version(
    note_id: str,
    sha: str,
    session: Session = Depends(get_session),
):
    """Return the content of a note at a specific commit."""
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    gs = get_git_service()
    path = _note_disk_path(note, session)
    content = gs.get_file_at_commit(path, sha)
    if content is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return VersionContent(sha=sha, content=content)


@router.get("/{note_id}/diff/{sha}", response_model=DiffResponse)
def get_note_diff(
    note_id: str,
    sha: str,
    session: Session = Depends(get_session),
):
    """Return the unified diff for a note at a specific commit."""
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    gs = get_git_service()
    path = _note_disk_path(note, session)
    diff = gs.get_diff(path, sha)
    if diff is None:
        raise HTTPException(status_code=404, detail="Diff not available")
    return DiffResponse(sha=sha, diff=diff)


@router.post("/{note_id}/restore", status_code=200)
def restore_note_version(
    note_id: str,
    body: RestoreRequest,
    session: Session = Depends(get_session),
):
    """Restore a note to a previous version's content."""
    from datetime import datetime, timezone

    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    gs = get_git_service()
    path = _note_disk_path(note, session)
    content = gs.get_file_at_commit(path, body.sha)
    if content is None:
        raise HTTPException(status_code=404, detail="Version not found")

    # Update the note content
    note.content = content
    note.updated_at = datetime.now(timezone.utc)
    session.add(note)
    session.commit()
    session.refresh(note)

    # Write file and commit
    _write_note_file(note, session)
    gs.commit_note(path, f"[restore] {note.title} to {body.sha[:7]}")

    return note
