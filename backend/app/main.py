"""NoteGuy backend — FastAPI application entry point."""

from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from git.exc import GitError

from app.config import get_settings
from app.database import init_db
from app.git_service import init_git_service, get_git_service
from app.notes import router as notes_router
from app.chat import router as chat_router
from app.history import router as history_router
from app.ingestion import router as ingestion_router
from app.context import router as context_router
from app.ai.router import router as ai_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database, vault directory, and AI services on startup."""
    init_db()
    Path(get_settings().vault_path).mkdir(parents=True, exist_ok=True)
    init_git_service()

    # Pre-warm the LightRAG instance so first query is fast
    try:
        from app.ai.lightrag_service import get_lightrag
        await get_lightrag()
        logger.info("LightRAG knowledge graph ready")
    except Exception as exc:
        logger.warning("LightRAG pre-warm failed (will retry on first use): %s", exc)

    yield

    # Shutdown: finalize LightRAG storages
    try:
        from app.ai.lightrag_service import shutdown_lightrag
        await shutdown_lightrag()
    except Exception as exc:
        logger.warning("LightRAG shutdown error: %s", exc)

    # Flush any staged but uncommitted git changes
    try:
        get_git_service().flush_staged()
    except (GitError, OSError) as exc:
        logger.warning("Failed to flush staged git changes on shutdown: %s", exc)


app = FastAPI(
    title="NoteGuy",
    description="Markdown note-taking backend with LightRAG-powered AI.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notes_router)
app.include_router(chat_router)
app.include_router(history_router)
app.include_router(ingestion_router)
app.include_router(context_router)
app.include_router(ai_router)


@app.get("/health")
def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}
