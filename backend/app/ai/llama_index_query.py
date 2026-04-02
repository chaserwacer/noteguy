"""LlamaIndex integration for document indexing and querying.

Provides an alternative retrieval and query engine using LlamaIndex's
``VectorStoreIndex``, combining:

- ``SimpleDirectoryReader`` for loading notes from the vault
- ``SentenceSplitter`` with markdown-aware chunking
- ``VectorStoreIndex`` backed by the existing ChromaDB store
- ``QueryEngine`` with customisable response synthesis

Public API:

    llama_index_query(question, folder_scope, provider) -> dict
    llama_index_ingest_note(note_id, content, metadata) -> int
"""

from __future__ import annotations

from typing import Optional

from llama_index.core import (
    Document,
    Settings,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.prompts import PromptTemplate
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as OpenAILLM
from llama_index.vector_stores.chroma import ChromaVectorStore

import chromadb

from app.config import get_settings

# ── Settings bootstrap ──────────────────────────────────────────────────────


def _configure_llama_settings(provider: str = "openai") -> None:
    """Set global LlamaIndex settings for the embedding model and LLM."""
    settings = get_settings()

    Settings.embed_model = OpenAIEmbedding(
        model="text-embedding-3-small",
        api_key=settings.openai_api_key,
    )

    Settings.node_parser = SentenceSplitter(
        chunk_size=400,
        chunk_overlap=80,
        separator="\n\n",
    )

    Settings.llm = OpenAILLM(
        model="gpt-4o",
        api_key=settings.openai_api_key,
        max_tokens=1024,
    )


# ── Vector store ────────────────────────────────────────────────────────────


def _get_vector_store() -> ChromaVectorStore:
    """Return a LlamaIndex ChromaVectorStore backed by the existing DB."""
    settings = get_settings()
    chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    collection = chroma_client.get_or_create_collection("noteguy_llama")
    return ChromaVectorStore(chroma_collection=collection)


def _get_index() -> VectorStoreIndex:
    """Build or load the VectorStoreIndex."""
    vector_store = _get_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
    )


# ── Custom prompt ───────────────────────────────────────────────────────────

_QA_TEMPLATE = PromptTemplate(
    "You are NoteGuy Assistant powered by LlamaIndex.\n"
    "Answer the question using ONLY the context below from the user's notes.\n"
    "If the context is insufficient, say so.\n\n"
    "Context:\n"
    "-----\n"
    "{context_str}\n"
    "-----\n\n"
    "Question: {query_str}\n"
    "Answer: "
)


# ── Query ───────────────────────────────────────────────────────────────────


def llama_index_query(
    question: str,
    folder_scope: Optional[str] = None,
    provider: str = "openai",
) -> dict:
    """Query the note vault using a LlamaIndex query engine.

    Returns ``{"answer": str, "sources": list[str], "framework": "llama_index"}``.
    """
    _configure_llama_settings(provider)
    index = _get_index()

    query_engine = index.as_query_engine(
        response_mode=ResponseMode.COMPACT,
        text_qa_template=_QA_TEMPLATE,
        similarity_top_k=8,
    )

    response = query_engine.query(question)

    source_ids = list({
        node.metadata.get("note_id", "")
        for node in response.source_nodes
        if node.metadata.get("note_id")
    })

    return {
        "answer": str(response),
        "sources": source_ids,
        "framework": "llama_index",
    }


# ── Ingestion ───────────────────────────────────────────────────────────────


def llama_index_ingest_note(
    note_id: str,
    content: str,
    metadata: dict | None = None,
) -> int:
    """Ingest a single note into the LlamaIndex vector store.

    Returns the number of nodes (chunks) created.
    """
    if not content or not content.strip():
        return 0

    _configure_llama_settings()

    doc_metadata = {"note_id": note_id}
    if metadata:
        doc_metadata.update(metadata)

    doc = Document(text=content, metadata=doc_metadata)

    index = _get_index()
    index.insert(doc)

    # Count nodes that were created
    splitter = SentenceSplitter(chunk_size=400, chunk_overlap=80)
    nodes = splitter.get_nodes_from_documents([doc])
    return len(nodes)
