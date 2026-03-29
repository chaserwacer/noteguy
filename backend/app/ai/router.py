"""FastAPI router exposing all AI framework integrations.

Provides endpoints grouped by framework:

    /api/ai/langchain/*    — LangChain RAG pipeline
    /api/ai/llama-index/*  — LlamaIndex query engine
    /api/ai/crewai/*       — CrewAI multi-agent crews
    /api/ai/dspy/*         — DSPy optimised modules
    /api/ai/instructor/*   — Instructor structured extraction
    /api/ai/mem0/*         — Mem0 memory layer
    /api/ai/pydantic-ai/*  — PydanticAI typed agents
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models import Note
from app.rag import retrieve_context

router = APIRouter(prefix="/api/ai", tags=["ai-frameworks"])


# ── Shared request / response schemas ──────────────────────────────────────


class AskRequest(BaseModel):
    question: str
    folder_scope: Optional[str] = None
    provider: str = "anthropic"


class NoteContentRequest(BaseModel):
    note_id: str
    provider: str = "anthropic"


class ContentRequest(BaseModel):
    content: str
    provider: str = "anthropic"


class CrewResearchRequest(BaseModel):
    question: str
    provider: str = "anthropic"


class CrewWriteRequest(BaseModel):
    topic: str
    provider: str = "anthropic"


class MemoryAddRequest(BaseModel):
    content: str
    user_id: str = "default"


class MemorySearchRequest(BaseModel):
    query: str
    user_id: str = "default"
    limit: int = 5


class MemoryChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    conversation_history: list[dict] = []
    provider: str = "anthropic"


class ConnectionRequest(BaseModel):
    note_id: str
    provider: str = "anthropic"


# ── Helper to get note content ─────────────────────────────────────────────


def _get_note_content(note_id: str, session: Session) -> str:
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note.content or ""


def _get_notes_context(question: str, folder_scope: Optional[str] = None) -> str:
    """Retrieve context chunks and format as a text block."""
    chunks = retrieve_context(question, folder_scope=folder_scope)
    return "\n\n---\n\n".join(
        f"[{c['note_title']}]\n{c['content']}" for c in chunks
    )


# ── Frameworks info endpoint ───────────────────────────────────────────────


@router.get("/frameworks")
def list_frameworks():
    """List all available AI framework integrations and their capabilities."""
    return {
        "frameworks": [
            {
                "id": "langchain",
                "name": "LangChain",
                "description": "RAG pipeline with composable chains and retrievers",
                "capabilities": ["ask", "stream", "ingest"],
                "category": "orchestration",
            },
            {
                "id": "llama_index",
                "name": "LlamaIndex",
                "description": "Document indexing and query engine",
                "capabilities": ["query", "ingest"],
                "category": "data_layer",
            },
            {
                "id": "crewai",
                "name": "CrewAI",
                "description": "Multi-agent system for research, summarisation, and writing",
                "capabilities": ["research", "summarise", "write"],
                "category": "orchestration",
            },
            {
                "id": "dspy",
                "name": "DSPy",
                "description": "Programmatic RAG optimisation with learnable modules",
                "capabilities": ["ask", "summarise", "extract_topics"],
                "category": "orchestration",
            },
            {
                "id": "instructor",
                "name": "Instructor",
                "description": "Structured data extraction with Pydantic validation",
                "capabilities": ["tags", "entities", "summary"],
                "category": "data_layer",
            },
            {
                "id": "mem0",
                "name": "Mem0",
                "description": "Persistent memory layer for conversational context",
                "capabilities": ["add", "search", "chat", "clear"],
                "category": "data_layer",
            },
            {
                "id": "pydantic_ai",
                "name": "PydanticAI",
                "description": "Type-safe agent framework with structured schemas",
                "capabilities": ["qa", "enhance", "connections"],
                "category": "orchestration",
            },
        ]
    }


# ── LangChain endpoints ───────────────────────────────────────────────────


@router.post("/langchain/ask")
def langchain_ask_endpoint(body: AskRequest):
    """Answer a question using the LangChain RetrievalQA chain."""
    from app.ai.langchain_rag import langchain_ask
    return langchain_ask(
        question=body.question,
        folder_scope=body.folder_scope,
        provider=body.provider,
    )


@router.post("/langchain/stream")
def langchain_stream_endpoint(body: AskRequest):
    """Stream an answer using LangChain with SSE."""
    from app.ai.langchain_rag import langchain_ask_stream
    return StreamingResponse(
        langchain_ask_stream(
            question=body.question,
            folder_scope=body.folder_scope,
            provider=body.provider,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── LlamaIndex endpoints ──────────────────────────────────────────────────


@router.post("/llama-index/query")
def llama_index_query_endpoint(body: AskRequest):
    """Query notes using the LlamaIndex query engine."""
    from app.ai.llama_index_query import llama_index_query
    return llama_index_query(
        question=body.question,
        folder_scope=body.folder_scope,
        provider=body.provider,
    )


@router.post("/llama-index/ingest")
def llama_index_ingest_endpoint(
    body: NoteContentRequest,
    session: Session = Depends(get_session),
):
    """Ingest a note into the LlamaIndex vector store."""
    from app.ai.llama_index_query import llama_index_ingest_note
    content = _get_note_content(body.note_id, session)
    note = session.get(Note, body.note_id)
    metadata = {
        "note_title": note.title if note else "Untitled",
        "note_id": body.note_id,
    }
    count = llama_index_ingest_note(body.note_id, content, metadata)
    return {"status": "ingested", "chunks": count, "framework": "llama_index"}


# ── CrewAI endpoints ──────────────────────────────────────────────────────


@router.post("/crewai/research")
def crewai_research_endpoint(body: CrewResearchRequest):
    """Run a CrewAI research crew to analyse notes."""
    from app.ai.crew_agents import run_research_crew
    context = _get_notes_context(body.question)
    return run_research_crew(
        question=body.question,
        notes_context=context,
        provider=body.provider,
    )


@router.post("/crewai/summarise")
def crewai_summarise_endpoint(
    body: NoteContentRequest,
    session: Session = Depends(get_session),
):
    """Run a CrewAI summarisation crew on a note."""
    from app.ai.crew_agents import run_summary_crew
    content = _get_note_content(body.note_id, session)
    return run_summary_crew(content=content, provider=body.provider)


@router.post("/crewai/write")
def crewai_write_endpoint(body: CrewWriteRequest):
    """Run a CrewAI writing crew to generate new content."""
    from app.ai.crew_agents import run_writing_crew
    context = _get_notes_context(body.topic)
    return run_writing_crew(
        topic=body.topic,
        notes_context=context,
        provider=body.provider,
    )


# ── DSPy endpoints ─────────────────────────────────────────────────────────


@router.post("/dspy/ask")
def dspy_ask_endpoint(body: AskRequest):
    """Answer a question using the DSPy ChainOfThought RAG module."""
    from app.ai.dspy_rag import dspy_ask
    chunks = retrieve_context(body.question, folder_scope=body.folder_scope)
    return dspy_ask(
        question=body.question,
        context_chunks=chunks,
        provider=body.provider,
    )


@router.post("/dspy/summarise")
def dspy_summarise_endpoint(
    body: NoteContentRequest,
    session: Session = Depends(get_session),
):
    """Summarise a note using DSPy's structured output module."""
    from app.ai.dspy_rag import dspy_summarise
    content = _get_note_content(body.note_id, session)
    return dspy_summarise(content=content, provider=body.provider)


@router.post("/dspy/topics")
def dspy_topics_endpoint(
    body: NoteContentRequest,
    session: Session = Depends(get_session),
):
    """Extract topics from a note using DSPy."""
    from app.ai.dspy_rag import dspy_extract_topics
    content = _get_note_content(body.note_id, session)
    return dspy_extract_topics(content=content, provider=body.provider)


# ── Instructor endpoints ──────────────────────────────────────────────────


@router.post("/instructor/tags")
def instructor_tags_endpoint(
    body: NoteContentRequest,
    session: Session = Depends(get_session),
):
    """Extract structured tags and metadata from a note."""
    from app.ai.structured import extract_tags
    content = _get_note_content(body.note_id, session)
    return extract_tags(content=content, provider=body.provider)


@router.post("/instructor/entities")
def instructor_entities_endpoint(
    body: NoteContentRequest,
    session: Session = Depends(get_session),
):
    """Extract named entities from a note."""
    from app.ai.structured import extract_entities
    content = _get_note_content(body.note_id, session)
    return extract_entities(content=content, provider=body.provider)


@router.post("/instructor/summary")
def instructor_summary_endpoint(
    body: NoteContentRequest,
    session: Session = Depends(get_session),
):
    """Generate a structured summary with action items."""
    from app.ai.structured import extract_summary
    content = _get_note_content(body.note_id, session)
    return extract_summary(content=content, provider=body.provider)


# ── Mem0 endpoints ─────────────────────────────────────────────────────────


@router.post("/mem0/add")
def mem0_add_endpoint(body: MemoryAddRequest):
    """Store a new memory."""
    from app.ai.memory import add_memory
    return add_memory(content=body.content, user_id=body.user_id)


@router.post("/mem0/search")
def mem0_search_endpoint(body: MemorySearchRequest):
    """Search for relevant memories."""
    from app.ai.memory import search_memories
    results = search_memories(
        query=body.query, user_id=body.user_id, limit=body.limit,
    )
    return {"memories": results, "framework": "mem0"}


@router.get("/mem0/memories")
def mem0_list_endpoint(user_id: str = "default"):
    """List all memories for a user."""
    from app.ai.memory import get_all_memories
    results = get_all_memories(user_id=user_id)
    return {"memories": results, "framework": "mem0"}


@router.post("/mem0/chat")
def mem0_chat_endpoint(body: MemoryChatRequest):
    """Chat with memory-augmented context."""
    from app.ai.memory import chat_with_memory
    return chat_with_memory(
        message=body.message,
        user_id=body.user_id,
        conversation_history=body.conversation_history,
        provider=body.provider,
    )


@router.delete("/mem0/memories")
def mem0_clear_endpoint(user_id: str = "default"):
    """Clear all memories for a user."""
    from app.ai.memory import clear_memories
    return clear_memories(user_id=user_id)


# ── PydanticAI endpoints ──────────────────────────────────────────────────


@router.post("/pydantic-ai/ask")
def pydantic_ai_ask_endpoint(body: AskRequest):
    """Answer a question using the PydanticAI QA agent."""
    from app.ai.pydantic_agent import note_qa_agent
    context = _get_notes_context(body.question, body.folder_scope)
    return note_qa_agent(
        question=body.question,
        notes_context=context,
        provider=body.provider,
    )


@router.post("/pydantic-ai/enhance")
def pydantic_ai_enhance_endpoint(
    body: NoteContentRequest,
    session: Session = Depends(get_session),
):
    """Enhance a note using the PydanticAI enhancement agent."""
    from app.ai.pydantic_agent import note_enhancement_agent
    content = _get_note_content(body.note_id, session)
    return note_enhancement_agent(content=content, provider=body.provider)


@router.post("/pydantic-ai/connections")
def pydantic_ai_connections_endpoint(
    body: NoteContentRequest,
    session: Session = Depends(get_session),
):
    """Find connections between a note and the rest of the vault."""
    from app.ai.pydantic_agent import note_connection_agent
    content = _get_note_content(body.note_id, session)

    # Get all note titles for context
    all_notes = session.exec(select(Note)).all()
    titles = [n.title for n in all_notes if n.id != body.note_id]

    return note_connection_agent(
        content=content,
        all_titles=titles,
        provider=body.provider,
    )
