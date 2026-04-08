"""Unified AI router — single entry point for all AI operations.

Exposes a streamlined API built on LightRAG (graph-augmented RAG) and
RAG-Anything (multimodal document processing). Replaces the previous
seven-framework router with a focused set of capabilities:

    /api/ai/query         — hybrid knowledge graph query
    /api/ai/query/stream  — streaming hybrid query (SSE)
    /api/ai/ingest/note   — index a note into the knowledge graph
    /api/ai/ingest/all    — re-index entire vault
    /api/ai/ingest/document — process multimodal document
    /api/ai/extract       — entity / relationship extraction
    /api/ai/analyze       — deep global analysis
    /api/ai/kg/stats      — knowledge graph statistics
    /api/ai/status        — system capabilities and status
"""

from __future__ import annotations

import json
import logging
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.database import get_session
from app.models import Note, Folder

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["ai"])


# ── Request / Response schemas ────────────────────────────────────────────────

QueryMode = Literal["naive", "local", "global", "hybrid", "mix"]


class QueryRequest(BaseModel):
    question: str
    mode: QueryMode = "hybrid"
    conversation_history: list[dict] = Field(default_factory=list)
    response_type: str = "Multiple Paragraphs"
    top_k: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    mode: str


class StreamQueryRequest(BaseModel):
    question: str
    mode: QueryMode = "hybrid"
    conversation_history: list[dict] = Field(default_factory=list)
    response_type: str = "Multiple Paragraphs"
    top_k: Optional[int] = None


class IngestNoteRequest(BaseModel):
    note_id: str


class IngestAllRequest(BaseModel):
    pass


class ExtractRequest(BaseModel):
    question: str
    mode: QueryMode = "local"


class AnalyzeRequest(BaseModel):
    question: str
    response_type: str = "Multiple Paragraphs"
    top_k: Optional[int] = None


class AnalyzeResponse(BaseModel):
    answer: str
    context: str | dict


class KGStatsResponse(BaseModel):
    entities: int
    relations: int


class DeleteDocRequest(BaseModel):
    doc_id: str


# ── Status endpoint ───────────────────────────────────────────────────────────


@router.get("/status")
async def ai_status():
    """Return current AI system capabilities and configuration."""
    from app.ai.raganything_service import is_available as ra_available
    from app.config import get_settings
    from app.embeddings import get_embedding_model_name

    settings = get_settings()

    return {
        "engine": "lightrag",
        "version": "1.0",
        "capabilities": [
            {
                "id": "chat",
                "name": "Chat",
                "description": "Conversational Q&A powered by graph-augmented retrieval",
                "icon": "chat",
            },
            {
                "id": "ingest",
                "name": "Document Ingestion",
                "description": "Index notes and documents into the knowledge graph",
                "icon": "upload",
            },
            {
                "id": "extract",
                "name": "Entity Extraction",
                "description": "Extract entities and relationships from your notes",
                "icon": "extract",
            },
            {
                "id": "analyze",
                "name": "Deep Analysis",
                "description": "Cross-document analysis using global knowledge graph traversal",
                "icon": "analyze",
            },
            {
                "id": "knowledge_graph",
                "name": "Knowledge Graph",
                "description": "Explore the entity-relationship graph built from your vault",
                "icon": "graph",
            },
        ],
        "config": {
            "llm_model": settings.llm_model,
            "embedding_model": get_embedding_model_name(),
            "embedding_dimension": settings.embedding_dimension,
            "raganything_available": ra_available(),
            "raganything_parser": settings.raganything_parser if ra_available() else None,
        },
    }


# ── Query endpoints ───────────────────────────────────────────────────────────


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(body: QueryRequest):
    """Query the knowledge graph using hybrid retrieval."""
    from app.ai.lightrag_service import query
    from app.ingestion_tracker import ensure_all_indexed

    await ensure_all_indexed()
    try:
        answer = await query(
            question=body.question,
            mode=body.mode,
            conversation_history=body.conversation_history,
            response_type=body.response_type,
            top_k=body.top_k,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return QueryResponse(answer=answer, mode=body.mode)


@router.post("/query/stream")
async def query_stream_endpoint(body: StreamQueryRequest):
    """Stream a knowledge graph query response via SSE."""
    from app.ai.lightrag_service import query_stream
    from app.ingestion_tracker import ensure_all_indexed

    try:
        await ensure_all_indexed()
    except Exception as exc:
        logger.error("Pre-query indexing failed: %s", exc)

    return StreamingResponse(
        query_stream(
            question=body.question,
            mode=body.mode,
            conversation_history=body.conversation_history,
            response_type=body.response_type,
            top_k=body.top_k,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Ingestion endpoints ──────────────────────────────────────────────────────


@router.post("/ingest/note")
async def ingest_note_endpoint(
    body: IngestNoteRequest,
    session: Session = Depends(get_session),
):
    """Index a single note into the LightRAG knowledge graph."""
    from app.ai.lightrag_service import insert_note

    note = session.get(Note, body.note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    result = await insert_note(
        note_id=note.id,
        title=note.title,
        content=note.content or "",
    )
    return result


@router.post("/ingest/all")
async def ingest_all_endpoint(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Re-index the entire vault into the knowledge graph (runs in background)."""
    from app.ai.lightrag_service import insert_notes_batch

    notes = session.exec(select(Note)).all()
    note_dicts = [
        {"note_id": n.id, "title": n.title, "content": n.content or ""}
        for n in notes
    ]

    async def _bg_ingest():
        result = await insert_notes_batch(note_dicts)
        logger.info("Vault re-index complete: %s", result)

    background_tasks.add_task(_bg_ingest)
    return {"status": "queued", "total_notes": len(note_dicts)}


@router.post("/ingest/document")
async def ingest_document_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(default=None),
    session: Session = Depends(get_session),
):
    """Upload and process a multimodal document via RAG-Anything.

    Supports: PDF, DOCX, PPTX, XLSX, images (JPG/PNG), MD, TXT.
    The document is saved, a note is created, and multimodal content
    is extracted and indexed into the knowledge graph.
    """
    from app.ai.raganything_service import is_available, process_document
    from app.ai.lightrag_service import insert_note
    import tempfile
    import os

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    filename_lower = file.filename.lower()
    file_bytes = await file.read()

    # For simple text formats, use LightRAG directly
    if filename_lower.endswith((".md", ".txt")):
        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded") from exc

        title = file.filename.rsplit(".", 1)[0]
        note = Note(title=title, content=content, folder_id=folder_id)
        session.add(note)
        session.commit()
        session.refresh(note)

        from app.notes import _write_note_file
        _write_note_file(note, session)

        result = await insert_note(note_id=note.id, title=note.title, content=content)
        return {**result, "note_id": note.id, "title": title}

    # For .docx, convert to markdown and index as text
    if filename_lower.endswith(".docx"):
        from app.ingestion import docx_to_markdown
        content = docx_to_markdown(file_bytes)
        title = file.filename.rsplit(".", 1)[0]

        note = Note(title=title, content=content, folder_id=folder_id)
        session.add(note)
        session.commit()
        session.refresh(note)

        from app.notes import _write_note_file
        _write_note_file(note, session)

        # Always index textual content so DOCX ingestion is resilient even if
        # optional multimodal parsing fails (e.g., missing LibreOffice).
        await insert_note(note_id=note.id, title=note.title, content=content)

        # If RAG-Anything is available, also process for multimodal entities
        if is_available():
            with tempfile.NamedTemporaryFile(
                suffix=".docx", delete=False
            ) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            async def _bg_process():
                try:
                    await process_document(tmp_path)
                except Exception as exc:
                    logger.error("DOCX multimodal processing failed for %s: %s", file.filename, exc)
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

            background_tasks.add_task(_bg_process)

        return {"status": "indexed", "note_id": note.id, "title": title}

    # For multimodal documents (PDF, PPTX, images, etc.), use RAG-Anything
    if not is_available():
        raise HTTPException(
            status_code=400,
            detail=f"RAG-Anything is not installed. Only .md, .txt, and .docx files are supported. "
                   f"Install raganything for {file.filename.rsplit('.', 1)[-1]} support.",
        )

    # Save to temp file for processing
    suffix = "." + file.filename.rsplit(".", 1)[-1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    title = file.filename.rsplit(".", 1)[0]

    # Create a note entry for tracking
    note = Note(
        title=title,
        content=f"[Multimodal document: {file.filename}]",
        folder_id=folder_id,
    )
    session.add(note)
    session.commit()
    session.refresh(note)

    async def _bg_process_multimodal():
        try:
            await process_document(tmp_path)
        except Exception as exc:
            logger.error("Multimodal processing failed for %s: %s", file.filename, exc)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    background_tasks.add_task(_bg_process_multimodal)

    return {
        "status": "queued",
        "note_id": note.id,
        "title": title,
        "processing": "multimodal",
    }


# ── Entity extraction endpoint ────────────────────────────────────────────────


@router.post("/extract")
async def extract_endpoint(body: ExtractRequest):
    """Extract entities and relationships relevant to a query.

    Uses local graph search to find specific entities and their
    immediate neighborhood in the knowledge graph.
    """
    from app.ai.lightrag_service import extract_entities
    from app.ingestion_tracker import ensure_all_indexed

    await ensure_all_indexed()
    result = await extract_entities(
        question=body.question,
        mode=body.mode,
    )
    return result


@router.post("/extract/note")
async def extract_note_entities(
    body: IngestNoteRequest,
    session: Session = Depends(get_session),
):
    """Extract entities from a specific note's content."""
    from app.ai.lightrag_service import extract_entities
    from app.ingestion_tracker import ensure_all_indexed

    await ensure_all_indexed()
    note = session.get(Note, body.note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    content = note.content or ""
    if not content.strip():
        return {"query": note.title, "mode": "local", "context": "", "note_id": body.note_id}

    result = await extract_entities(
        question=f"What are the key entities, concepts, and relationships in: {note.title}",
        mode="local",
    )
    result["note_id"] = body.note_id
    return result


# ── Deep analysis endpoint ────────────────────────────────────────────────────


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(body: AnalyzeRequest):
    """Perform deep cross-document analysis using global graph traversal.

    Uses the global query mode to leverage high-level community structures
    across the entire knowledge graph for comprehensive analysis.
    """
    from app.ai.lightrag_service import query_with_context
    from app.ingestion_tracker import ensure_all_indexed

    await ensure_all_indexed()
    try:
        result = await query_with_context(
            question=body.question,
            mode="global",
            top_k=body.top_k,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AnalyzeResponse(
        answer=result["answer"],
        context=result["context"],
    )


# ── Knowledge graph endpoints ─────────────────────────────────────────────────


@router.get("/kg/graph")
async def kg_graph_endpoint(limit: int = 200):
    """Export knowledge graph nodes and edges for visualization."""
    from app.ai.lightrag_service import get_knowledge_graph_data
    return await get_knowledge_graph_data(limit=limit)


@router.get("/kg/stats", response_model=KGStatsResponse)
async def kg_stats_endpoint():
    """Return knowledge graph statistics."""
    from app.ai.lightrag_service import get_knowledge_graph_stats
    stats = await get_knowledge_graph_stats()
    return KGStatsResponse(**stats)


@router.delete("/kg/document")
async def kg_delete_document(body: DeleteDocRequest):
    """Delete a document and its entities from the knowledge graph."""
    from app.ai.lightrag_service import delete_document
    return await delete_document(body.doc_id)
