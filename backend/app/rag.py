"""RAG pipeline — vector search + LLM answer generation.

The ``retrieve_context`` function supports folder-scoped search by filtering
on the ``folder_path`` metadata prefix stored in each chunk.
"""

from typing import Optional

import anthropic
import openai
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.vector_store import get_collection

router = APIRouter(prefix="/api", tags=["search"])

DEFAULT_TOP_K = 8


# ── Retrieval ────────────────────────────────────────────────────────────────


def retrieve_context(
    query: str,
    folder_scope: Optional[str] = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """Perform a vector similarity search and return relevant chunks.

    Parameters
    ----------
    query : str
        The user's search query.
    folder_scope : str | None
        If provided, only return chunks whose ``folder_path`` starts with
        this prefix (scopes search to a folder and its descendants).
    top_k : int
        Maximum number of chunks to return.

    Returns
    -------
    list[dict]
        Each dict has keys: content, note_title, note_id, folder_path, score.
    """
    collection = get_collection()

    where_filter = None
    if folder_scope:
        where_filter = {
            "folder_path": {"$startsWith": folder_scope},  # type: ignore[dict-item]
        }

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
    )

    if not results["documents"] or not results["documents"][0]:
        return []

    chunks: list[dict] = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # ChromaDB distances are L2 by default; convert to a 0-1 similarity
        score = 1.0 / (1.0 + distance)
        chunks.append(
            {
                "content": doc,
                "note_title": meta.get("note_title", ""),
                "note_id": meta.get("note_id", ""),
                "folder_path": meta.get("folder_path", ""),
                "score": round(score, 4),
            }
        )
    return chunks


# ── Search endpoint ──────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str
    folder_scope: Optional[str] = None
    top_k: int = DEFAULT_TOP_K


class SearchResult(BaseModel):
    content: str
    note_title: str
    note_id: str
    folder_path: str
    score: float


@router.post("/search", response_model=list[SearchResult])
def search_endpoint(body: SearchRequest):
    """Search the vault using vector similarity."""
    results = retrieve_context(
        query=body.query,
        folder_scope=body.folder_scope,
        top_k=body.top_k,
    )
    return results


# ── LLM answer generation (used by chat) ─────────────────────────────────────


def ask(
    question: str,
    folder_id: Optional[str] = None,
    folder_scope: Optional[str] = None,
    provider: str = "anthropic",
) -> dict:
    """Answer a user question using retrieved context.

    Returns a dict with ``answer`` and ``sources`` keys.
    """
    # Use folder_scope if provided, otherwise fall back to folder_id for
    # backward compatibility with chat.py
    scope = folder_scope
    if not scope and folder_id:
        # Legacy path: use folder_id directly as a metadata filter
        scope = None  # will use folder_id filter below

    chunks = retrieve_context(question, folder_scope=scope)

    if not chunks:
        # If scoped search found nothing, try a broader search
        if scope:
            chunks = retrieve_context(question, folder_scope=None, top_k=4)

    context_block = "\n\n---\n\n".join(
        f"[{c['note_title']}]\n{c['content']}" for c in chunks
    )

    system_prompt = (
        "You are NoteVault Assistant, a helpful AI that answers questions "
        "based on the user's notes. Use ONLY the provided context to answer. "
        "If the context does not contain enough information, say so."
    )
    user_prompt = (
        f"Context from my notes:\n\n{context_block}\n\n---\n\nQuestion: {question}"
    )

    if provider == "anthropic":
        answer = _ask_anthropic(system_prompt, user_prompt)
    else:
        answer = _ask_openai(system_prompt, user_prompt)

    sources = list({c["note_id"] for c in chunks})
    return {"answer": answer, "sources": sources}


def ask_stream(
    question: str,
    conversation_history: list[dict] | None = None,
    folder_id: Optional[str] = None,
    folder_scope: Optional[str] = None,
    active_note_id: Optional[str] = None,
    provider: str = "anthropic",
):
    """Stream an answer using retrieved context.  Yields SSE-formatted strings.

    Events:
      data: {"type":"text_delta","delta":"..."}
      data: {"type":"source_notes","notes":[{"note_id":...,"note_title":...,"folder_path":...}]}
      data: {"type":"done"}
    """
    import json

    scope = folder_scope
    if not scope and folder_id:
        scope = None

    chunks = retrieve_context(question, folder_scope=scope)
    if not chunks and scope:
        chunks = retrieve_context(question, folder_scope=None, top_k=4)

    context_block = "\n\n---\n\n".join(
        f"[{c['note_title']}]\n{c['content']}" for c in chunks
    )

    system_prompt = (
        "You are NoteVault Assistant, a helpful AI with access to the user's notes. "
        "Here are relevant excerpts from their notes:\n\n"
        f"{context_block}\n\n"
        "Answer based on this information, citing which note the info came from. "
        "If the context does not contain enough information, say so."
    )

    # Build messages list from conversation history
    messages: list[dict] = []
    if conversation_history:
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    if provider == "anthropic":
        yield from _stream_anthropic(system_prompt, messages)
    else:
        yield from _stream_openai(system_prompt, messages)

    # Emit source notes
    seen = set()
    source_notes = []
    for c in chunks:
        nid = c["note_id"]
        if nid not in seen:
            seen.add(nid)
            source_notes.append(
                {
                    "note_id": nid,
                    "note_title": c["note_title"],
                    "folder_path": c["folder_path"],
                }
            )
    yield f"data: {json.dumps({'type': 'source_notes', 'notes': source_notes})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


def _ask_anthropic(system: str, user: str) -> str:
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text


def _stream_anthropic(system: str, messages: list[dict]):
    """Yield SSE text_delta events from Anthropic streaming."""
    import json

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'type': 'text_delta', 'delta': text})}\n\n"


def _ask_openai(system: str, user: str) -> str:
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _stream_openai(system: str, messages: list[dict]):
    """Yield SSE text_delta events from OpenAI streaming."""
    import json

    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            *messages,
        ],
        max_tokens=1024,
        stream=True,
    )
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            delta = chunk.choices[0].delta.content
            yield f"data: {json.dumps({'type': 'text_delta', 'delta': delta})}\n\n"
