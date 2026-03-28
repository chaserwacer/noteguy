"""Chat API routes — exposes the RAG pipeline over HTTP."""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.rag import ask, ask_stream

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""

    message: str
    folder_id: Optional[str] = None
    provider: str = "anthropic"


class ChatStreamRequest(BaseModel):
    """Incoming streaming chat message."""

    message: str
    conversation_history: list[dict] = []
    folder_scope: Optional[str] = None
    active_note_id: Optional[str] = None
    provider: str = "anthropic"


class ChatResponse(BaseModel):
    """Response containing the AI-generated answer and source note IDs."""

    answer: str
    sources: list[str]


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest, session: Session = Depends(get_session)):
    """Answer a user question using RAG over their notes."""
    result = ask(
        question=body.message,
        folder_id=body.folder_id,
        provider=body.provider,
    )
    return ChatResponse(**result)


@router.post("/stream")
def chat_stream(body: ChatStreamRequest):
    """Stream an AI answer using Server-Sent Events."""
    return StreamingResponse(
        ask_stream(
            question=body.message,
            conversation_history=body.conversation_history,
            folder_scope=body.folder_scope,
            active_note_id=body.active_note_id,
            provider=body.provider,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
