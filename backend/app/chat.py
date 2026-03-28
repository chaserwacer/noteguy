"""Chat API routes — exposes the RAG pipeline over HTTP."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.rag import ask

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""

    message: str
    folder_id: Optional[str] = None
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
