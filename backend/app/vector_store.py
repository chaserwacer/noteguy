"""ChromaDB vector store initialisation with pluggable embedding functions."""

from functools import lru_cache

import chromadb

from app.config import get_settings
from app.embeddings import get_embedding_provider

COLLECTION_NAME = "noteguy_notes"


def _build_embedding_function():
    """Return the ChromaDB embedding function.

    Delegates to the configured embedding provider abstraction.
    """
    provider = get_embedding_provider()
    return lambda texts: provider.embed(texts)


@lru_cache
def get_collection():
    """Return the singleton ChromaDB collection, creating it if needed."""
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_build_embedding_function(),
    )
