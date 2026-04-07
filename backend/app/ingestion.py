"""Document ingestion pipeline — converts files and indexes notes into LightRAG.

These endpoints are retained for backward compatibility with older clients.
All indexing now targets the LightRAG knowledge graph.

IMPORTANT: All LightRAG operations are async.  Background tasks MUST be async
functions so FastAPI runs them in the same event loop as the LightRAG singleton.
Using ``asyncio.run()`` would create a separate event loop and break LightRAG's
internal worker queues.
"""

import io
import logging
from typing import Optional

from docx import Document as DocxDocument
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select

from app.database import get_session
from app.models import Note

router = APIRouter(prefix="/api", tags=["ingestion"])
logger = logging.getLogger(__name__)


# ── Core ingest / remove (async) ─────────────────────────────────────────────


async def ingest_note_async(note_id: str, session: Session) -> int:
    """Index a single note into LightRAG and return 1 when indexed."""
    note = session.get(Note, note_id)
    if not note:
        return 0

    if not note.content or not note.content.strip():
        return 0

    from app.ai.lightrag_service import insert_note

    await insert_note(
        note_id=note.id,
        title=note.title,
        content=note.content,
    )
    return 1


async def remove_note_chunks_async(note_id: str) -> None:
    """Remove all LightRAG knowledge linked to a note ID."""
    from app.ai.lightrag_service import delete_document

    await delete_document(note_id)


async def ingest_all_async(session: Session) -> int:
    """Re-index every note in the vault into LightRAG."""
    from app.ai.lightrag_service import insert_notes_batch

    notes = session.exec(select(Note)).all()
    payload = []
    for note in notes:
        if note.content and note.content.strip():
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
    return int(result.get("indexed", 0))


# ── Docx conversion ──────────────────────────────────────────────────────────

_DOCX_HEADING_MAP = {
    "Heading 1": "# ",
    "Heading 2": "## ",
    "Heading 3": "### ",
    "Heading 4": "#### ",
    "Heading 5": "##### ",
    "Heading 6": "###### ",
}


def docx_to_markdown(file_bytes: bytes) -> str:
    """Convert a .docx file to markdown text preserving heading hierarchy."""
    doc = DocxDocument(io.BytesIO(file_bytes))
    lines: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            lines.append("")
            continue
        style = getattr(para, "style", None)
        style_name = getattr(style, "name", None)
        prefix = _DOCX_HEADING_MAP.get(style_name or "", "")
        lines.append(f"{prefix}{text}")
    return "\n\n".join(lines)


# ── Async background tasks ───────────────────────────────────────────────────


async def _bg_ingest_note(note_id: str) -> None:
    """Async background task — runs in the same event loop as LightRAG."""
    from app.database import engine

    with Session(engine) as session:
        await ingest_note_async(note_id, session)


async def _bg_ingest_all() -> None:
    """Async background task — runs in the same event loop as LightRAG."""
    from app.database import engine

    with Session(engine) as session:
        await ingest_all_async(session)


# ── API endpoints ────────────────────────────────────────────────────────────


@router.post("/ingest/note/{note_id}")
async def ingest_note_endpoint(
    note_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Trigger ingestion for a single note (runs in background)."""
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    background_tasks.add_task(_bg_ingest_note, note_id)
    return {"status": "queued", "note_id": note_id}


@router.post("/ingest/all")
async def ingest_all_endpoint(background_tasks: BackgroundTasks):
    """Trigger a full vault re-index (runs in background)."""
    background_tasks.add_task(_bg_ingest_all)
    return {"status": "queued"}


@router.post("/ingest/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(default=None),
    session: Session = Depends(get_session),
):
    """Upload a .docx or .md file, create a note, and trigger ingestion."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    filename_lower = file.filename.lower()
    file_bytes = await file.read()

    if filename_lower.endswith(".docx"):
        md_content = docx_to_markdown(file_bytes)
    elif filename_lower.endswith(".md"):
        try:
            md_content = file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="Markdown files must be UTF-8 encoded",
            ) from exc
    else:
        raise HTTPException(
            status_code=400,
            detail="Only .docx and .md files are supported",
        )

    # Derive title from filename
    title = file.filename.rsplit(".", 1)[0]

    note = Note(title=title, content=md_content, folder_id=folder_id)
    session.add(note)
    session.commit()
    session.refresh(note)

    # Write .md file to disk
    from app.notes import _write_note_file
    _write_note_file(note, session)

    background_tasks.add_task(_bg_ingest_note, note.id)
    return {"status": "created", "note_id": note.id, "title": title}
