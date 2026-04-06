"""LightRAG service — graph-augmented retrieval over the note vault.

Provides a singleton async LightRAG instance that builds a knowledge graph
from note content, supporting hybrid (local + global) queries with entity
and relationship extraction.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional

import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

from app.config import get_settings

logger = logging.getLogger(__name__)

_rag_instance: LightRAG | None = None
_rag_lock = asyncio.Lock()


def _build_llm_func():
    """Build the LLM completion function for LightRAG entity extraction and query."""
    settings = get_settings()

    async def llm_func(
        prompt: str,
        system_prompt: str | None = None,
        history_messages: list[dict] | None = None,
        **kwargs,
    ) -> str:
        return await openai_complete_if_cache(
            settings.llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            api_key=settings.openai_api_key,
            **kwargs,
        )

    return llm_func


def _build_embedding_func() -> EmbeddingFunc:
    """Build the embedding function for LightRAG vector storage."""
    settings = get_settings()
    return EmbeddingFunc(
        embedding_dim=settings.embedding_dimension,
        max_token_size=8192,
        func=lambda texts: openai_embed(
            texts,
            model=settings.embedding_openai_model,
            api_key=settings.openai_api_key,
        ),
    )


async def get_lightrag() -> LightRAG:
    """Return the singleton LightRAG instance, initializing on first call."""
    global _rag_instance

    if _rag_instance is not None:
        return _rag_instance

    async with _rag_lock:
        if _rag_instance is not None:
            return _rag_instance

        settings = get_settings()
        working_dir = str(Path(settings.lightrag_working_dir).expanduser().resolve())
        Path(working_dir).mkdir(parents=True, exist_ok=True)

        rag = LightRAG(
            working_dir=working_dir,
            llm_model_func=_build_llm_func(),
            embedding_func=_build_embedding_func(),
            chunk_token_size=settings.lightrag_chunk_token_size,
            chunk_overlap_token_size=settings.lightrag_chunk_overlap_token_size,
        )
        await rag.initialize_storages()
        _rag_instance = rag
        logger.info("LightRAG instance initialized at %s", working_dir)
        return _rag_instance


async def shutdown_lightrag() -> None:
    """Gracefully finalize LightRAG storages on app shutdown."""
    global _rag_instance
    if _rag_instance is not None:
        await _rag_instance.finalize_storages()
        _rag_instance = None
        logger.info("LightRAG instance shut down")


# ── Document insertion ────────────────────────────────────────────────────────


async def insert_text(
    text: str,
    doc_id: str | None = None,
) -> dict:
    """Insert plain text content into the LightRAG knowledge graph.

    Returns metadata about the insertion.
    """
    rag = await get_lightrag()
    kwargs = {}
    if doc_id:
        kwargs["ids"] = [doc_id]

    await rag.ainsert(text, **kwargs)
    return {"status": "indexed", "doc_id": doc_id}


async def insert_note(
    note_id: str,
    title: str,
    content: str,
) -> dict:
    """Insert a note's content into the knowledge graph with its ID."""
    if not content or not content.strip():
        return {"status": "skipped", "note_id": note_id, "reason": "empty content"}

    # Prepend the title for better entity extraction context
    text = f"# {title}\n\n{content}" if title else content
    return await insert_text(text, doc_id=note_id)


async def insert_notes_batch(
    notes: list[dict],
) -> dict:
    """Insert multiple notes in batch.

    Each dict should have keys: note_id, title, content.
    """
    rag = await get_lightrag()
    texts = []
    ids = []
    skipped = 0

    for note in notes:
        content = note.get("content", "").strip()
        if not content:
            skipped += 1
            continue
        title = note.get("title", "")
        text = f"# {title}\n\n{content}" if title else content
        texts.append(text)
        ids.append(note["note_id"])

    if texts:
        await rag.ainsert(texts, ids=ids)

    return {
        "status": "indexed",
        "indexed": len(texts),
        "skipped": skipped,
    }


# ── Querying ──────────────────────────────────────────────────────────────────


async def query(
    question: str,
    mode: str = "hybrid",
    conversation_history: list[dict] | None = None,
    response_type: str = "Multiple Paragraphs",
    top_k: int | None = None,
) -> str:
    """Query the knowledge graph and return a synthesized answer."""
    settings = get_settings()
    rag = await get_lightrag()

    param = QueryParam(
        mode=mode,
        top_k=top_k or settings.lightrag_top_k,
        response_type=response_type,
        conversation_history=conversation_history or [],
    )

    result = await rag.aquery(question, param=param)
    return result


async def query_stream(
    question: str,
    mode: str = "hybrid",
    conversation_history: list[dict] | None = None,
    response_type: str = "Multiple Paragraphs",
    top_k: int | None = None,
) -> AsyncGenerator[str, None]:
    """Stream a query response as SSE events.

    Yields:
        SSE-formatted strings with type: text_delta, source_entities, done
    """
    settings = get_settings()
    rag = await get_lightrag()

    param = QueryParam(
        mode=mode,
        stream=True,
        top_k=top_k or settings.lightrag_top_k,
        response_type=response_type,
        conversation_history=conversation_history or [],
    )

    response = await rag.aquery(question, param=param)

    async for chunk in response:
        if chunk:
            yield f"data: {json.dumps({'type': 'text_delta', 'delta': chunk})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def query_with_context(
    question: str,
    mode: str = "hybrid",
    top_k: int | None = None,
) -> dict:
    """Query and return both the answer and the raw retrieved context.

    Useful for entity extraction and analysis modes.
    """
    settings = get_settings()
    rag = await get_lightrag()

    # Get just the context (no LLM generation)
    context_param = QueryParam(
        mode=mode,
        top_k=top_k or settings.lightrag_top_k,
        only_need_context=True,
    )
    context = await rag.aquery(question, param=context_param)

    # Get the full answer
    answer_param = QueryParam(
        mode=mode,
        top_k=top_k or settings.lightrag_top_k,
        response_type="Multiple Paragraphs",
    )
    answer = await rag.aquery(question, param=answer_param)

    return {
        "answer": answer,
        "context": context,
    }


# ── Knowledge graph operations ────────────────────────────────────────────────


async def get_knowledge_graph_stats() -> dict:
    """Return statistics about the current knowledge graph."""
    rag = await get_lightrag()

    try:
        # Access the graph storage for stats
        graph = rag.chunk_entity_relation_graph
        if hasattr(graph, '_graph'):
            g = graph._graph
            return {
                "entities": g.number_of_nodes(),
                "relations": g.number_of_edges(),
            }
    except Exception as exc:
        logger.warning("Could not read KG stats: %s", exc)

    return {"entities": 0, "relations": 0}


async def extract_entities(
    question: str,
    mode: str = "local",
) -> dict:
    """Extract entities relevant to a query using local graph search."""
    rag = await get_lightrag()

    param = QueryParam(
        mode=mode,
        only_need_context=True,
        top_k=30,
    )
    context = await rag.aquery(question, param=param)

    return {
        "query": question,
        "mode": mode,
        "context": context,
    }


async def delete_document(doc_id: str) -> dict:
    """Delete a document and its entities from the knowledge graph."""
    rag = await get_lightrag()
    try:
        await rag.adelete_by_doc_id(doc_id)
        return {"status": "deleted", "doc_id": doc_id}
    except Exception as exc:
        logger.error("Failed to delete document %s: %s", doc_id, exc)
        return {"status": "error", "doc_id": doc_id, "error": str(exc)}
