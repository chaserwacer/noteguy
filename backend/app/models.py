"""SQLModel data models for notes and folders."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlmodel import SQLModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid4().hex


class Folder(SQLModel, table=True):
    """A folder that organises notes into a hierarchy."""

    id: str = Field(default_factory=_new_id, primary_key=True)
    name: str
    parent_id: Optional[str] = Field(default=None, foreign_key="folder.id")
    path: str = Field(default="")
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class Note(SQLModel, table=True):
    """A single markdown note belonging to an optional folder."""

    id: str = Field(default_factory=_new_id, primary_key=True)
    title: str = "Untitled"
    content: str = ""
    folder_id: Optional[str] = Field(default=None, foreign_key="folder.id")
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
