"""LightRAG service — graph-augmented retrieval over the note vault.

Provides a singleton async LightRAG instance that builds a knowledge graph
from note content, supporting hybrid (local + global) queries with entity
and relationship extraction.

Uses the OpenAI API for both LLM completions and embeddings.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional

import numpy as np
from openai import AsyncOpenAI
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc

from app.config import get_settings

logger = logging.getLogger(__name__)

_rag_instance: LightRAG | None = None
_rag_lock = asyncio.Lock()


def _normalize_embedding_texts(texts: object) -> list[str]:
    """Normalize embedding inputs to a stable list of strings.

    LightRAG can pass values that are not strictly ``list[str]`` in some
    query/index paths. Normalizing to strings avoids provider-specific parsing
    differences that can produce vector count mismatches.
    """
    if isinstance(texts, str):
        return [texts]
    if isinstance(texts, np.ndarray):
        texts = texts.tolist()
    if isinstance(texts, tuple):
        texts = list(texts)
    if not isinstance(texts, list):
        return ["" if texts is None else str(texts)]

    normalized: list[str] = []
    for item in texts:
        if item is None:
            normalized.append("")
        elif isinstance(item, str):
            normalized.append(item)
        elif isinstance(item, (dict, list, tuple, np.ndarray)):
            normalized.append(json.dumps(item, ensure_ascii=False, default=str))
        else:
            normalized.append(str(item))
    return normalized


# ── OpenAI builders ─────────────────────────────────────────────────────────


async def _openai_embed(
    texts: object,
    model: str,
    api_key: str,
) -> np.ndarray:
    """Embed texts with OpenAI and enforce 1:1 input-to-vector cardinality."""
    normalized_texts = _normalize_embedding_texts(texts)
    if not normalized_texts:
        return np.array([], dtype=np.float32)

    client = AsyncOpenAI(api_key=api_key)
    response = await client.embeddings.create(model=model, input=normalized_texts)
    vectors = [item.embedding for item in response.data]

    if len(vectors) != len(normalized_texts):
        logger.warning(
            "OpenAI embedding batch cardinality mismatch (inputs=%d, vectors=%d); retrying one-by-one",
            len(normalized_texts),
            len(vectors),
        )
        vectors = []
        for text in normalized_texts:
            single = await client.embeddings.create(model=model, input=[text])
            if not single.data:
                raise RuntimeError("OpenAI embedding returned no vectors for single-input retry")
            vectors.append(single.data[0].embedding)

    return np.array(vectors, dtype=np.float32)


def _build_llm_func():
    """Build the OpenAI LLM completion function for LightRAG."""
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
    """Build the OpenAI embedding function for LightRAG vector storage."""
    settings = get_settings()
    return EmbeddingFunc(
        embedding_dim=settings.embedding_dimension,
        max_token_size=8192,
        func=lambda texts: _openai_embed(
            texts,
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        ),
    )


# ── Singleton management ────────────────────────────────────────────────────


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


async def reset_lightrag() -> None:
    """Shut down and discard the current instance so the next call reinitializes."""
    await shutdown_lightrag()


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

    try:
        result = await rag.aquery(question, param=param)
    except Exception as exc:
        logger.error("LightRAG query failed: %s", exc)
        raise RuntimeError(f"Query failed: {exc}") from exc

    if result is None:
        raise RuntimeError("Query returned no results — the knowledge graph may be empty.")
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
        SSE-formatted strings with type: text_delta, error, done
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

    try:
        response = await rag.aquery(question, param=param)
    except Exception as exc:
        logger.error("LightRAG streaming query failed: %s", exc)
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        return

    if response is None:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Query returned no results — the knowledge graph may be empty.'})}\n\n"
        return

    try:
        async for chunk in response:
            if chunk:
                yield f"data: {json.dumps({'type': 'text_delta', 'delta': chunk})}\n\n"
    except Exception as exc:
        logger.error("Error during stream iteration: %s", exc)
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        return

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


async def get_knowledge_graph_data(limit: int = 200) -> dict:
    """Export the knowledge graph as nodes and edges for visualization.

    Returns the top ``limit`` nodes by degree centrality and all edges
    between them, formatted for a force-directed graph renderer.
    """
    rag = await get_lightrag()

    try:
        graph = rag.chunk_entity_relation_graph
        if not hasattr(graph, "_graph"):
            return {"nodes": [], "edges": []}

        g = graph._graph

        all_node_ids = list(g.nodes())
        if not all_node_ids:
            return {"nodes": [], "edges": []}

        # Select top nodes by degree when the graph exceeds the limit
        if len(all_node_ids) <= limit:
            selected = set(all_node_ids)
        else:
            degrees = sorted(g.degree(), key=lambda x: x[1], reverse=True)
            selected = set(n for n, _ in degrees[:limit])

        degree_map = dict(g.degree())

        nodes = []
        for nid in selected:
            attrs = g.nodes[nid]
            nodes.append({
                "id": str(nid),
                "label": str(nid),
                "type": attrs.get("entity_type", "unknown"),
                "description": attrs.get("description", ""),
                "degree": degree_map.get(nid, 0),
            })

        edges = []
        edge_id = 0
        for u, v, data in g.edges(data=True):
            if u in selected and v in selected:
                edges.append({
                    "id": str(edge_id),
                    "source": str(u),
                    "target": str(v),
                    "label": data.get("keywords", data.get("description", "")),
                    "weight": data.get("weight", 1.0),
                })
                edge_id += 1

        return {"nodes": nodes, "edges": edges}
    except Exception as exc:
        logger.warning("Could not export KG data: %s", exc)
        return {"nodes": [], "edges": []}


async def delete_document(doc_id: str) -> dict:
    """Delete a document and its entities from the knowledge graph."""
    rag = await get_lightrag()
    try:
        await rag.adelete_by_doc_id(doc_id)
        return {"status": "deleted", "doc_id": doc_id}
    except Exception as exc:
        logger.error("Failed to delete document %s: %s", doc_id, exc)
        return {"status": "error", "doc_id": doc_id, "error": str(exc)}
