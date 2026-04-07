"""Embedding utilities.

All actual embedding is handled by the async functions in
``lightrag_service.py``.  This module provides a helper for
resolving the configured model name.
"""

from app.config import get_settings


def get_embedding_model_name() -> str:
    """Return the configured OpenAI embedding model name."""
    return get_settings().embedding_model
