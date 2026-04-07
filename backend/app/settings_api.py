"""Settings API — runtime AI provider configuration.

Exposes GET / PUT ``/api/settings`` so the frontend can read and update
which LLM and embedding providers are active.  Changes are persisted to
``user_settings.json`` and take effect immediately (cached singletons are
invalidated).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings, save_user_overrides
from app.embeddings import get_embedding_provider, get_embedding_model_name

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


# ── Schemas ─────────────────────────────────────────────────────────────────


class AISettingsResponse(BaseModel):
    """Current AI provider configuration (read)."""

    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    vision_model: str
    openai_api_key_set: bool
    ollama_base_url: str
    ollama_model: str


class AISettingsUpdate(BaseModel):
    """Partial update to AI provider settings."""

    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_provider: Optional[str] = None
    embedding_openai_model: Optional[str] = None
    embedding_ollama_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    vision_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None


# ── Allowed values ──────────────────────────────────────────────────────────

_VALID_PROVIDERS = {"openai", "ollama"}


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("", response_model=AISettingsResponse)
def get_ai_settings():
    """Return the current AI provider configuration."""
    settings = get_settings()
    return AISettingsResponse(
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        embedding_provider=settings.embedding_provider,
        embedding_model=get_embedding_model_name(),
        embedding_dimension=settings.embedding_dimension,
        vision_model=settings.vision_model,
        openai_api_key_set=bool(settings.openai_api_key),
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
    )


@router.put("", response_model=AISettingsResponse)
async def update_ai_settings(body: AISettingsUpdate):
    """Update AI provider settings and reinitialize services.

    Only supplied fields are changed; omitted fields keep their current value.
    """
    overrides: dict = {}
    update = body.model_dump(exclude_unset=True)

    # Validate provider names
    for key in ("llm_provider", "embedding_provider"):
        if key in update:
            val = update[key].strip().lower()
            if val not in _VALID_PROVIDERS:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid {key}: {val!r}. Must be one of {sorted(_VALID_PROVIDERS)}.",
                )
            overrides[key] = val

    # Pass through scalar settings
    for key in (
        "llm_model",
        "embedding_openai_model",
        "embedding_ollama_model",
        "embedding_dimension",
        "vision_model",
        "openai_api_key",
        "ollama_base_url",
        "ollama_model",
    ):
        if key in update and update[key] is not None:
            overrides[key] = update[key]

    if not overrides:
        raise HTTPException(status_code=422, detail="No settings to update.")

    # Persist and invalidate config cache
    save_user_overrides(overrides)

    # Invalidate embedding provider cache
    get_embedding_provider.cache_clear()

    # Reset the LightRAG singleton so it picks up new provider/model
    try:
        from app.ai.lightrag_service import reset_lightrag
        await reset_lightrag()
    except Exception as exc:
        logger.warning("Failed to reset LightRAG after settings change: %s", exc)

    # Reset RAG-Anything singleton
    try:
        from app.ai.raganything_service import reset_raganything
        await reset_raganything()
    except Exception as exc:
        logger.warning("Failed to reset RAGAnything after settings change: %s", exc)

    # Return the refreshed settings
    return get_ai_settings()
