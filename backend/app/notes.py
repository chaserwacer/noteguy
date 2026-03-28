"""CRUD operations and API routes for notes and folders.

Notes are persisted as .md files on disk under the configured vault_path.
SQLite tracks metadata and the folder tree; the files are the source of truth.
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models import Note, Folder

router = APIRouter(prefix="/api", tags=["notes"])


# ── Background ingestion helpers ─────────────────────────────────────────────


def _schedule_ingest(background_tasks: BackgroundTasks, note_id: str) -> None:
    """Schedule async ingestion of a note into the vector store."""
    from app.ingestion import _bg_ingest_note
    background_tasks.add_task(_bg_ingest_note, note_id)


def _bg_remove_chunks(note_id: str) -> None:
    """Remove all vector chunks for a deleted note."""
    from app.ingestion import remove_note_chunks
    remove_note_chunks(note_id)


# ── Vault file helpers ──────────────────────────────────────────────────────


def _vault_path() -> Path:
    """Return the absolute vault root directory."""
    return Path(get_settings().vault_path)


def _note_disk_path(note: Note, session: Session) -> Path:
    """Return the absolute .md file path for a note."""
    if note.folder_id:
        folder = session.get(Folder, note.folder_id)
        if folder and folder.path:
            return _vault_path() / folder.path / f"{note.id}.md"
    return _vault_path() / f"{note.id}.md"


def _write_note_file(note: Note, session: Session) -> None:
    """Write note content to its .md file on disk."""
    path = _note_disk_path(note, session)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(note.content, encoding="utf-8")


def _delete_note_file(note: Note, session: Session) -> None:
    """Remove a note's .md file from disk if it exists."""
    path = _note_disk_path(note, session)
    if path.exists():
        path.unlink()


def _compute_folder_path(
    folder_name: str, parent_id: Optional[str], session: Session
) -> str:
    """Build the materialised path for a folder from its ancestors."""
    if not parent_id:
        return folder_name
    parent = session.get(Folder, parent_id)
    if not parent:
        return folder_name
    return f"{parent.path}/{folder_name}" if parent.path else folder_name


def _get_descendant_folder_ids(folder_id: str, session: Session) -> List[str]:
    """Recursively collect all descendant folder IDs."""
    children = session.exec(
        select(Folder).where(Folder.parent_id == folder_id)
    ).all()
    ids: List[str] = []
    for child in children:
        ids.append(child.id)
        ids.extend(_get_descendant_folder_ids(child.id, session))
    return ids


def _update_descendant_paths(folder_id: str, session: Session) -> None:
    """Recursively recompute paths of all descendant folders."""
    children = session.exec(
        select(Folder).where(Folder.parent_id == folder_id)
    ).all()
    for child in children:
        child.path = _compute_folder_path(child.name, child.parent_id, session)
        child.updated_at = datetime.now(timezone.utc)
        session.add(child)
        _update_descendant_paths(child.id, session)
    session.commit()


# ── Request / Response Schemas ──────────────────────────────────────────────


class NoteCreate(BaseModel):
    """Payload for creating a new note."""

    title: str = "Untitled"
    content: str = ""
    folder_id: Optional[str] = None


class NoteUpdate(BaseModel):
    """Payload for updating an existing note."""

    title: Optional[str] = None
    content: Optional[str] = None
    folder_id: Optional[str] = None


class FolderCreate(BaseModel):
    """Payload for creating a new folder."""

    name: str
    parent_id: Optional[str] = None


class FolderUpdate(BaseModel):
    """Payload for renaming or moving a folder."""

    name: Optional[str] = None
    parent_id: Optional[str] = None


# ── Note Endpoints ──────────────────────────────────────────────────────────


@router.get("/notes")
def list_notes(
    folder_id: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Return all notes, optionally filtered by folder."""
    query = select(Note)
    if folder_id is not None:
        query = query.where(Note.folder_id == folder_id)
    return session.exec(query.order_by(Note.updated_at.desc())).all()


@router.post("/notes", status_code=201)
def create_note(
    body: NoteCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Create a new note and write its .md file to the vault."""
    note = Note(**body.model_dump())
    session.add(note)
    session.commit()
    session.refresh(note)
    _write_note_file(note, session)
    _schedule_ingest(background_tasks, note.id)
    return note


@router.get("/notes/{note_id}")
def get_note(note_id: str, session: Session = Depends(get_session)):
    """Return a single note by ID."""
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def _do_update_note(
    note_id: str,
    body: NoteUpdate,
    session: Session,
    background_tasks: BackgroundTasks,
) -> Note:
    """Shared logic for PATCH and PUT note updates."""
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    old_folder_id = note.folder_id
    updates = body.model_dump(exclude_unset=True)

    # If the folder changed, remove the old .md file first
    if "folder_id" in updates and updates["folder_id"] != old_folder_id:
        _delete_note_file(note, session)

    for field, value in updates.items():
        setattr(note, field, value)
    note.updated_at = datetime.now(timezone.utc)

    session.add(note)
    session.commit()
    session.refresh(note)
    _write_note_file(note, session)
    _schedule_ingest(background_tasks, note.id)
    return note


@router.patch("/notes/{note_id}")
def update_note(
    note_id: str,
    body: NoteUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Partially update a note and sync its .md file."""
    return _do_update_note(note_id, body, session, background_tasks)


@router.put("/notes/{note_id}")
def replace_note(
    note_id: str,
    body: NoteUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Update a note (PUT alias) and sync its .md file."""
    return _do_update_note(note_id, body, session, background_tasks)


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Delete a note and remove its .md file and vector chunks."""
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    _delete_note_file(note, session)
    session.delete(note)
    session.commit()
    background_tasks.add_task(_bg_remove_chunks, note_id)


# ── Folder Endpoints ────────────────────────────────────────────────────────


@router.get("/folders")
def list_folders(session: Session = Depends(get_session)):
    """Return all folders (flat list, client builds the tree)."""
    return session.exec(select(Folder).order_by(Folder.name)).all()


@router.post("/folders", status_code=201)
def create_folder(body: FolderCreate, session: Session = Depends(get_session)):
    """Create a folder in the database and on disk."""
    path = _compute_folder_path(body.name, body.parent_id, session)
    folder = Folder(name=body.name, parent_id=body.parent_id, path=path)
    session.add(folder)
    session.commit()
    session.refresh(folder)

    # Create directory on disk
    disk_path = _vault_path() / path
    disk_path.mkdir(parents=True, exist_ok=True)

    return folder


@router.get("/folders/{folder_id}/notes")
def list_folder_notes(folder_id: str, session: Session = Depends(get_session)):
    """Return all notes belonging to a specific folder."""
    folder = session.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return session.exec(
        select(Note)
        .where(Note.folder_id == folder_id)
        .order_by(Note.updated_at.desc())
    ).all()


@router.patch("/folders/{folder_id}")
def update_folder(
    folder_id: str, body: FolderUpdate, session: Session = Depends(get_session)
):
    """Rename or move a folder, updating its disk directory."""
    folder = session.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    old_path = folder.path
    updates = body.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(folder, field, value)

    # Recompute materialised path
    new_path = _compute_folder_path(folder.name, folder.parent_id, session)
    folder.path = new_path
    folder.updated_at = datetime.now(timezone.utc)

    session.add(folder)
    session.commit()
    session.refresh(folder)

    # Move directory on disk if path changed
    old_disk = _vault_path() / old_path
    new_disk = _vault_path() / new_path
    if old_disk.exists() and old_path != new_path:
        new_disk.parent.mkdir(parents=True, exist_ok=True)
        old_disk.rename(new_disk)
    else:
        new_disk.mkdir(parents=True, exist_ok=True)

    # Cascade path updates to descendants
    _update_descendant_paths(folder_id, session)

    return folder


@router.delete("/folders/{folder_id}", status_code=204)
def delete_folder(folder_id: str, session: Session = Depends(get_session)):
    """Recursively delete a folder, all its notes, sub-folders, and disk files."""
    folder = session.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Collect this folder + all descendants
    all_folder_ids = [folder_id] + _get_descendant_folder_ids(folder_id, session)

    # Delete every note inside those folders (files + DB rows)
    for fid in all_folder_ids:
        notes = session.exec(select(Note).where(Note.folder_id == fid)).all()
        for note in notes:
            _delete_note_file(note, session)
            session.delete(note)

    # Delete folder rows (deepest first to respect FK ordering)
    for fid in reversed(all_folder_ids):
        f = session.get(Folder, fid)
        if f:
            session.delete(f)

    session.commit()

    # Remove the entire directory tree from disk
    disk_path = _vault_path() / folder.path
    if disk_path.exists():
        shutil.rmtree(disk_path)
