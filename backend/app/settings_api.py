"""Settings API — runtime AI configuration.

Exposes GET / PUT ``/api/settings`` so the frontend can read and update
model names and the API key.  Changes are persisted to
``user_settings.json`` and take effect immediately (cached singletons are
invalidated).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings, save_user_overrides
from app.embeddings import get_embedding_model_name

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


# ── Schemas ─────────────────────────────────────────────────────────────────


class AISettingsResponse(BaseModel):
    """Current AI configuration (read)."""

    llm_model: str
    embedding_model: str
    embedding_dimension: int
    vision_model: str
    openai_api_key_set: bool


class AISettingsUpdate(BaseModel):
    """Partial update to AI settings."""

    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    vision_model: Optional[str] = None
    openai_api_key: Optional[str] = None


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("", response_model=AISettingsResponse)
def get_ai_settings():
    """Return the current AI configuration."""
    settings = get_settings()
    return AISettingsResponse(
        llm_model=settings.llm_model,
        embedding_model=get_embedding_model_name(),
        embedding_dimension=settings.embedding_dimension,
        vision_model=settings.vision_model,
        openai_api_key_set=bool(settings.openai_api_key),
    )


@router.put("", response_model=AISettingsResponse)
async def update_ai_settings(body: AISettingsUpdate):
    """Update AI settings and reinitialize services.

    Only supplied fields are changed; omitted fields keep their current value.
    """
    overrides: dict = {}
    update = body.model_dump(exclude_unset=True)

    for key in (
        "llm_model",
        "embedding_model",
        "embedding_dimension",
        "vision_model",
        "openai_api_key",
    ):
        if key in update and update[key] is not None:
            overrides[key] = update[key]

    if not overrides:
        raise HTTPException(status_code=422, detail="No settings to update.")

    # Persist and invalidate config cache
    save_user_overrides(overrides)

    # Reset the LightRAG singleton so it picks up new model settings
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

    return get_ai_settings()
