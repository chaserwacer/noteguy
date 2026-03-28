"""ChromaDB vector store initialisation with pluggable embedding functions."""

from functools import lru_cache

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from app.config import get_settings

COLLECTION_NAME = "notevault_notes"


def _build_embedding_function():
    """Return the ChromaDB embedding function.

    Uses OpenAI text-embedding-3-small.  The ``embeddings.py`` provider
    abstraction is used by the ingestion pipeline directly; this wrapper
    exists only because ChromaDB's ``query()`` requires its own callable.
    """
    settings = get_settings()
    return OpenAIEmbeddingFunction(
        api_key=settings.openai_api_key,
        model_name="text-embedding-3-small",
    )


@lru_cache
def get_collection():
    """Return the singleton ChromaDB collection, creating it if needed."""
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_build_embedding_function(),
    )
