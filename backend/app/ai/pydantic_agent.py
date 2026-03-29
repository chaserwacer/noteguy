"""PydanticAI agent for type-safe note operations.

Uses PydanticAI's agent framework to build structured, type-safe interactions
with LLMs.  Features:

- **Typed dependencies** — Inject note context via Pydantic models
- **Structured results** — Enforce output schemas with validation
- **Tool use** — Register functions as agent tools for note operations
- **System prompts** — Dynamic system prompts based on context

Public API:

    note_qa_agent(question, notes_context, provider) -> dict
    note_enhancement_agent(content, provider) -> dict
    note_connection_agent(content, all_titles, provider) -> dict
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIModel

from app.config import get_settings


# ── Dependencies and result types ──────────────────────────────────────────


@dataclass
class NoteContext:
    """Dependencies injected into PydanticAI agents."""
    notes_context: str
    active_note_title: str = ""
    vault_note_titles: list[str] | None = None


class QAResult(BaseModel):
    """Structured result from the QA agent."""
    answer: str = Field(description="The answer to the user's question")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in the answer (0.0 to 1.0)",
    )
    sources_used: list[str] = Field(
        description="Titles of notes used to form the answer",
    )
    follow_up_questions: list[str] = Field(
        description="Suggested follow-up questions",
        max_length=3,
    )


class EnhancementResult(BaseModel):
    """Structured result from the note enhancement agent."""
    enhanced_content: str = Field(description="The improved note content in markdown")
    changes_made: list[str] = Field(
        description="Summary of changes made to improve the note",
    )
    readability_score: int = Field(
        ge=1, le=10,
        description="Readability score after enhancement (1-10)",
    )


class ConnectionResult(BaseModel):
    """Structured result from the note connection agent."""
    connections: list[NoteConnection] = Field(
        description="Identified connections to other notes",
    )
    suggested_tags: list[str] = Field(
        description="Tags that would help link this note to others",
    )
    knowledge_gaps: list[str] = Field(
        description="Topics mentioned but not covered in existing notes",
    )


class NoteConnection(BaseModel):
    """A connection between the current note and another."""
    related_title: str = Field(description="Title of the related note")
    relationship: str = Field(description="How the notes are related")
    strength: float = Field(
        ge=0.0, le=1.0,
        description="Strength of the connection (0.0 to 1.0)",
    )


# Fix forward reference
ConnectionResult.model_rebuild()


# ── Model factory ──────────────────────────────────────────────────────────


def _get_model(provider: str = "anthropic"):
    """Return a PydanticAI model instance."""
    settings = get_settings()
    if provider == "ollama":
        # Ollama exposes an OpenAI-compatible /v1 endpoint
        return OpenAIModel(
            settings.ollama_model,
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
        )
    if provider == "anthropic":
        return AnthropicModel(
            "claude-sonnet-4-20250514",
            api_key=settings.anthropic_api_key,
        )
    return OpenAIModel(
        "gpt-4o",
        api_key=settings.openai_api_key,
    )


# ── QA Agent ────────────────────────────────────────────────────────────────


_qa_agent = Agent(
    "anthropic:claude-sonnet-4-20250514",
    deps_type=NoteContext,
    result_type=QAResult,
    system_prompt=(
        "You are NoteGuy Assistant powered by PydanticAI. "
        "Answer questions using the provided note context. "
        "Always cite which notes you used and rate your confidence. "
        "Suggest relevant follow-up questions."
    ),
)


@_qa_agent.system_prompt
def _add_note_context(ctx):
    return f"Available note context:\n{ctx.deps.notes_context}"


def note_qa_agent(
    question: str,
    notes_context: str,
    provider: str = "anthropic",
) -> dict:
    """Answer a question using the PydanticAI QA agent.

    Returns the ``QAResult`` as a dict with ``framework: "pydantic_ai"``.
    """
    model = _get_model(provider)
    deps = NoteContext(notes_context=notes_context)

    result = _qa_agent.run_sync(
        question,
        deps=deps,
        model=model,
    )

    return {**result.data.model_dump(), "framework": "pydantic_ai"}


# ── Enhancement Agent ──────────────────────────────────────────────────────


_enhancement_agent = Agent(
    "anthropic:claude-sonnet-4-20250514",
    deps_type=NoteContext,
    result_type=EnhancementResult,
    system_prompt=(
        "You are a note enhancement assistant. Improve the given note by:\n"
        "- Fixing grammar and spelling\n"
        "- Improving structure and formatting\n"
        "- Adding missing markdown headings\n"
        "- Clarifying ambiguous statements\n"
        "- Preserving the author's voice and intent\n"
        "Return the full improved content in markdown."
    ),
)


def note_enhancement_agent(
    content: str,
    provider: str = "anthropic",
) -> dict:
    """Enhance a note's content using the PydanticAI enhancement agent.

    Returns the ``EnhancementResult`` as a dict with ``framework: "pydantic_ai"``.
    """
    model = _get_model(provider)
    deps = NoteContext(notes_context=content)

    result = _enhancement_agent.run_sync(
        f"Enhance this note:\n\n{content}",
        deps=deps,
        model=model,
    )

    return {**result.data.model_dump(), "framework": "pydantic_ai"}


# ── Connection Agent ───────────────────────────────────────────────────────


_connection_agent = Agent(
    "anthropic:claude-sonnet-4-20250514",
    deps_type=NoteContext,
    result_type=ConnectionResult,
    system_prompt=(
        "You are a knowledge graph assistant. Analyse the current note and "
        "identify connections to other notes in the vault. Look for:\n"
        "- Shared topics or concepts\n"
        "- Referenced ideas that exist in other notes\n"
        "- Complementary information\n"
        "- Knowledge gaps that could be filled with new notes\n"
        "Only suggest connections to notes that exist in the vault."
    ),
)


@_connection_agent.system_prompt
def _add_vault_titles(ctx):
    if ctx.deps.vault_note_titles:
        titles = "\n".join(f"- {t}" for t in ctx.deps.vault_note_titles)
        return f"Notes in the vault:\n{titles}"
    return "No vault note list available."


def note_connection_agent(
    content: str,
    all_titles: list[str] | None = None,
    provider: str = "anthropic",
) -> dict:
    """Find connections between a note and the rest of the vault.

    Returns the ``ConnectionResult`` as a dict with ``framework: "pydantic_ai"``.
    """
    model = _get_model(provider)
    deps = NoteContext(
        notes_context=content,
        vault_note_titles=all_titles or [],
    )

    result = _connection_agent.run_sync(
        f"Analyse this note and find connections:\n\n{content}",
        deps=deps,
        model=model,
    )

    return {**result.data.model_dump(), "framework": "pydantic_ai"}
