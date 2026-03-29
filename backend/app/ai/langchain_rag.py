"""LangChain-powered RAG pipeline.

Replaces the manual retrieve-then-prompt pattern with LangChain's composable
chain abstractions.  Uses:

- ``CharacterTextSplitter`` for chunking (with heading-aware separators)
- ``Chroma`` as a LangChain-compatible vector store wrapper
- ``RetrievalQA`` chain for end-to-end RAG
- ``ChatPromptTemplate`` for structured prompt engineering
- ``ChatAnthropic`` / ``ChatOpenAI`` as swappable LLM backends

This module exposes two public helpers consumed by the AI router:

    langchain_ask(question, folder_scope, provider) -> dict
    langchain_ask_stream(question, ..., provider) -> Generator[str]
"""

from __future__ import annotations

import json
from typing import Optional, Generator

from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import Chroma
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import get_settings


# ── Text splitter (mirrors the existing heading-aware strategy) ─────────────

def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """Return a heading-aware markdown text splitter."""
    return RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
        separators=[
            "\n## ",    # h2
            "\n### ",   # h3
            "\n#### ",  # h4
            "\n\n",     # paragraph
            "\n",       # line
            " ",        # word
        ],
        length_function=len,
    )


# ── Vector store wrapper ───────────────────────────────────────────────────

def get_langchain_vectorstore() -> Chroma:
    """Return a LangChain Chroma wrapper pointing at the existing collection."""
    settings = get_settings()
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key,
    )
    return Chroma(
        collection_name="noteguy_notes",
        persist_directory=settings.chroma_persist_dir,
        embedding_function=embeddings,
    )


# ── LLM factory ────────────────────────────────────────────────────────────

def _get_llm(provider: str = "anthropic", streaming: bool = False, callbacks=None):
    """Return a LangChain chat model for the given provider."""
    settings = get_settings()
    if provider == "anthropic":
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            anthropic_api_key=settings.anthropic_api_key,
            max_tokens=1024,
            streaming=streaming,
            callbacks=callbacks,
        )
    return ChatOpenAI(
        model="gpt-4o",
        openai_api_key=settings.openai_api_key,
        max_tokens=1024,
        streaming=streaming,
        callbacks=callbacks,
    )


# ── Prompt template ────────────────────────────────────────────────────────

_RAG_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are NoteGuy Assistant, a helpful AI that answers questions "
        "based on the user's notes.  Use ONLY the provided context to answer. "
        "If the context does not contain enough information, say so.\n\n"
        "Context from notes:\n{context}",
    ),
    ("human", "{question}"),
])


# ── Retrieval QA chain ─────────────────────────────────────────────────────

def langchain_ask(
    question: str,
    folder_scope: Optional[str] = None,
    provider: str = "anthropic",
) -> dict:
    """Answer a question using a LangChain RetrievalQA chain.

    Returns ``{"answer": str, "sources": list[str], "framework": "langchain"}``.
    """
    vectorstore = get_langchain_vectorstore()
    search_kwargs: dict = {"k": 8}
    if folder_scope:
        search_kwargs["filter"] = {"folder_path": {"$startsWith": folder_scope}}

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
    llm = _get_llm(provider)

    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": _RAG_PROMPT},
    )

    result = chain.invoke({"query": question})

    source_ids = list({
        doc.metadata.get("note_id", "")
        for doc in result.get("source_documents", [])
    })

    return {
        "answer": result["result"],
        "sources": source_ids,
        "framework": "langchain",
    }


# ── Streaming callback handler ─────────────────────────────────────────────

class _SSECallbackHandler(BaseCallbackHandler):
    """Collects streamed tokens into a list for SSE emission."""

    def __init__(self):
        self.tokens: list[str] = []

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.tokens.append(token)


def langchain_ask_stream(
    question: str,
    conversation_history: list[dict] | None = None,
    folder_scope: Optional[str] = None,
    provider: str = "anthropic",
) -> Generator[str, None, None]:
    """Stream an answer via LangChain RetrievalQA, yielding SSE events."""
    vectorstore = get_langchain_vectorstore()
    search_kwargs: dict = {"k": 8}
    if folder_scope:
        search_kwargs["filter"] = {"folder_path": {"$startsWith": folder_scope}}

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)

    # Retrieve source docs first for attribution
    docs = retriever.invoke(question)

    context_block = "\n\n---\n\n".join(
        f"[{d.metadata.get('note_title', 'Untitled')}]\n{d.page_content}"
        for d in docs
    )

    messages = _RAG_PROMPT.format_messages(
        context=context_block,
        question=question,
    )

    llm = _get_llm(provider, streaming=True)
    for chunk in llm.stream(messages):
        if chunk.content:
            yield f"data: {json.dumps({'type': 'text_delta', 'delta': chunk.content})}\n\n"

    # Emit sources
    seen: set[str] = set()
    source_notes = []
    for d in docs:
        nid = d.metadata.get("note_id", "")
        if nid and nid not in seen:
            seen.add(nid)
            source_notes.append({
                "note_id": nid,
                "note_title": d.metadata.get("note_title", ""),
                "folder_path": d.metadata.get("folder_path", ""),
            })
    yield f"data: {json.dumps({'type': 'source_notes', 'notes': source_notes})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


# ── Document ingestion helper ──────────────────────────────────────────────

def langchain_ingest_documents(docs: list[Document]) -> int:
    """Split and upsert documents into the LangChain Chroma store.

    Useful for batch ingestion via LangChain's document model.
    Returns the number of chunks indexed.
    """
    splitter = get_text_splitter()
    chunks = splitter.split_documents(docs)
    if not chunks:
        return 0

    vectorstore = get_langchain_vectorstore()
    vectorstore.add_documents(chunks)
    return len(chunks)
