"""Active folder context resolver.

Provides a ``FolderContext`` object that tells the frontend and RAG pipeline
which folder is active, its path, and the suggested scope prefix for
query scoping.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import Note, Folder

router = APIRouter(prefix="/api", tags=["context"])


class FolderContext(BaseModel):
    """Context object describing an active folder for the RAG pipeline."""

    folder_id: str
    folder_name: str
    folder_path: str
    note_count: int
    suggested_scope: str


def _count_notes_in_scope(folder_id: str, session: Session) -> int:
    """Count notes in a folder and all its descendants."""
    folder_ids = _collect_folder_ids(folder_id, session)
    count = session.exec(
        select(func.count(Note.id)).where(Note.folder_id.in_(folder_ids))
    ).one()
    return count


def _collect_folder_ids(root_id: str, session: Session) -> list[str]:
    """Gather root_id and all descendant folder IDs (BFS)."""
    ids = [root_id]
    queue = [root_id]
    while queue:
        parent = queue.pop()
        children = session.exec(
            select(Folder).where(Folder.parent_id == parent)
        ).all()
        for child in children:
            ids.append(child.id)
            queue.append(child.id)
    return ids


@router.get("/context/{folder_id}", response_model=FolderContext)
def get_folder_context(
    folder_id: str,
    session: Session = Depends(get_session),
):
    """Return the context object for a folder, used to scope RAG queries."""
    folder = session.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    note_count = _count_notes_in_scope(folder_id, session)

    # The suggested_scope is the folder's materialised path used for
    # retrieval scoping in AI query endpoints.
    suggested_scope = folder.path or folder.name

    return FolderContext(
        folder_id=folder.id,
        folder_name=folder.name,
        folder_path=folder.path or folder.name,
        note_count=note_count,
        suggested_scope=suggested_scope,
    )
