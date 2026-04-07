"""Chat API routes — LightRAG-powered conversational interface.

The chat endpoints use LightRAG's hybrid query mode for graph-augmented
retrieval, providing richer answers that leverage entity relationships.
"""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    folder_id: Optional[str] = None


class ChatStreamRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []
    folder_scope: Optional[str] = None
    active_note_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """Answer a user question using LightRAG hybrid retrieval."""
    from app.ai.lightrag_service import query
    from app.ingestion_tracker import ensure_all_indexed

    await ensure_all_indexed()
    answer = await query(
        question=body.message,
        mode="hybrid",
    )
    return ChatResponse(answer=answer, sources=[])


@router.post("/stream")
async def chat_stream(body: ChatStreamRequest):
    """Stream an AI answer using LightRAG with SSE."""
    from app.ai.lightrag_service import query_stream
    from app.ingestion_tracker import ensure_all_indexed

    await ensure_all_indexed()
    return StreamingResponse(
        query_stream(
            question=body.message,
            mode="hybrid",
            conversation_history=body.conversation_history,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
