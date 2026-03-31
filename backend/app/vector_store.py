"""ChromaDB vector store initialisation with pluggable embedding functions."""

import logging
import shutil
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api.shared_system_client import SharedSystemClient

from app.config import get_settings
from app.embeddings import get_embedding_provider

COLLECTION_NAME = "noteguy_notes"
_LOGGER = logging.getLogger(__name__)


def _is_tenant_error(exc: BaseException) -> bool:
    return "Could not connect to tenant" in str(exc)


def _is_recoverable_chroma_error(exc: BaseException) -> bool:
    text = str(exc)
    return (
        _is_tenant_error(exc)
        or "out of range for slice" in text
        or "PanicException" in text
        or "sqlite" in text.lower()
    )


def _backup_corrupt_persist_dir(persist_path: str) -> None:
    path = Path(persist_path)
    if not path.exists():
        return

    backup_name = f"{path.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = path.with_name(backup_name)
    shutil.move(str(path), str(backup_path))
    _LOGGER.warning(
        "Backed up incompatible Chroma data directory from %s to %s",
        path,
        backup_path,
    )


def _create_persistent_client() -> chromadb.ClientAPI:
    """Create a persistent Chroma client, repairing missing default tenancy if needed."""
    settings = get_settings()
    persist_path = str(Path(settings.chroma_persist_dir).expanduser().resolve())
    tenant = settings.chroma_tenant
    database = settings.chroma_database

    client_settings = ChromaSettings(
        is_persistent=True,
        persist_directory=persist_path,
    )

    def _new_client() -> chromadb.ClientAPI:
        return chromadb.PersistentClient(
            path=persist_path,
            settings=client_settings,
            tenant=tenant,
            database=database,
        )

    try:
        return _new_client()
    except BaseException as exc:
        SharedSystemClient.clear_system_cache()
        if not _is_tenant_error(exc):
            if _is_recoverable_chroma_error(exc):
                _backup_corrupt_persist_dir(persist_path)
                Path(persist_path).mkdir(parents=True, exist_ok=True)
                SharedSystemClient.clear_system_cache()
                return _new_client()
            raise

        admin = chromadb.AdminClient(settings=client_settings)
        try:
            admin.get_tenant(name=tenant)
        except Exception:
            admin.create_tenant(name=tenant)

        try:
            admin.get_database(name=database, tenant=tenant)
        except Exception:
            admin.create_database(name=database, tenant=tenant)

        try:
            return _new_client()
        except BaseException as retry_exc:
            SharedSystemClient.clear_system_cache()
            if _is_recoverable_chroma_error(retry_exc):
                _backup_corrupt_persist_dir(persist_path)
                Path(persist_path).mkdir(parents=True, exist_ok=True)
                SharedSystemClient.clear_system_cache()
                return _new_client()
            raise


def _build_embedding_function():
    """Return a Chroma-compatible embedding adapter."""
    provider = get_embedding_provider()

    class _EmbeddingAdapter:
        def __call__(self, input):
            return provider.embed(input)

        def embed_query(self, query: str):
            return provider.embed([query])[0]

        def name(self) -> str:
            return "noteguy-embedding-adapter"

    return _EmbeddingAdapter()


@lru_cache
def get_collection():
    """Return the singleton ChromaDB collection, creating it if needed."""
    client = _create_persistent_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_build_embedding_function(),
    )
