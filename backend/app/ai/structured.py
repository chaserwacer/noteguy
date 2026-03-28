"""Instructor-powered structured data extraction.

Uses the ``instructor`` library to extract typed, validated data from LLM
responses via Pydantic models.  This enables reliable structured outputs for:

- Auto-tagging notes with categories
- Extracting named entities (people, places, concepts)
- Generating structured summaries with confidence scores
- Identifying action items and deadlines

Public API:

    extract_tags(content, provider) -> NoteAnalysis
    extract_entities(content, provider) -> EntityExtraction
    extract_summary(content, provider) -> StructuredSummary
"""

from __future__ import annotations

from enum import Enum

import anthropic
import instructor
import openai
from pydantic import BaseModel, Field

from app.config import get_settings


# ── Pydantic schemas for structured extraction ──────────────────────────────


class NoteCategory(str, Enum):
    """High-level note categories for auto-tagging."""
    MEETING = "meeting"
    RESEARCH = "research"
    TODO = "todo"
    JOURNAL = "journal"
    REFERENCE = "reference"
    PROJECT = "project"
    LEARNING = "learning"
    IDEA = "idea"
    OTHER = "other"


class NoteTag(BaseModel):
    """A single tag with confidence score."""
    name: str = Field(description="The tag name (lowercase, hyphenated)")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score for this tag (0.0 to 1.0)",
    )


class NoteAnalysis(BaseModel):
    """Structured analysis of a note's content."""
    category: NoteCategory = Field(description="The primary category of this note")
    tags: list[NoteTag] = Field(
        description="Relevant tags for this note, ordered by confidence",
        max_length=10,
    )
    complexity: int = Field(
        ge=1, le=5,
        description="Content complexity level (1=simple, 5=very complex)",
    )
    word_count_estimate: int = Field(description="Estimated word count")
    summary_sentence: str = Field(
        description="One-sentence summary of the note",
    )


class Entity(BaseModel):
    """A named entity extracted from text."""
    name: str = Field(description="The entity name")
    entity_type: str = Field(
        description="Entity type: person, organisation, concept, technology, place, date",
    )
    context: str = Field(description="Brief context of how this entity appears")


class EntityExtraction(BaseModel):
    """Collection of entities extracted from a note."""
    entities: list[Entity] = Field(
        description="Named entities found in the text",
        max_length=20,
    )
    key_concepts: list[str] = Field(
        description="Main concepts discussed (as short phrases)",
        max_length=10,
    )


class ActionItem(BaseModel):
    """An action item or task extracted from text."""
    task: str = Field(description="The action item description")
    priority: str = Field(description="Priority: high, medium, or low")
    deadline: str | None = Field(
        default=None,
        description="Deadline if mentioned, in ISO format or natural language",
    )


class StructuredSummary(BaseModel):
    """A comprehensive structured summary of note content."""
    title_suggestion: str = Field(description="Suggested title for this note")
    tldr: str = Field(description="One-sentence TL;DR")
    key_points: list[str] = Field(
        description="Key points as concise bullet items",
        max_length=10,
    )
    action_items: list[ActionItem] = Field(
        description="Action items or tasks mentioned",
        max_length=10,
    )
    related_topics: list[str] = Field(
        description="Topics the user might want to explore further",
        max_length=5,
    )


# ── Instructor client factory ──────────────────────────────────────────────


def _get_instructor_client(provider: str = "anthropic"):
    """Return an instructor-patched LLM client."""
    settings = get_settings()
    if provider == "anthropic":
        raw_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return instructor.from_anthropic(raw_client), "claude-sonnet-4-20250514"
    raw_client = openai.OpenAI(api_key=settings.openai_api_key)
    return instructor.from_openai(raw_client), "gpt-4o"


# ── Extraction functions ───────────────────────────────────────────────────


def extract_tags(
    content: str,
    provider: str = "anthropic",
) -> dict:
    """Analyse a note and extract structured tags and metadata.

    Returns the ``NoteAnalysis`` as a dict with ``framework: "instructor"``.
    """
    client, model = _get_instructor_client(provider)

    if provider == "anthropic":
        result = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": (
                    "Analyse the following note and extract structured metadata.\n\n"
                    f"Note content:\n{content}"
                ),
            }],
            response_model=NoteAnalysis,
        )
    else:
        result = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[
                {
                    "role": "system",
                    "content": "You are a note analysis assistant. Extract structured metadata from the note.",
                },
                {"role": "user", "content": content},
            ],
            response_model=NoteAnalysis,
        )

    return {**result.model_dump(), "framework": "instructor"}


def extract_entities(
    content: str,
    provider: str = "anthropic",
) -> dict:
    """Extract named entities and key concepts from note content.

    Returns the ``EntityExtraction`` as a dict with ``framework: "instructor"``.
    """
    client, model = _get_instructor_client(provider)

    if provider == "anthropic":
        result = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": (
                    "Extract all named entities and key concepts from this note.\n\n"
                    f"Note content:\n{content}"
                ),
            }],
            response_model=EntityExtraction,
        )
    else:
        result = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[
                {
                    "role": "system",
                    "content": "Extract named entities and key concepts from the text.",
                },
                {"role": "user", "content": content},
            ],
            response_model=EntityExtraction,
        )

    return {**result.model_dump(), "framework": "instructor"}


def extract_summary(
    content: str,
    provider: str = "anthropic",
) -> dict:
    """Generate a structured summary with action items.

    Returns the ``StructuredSummary`` as a dict with ``framework: "instructor"``.
    """
    client, model = _get_instructor_client(provider)

    if provider == "anthropic":
        result = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": (
                    "Create a comprehensive structured summary of this note, "
                    "including action items and related topics.\n\n"
                    f"Note content:\n{content}"
                ),
            }],
            response_model=StructuredSummary,
        )
    else:
        result = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[
                {
                    "role": "system",
                    "content": "Create a structured summary with action items and related topics.",
                },
                {"role": "user", "content": content},
            ],
            response_model=StructuredSummary,
        )

    return {**result.model_dump(), "framework": "instructor"}
