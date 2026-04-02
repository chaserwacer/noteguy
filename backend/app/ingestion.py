"""Document ingestion pipeline — splits notes into chunks and indexes embeddings.

Chunks are split on headings first, then subdivided to ~400 tokens with
80 token overlap.  Each chunk stores rich metadata for folder-scoped retrieval.

All ingestion endpoints dispatch work as background tasks so the API
response returns immediately.
"""

import hashlib
import io
import re
from typing import Optional

import tiktoken
from docx import Document as DocxDocument
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select

from app.database import get_session
from app.models import Note, Folder
from app.vector_store import get_collection

router = APIRouter(prefix="/api", tags=["ingestion"])

# ── Chunking parameters ──────────────────────────────────────────────────────

TARGET_TOKENS = 400
OVERLAP_TOKENS = 80

_enc = tiktoken.get_encoding("cl100k_base")


def _token_len(text: str) -> int:
    return len(_enc.encode(text))


# ── Heading-aware chunking ───────────────────────────────────────────────────

_HEADING_RE = re.compile(r"^(#{1,6})\s", re.MULTILINE)


def _split_on_headings(text: str) -> list[str]:
    """Split markdown text on heading boundaries."""
    positions = [m.start() for m in _HEADING_RE.finditer(text)]
    if not positions:
        return [text] if text.strip() else []

    # If there is content before the first heading, include it
    if positions[0] > 0:
        positions = [0] + positions

    sections: list[str] = []
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        section = text[start:end].strip()
        if section:
            sections.append(section)
    return sections


def _subdivide_section(section: str) -> list[str]:
    """Split a section into ~TARGET_TOKENS chunks with OVERLAP_TOKENS overlap.

    Splits on paragraph boundaries (double newline) for cleaner chunks.
    """
    tokens = _enc.encode(section)
    if len(tokens) <= TARGET_TOKENS:
        return [section]

    paragraphs = re.split(r"\n\n+", section)
    chunks: list[str] = []
    current_paragraphs: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _token_len(para)
        if current_tokens + para_tokens > TARGET_TOKENS and current_paragraphs:
            chunks.append("\n\n".join(current_paragraphs))
            # Keep overlap: walk backwards until we have ~OVERLAP_TOKENS
            overlap_paragraphs: list[str] = []
            overlap_count = 0
            for p in reversed(current_paragraphs):
                t = _token_len(p)
                if overlap_count + t > OVERLAP_TOKENS:
                    break
                overlap_paragraphs.insert(0, p)
                overlap_count += t
            current_paragraphs = overlap_paragraphs
            current_tokens = overlap_count

        current_paragraphs.append(para)
        current_tokens += para_tokens

    if current_paragraphs:
        chunks.append("\n\n".join(current_paragraphs))

    return chunks


def chunk_markdown(text: str) -> list[str]:
    """Split markdown into embedding-ready chunks.

    1. Split on headings
    2. Subdivide large sections into ~400 token chunks with 80 token overlap
    """
    sections = _split_on_headings(text)
    if not sections:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    for section in sections:
        chunks.extend(_subdivide_section(section))
    return chunks


# ── Deterministic chunk IDs ──────────────────────────────────────────────────


def _chunk_id(note_id: str, chunk_index: int) -> str:
    raw = f"{note_id}::chunk::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Core ingest / remove ─────────────────────────────────────────────────────


def _resolve_folder_meta(
    folder_id: Optional[str], session: Session
) -> tuple[str, str]:
    """Return (folder_id_str, folder_path) for chunk metadata."""
    if not folder_id:
        return ("", "")
    folder = session.get(Folder, folder_id)
    if not folder:
        return (folder_id, "")
    return (folder_id, folder.path or "")


def ingest_note_sync(note_id: str, session: Session) -> int:
    """Index a single note's chunks into ChromaDB.

    Deletes any existing chunks for this note first, then re-embeds.
    Returns the number of chunks indexed.
    """
    note = session.get(Note, note_id)
    if not note:
        return 0

    collection = get_collection()

    # Remove old chunks
    old = collection.get(where={"note_id": note_id})
    if old["ids"]:
        collection.delete(ids=old["ids"])

    if not note.content or not note.content.strip():
        return 0

    chunks = chunk_markdown(note.content)
    folder_id_str, folder_path = _resolve_folder_meta(note.folder_id, session)

    ids = [_chunk_id(note_id, i) for i in range(len(chunks))]
    metadatas = [
        {
            "note_id": note_id,
            "folder_id": folder_id_str,
            "folder_path": folder_path,
            "note_title": note.title or "Untitled",
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
    return len(chunks)


def remove_note_chunks(note_id: str) -> None:
    """Remove all chunks belonging to a note from the vector store."""
    collection = get_collection()
    results = collection.get(where={"note_id": note_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])


def ingest_all_sync(session: Session) -> int:
    """Re-index every note in the vault. Returns total chunks indexed."""
    notes = session.exec(select(Note)).all()
    total = 0
    for note in notes:
        total += ingest_note_sync(note.id, session)
    return total


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
        prefix = _DOCX_HEADING_MAP.get(para.style.name, "")
        lines.append(f"{prefix}{text}")
    return "\n\n".join(lines)


# ── API endpoints ────────────────────────────────────────────────────────────


def _bg_ingest_note(note_id: str) -> None:
    """Background task wrapper — opens its own session."""
    from app.database import engine
    with Session(engine) as session:
        ingest_note_sync(note_id, session)


def _bg_ingest_all() -> None:
    """Background task wrapper — opens its own session."""
    from app.database import engine
    with Session(engine) as session:
        ingest_all_sync(session)


@router.post("/ingest/note/{note_id}")
def ingest_note_endpoint(
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
def ingest_all_endpoint(background_tasks: BackgroundTasks):
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
