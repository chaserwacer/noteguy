"""OpenAI-only model router helpers.

AI endpoints are pinned to OpenAI. These helpers keep a stable API shape for
metadata and compatibility with existing UI code paths.

Task classification
-------------------
LIGHT  — suitable for a local Ollama model (llama3.2 / mistral / etc.)
         * dspy_summarise    — structured summary of a single note
         * dspy_topics       — topic / theme extraction
         * instructor_tags   — note categorisation + confidence-scored tags
         * instructor_entities — named entity extraction
         * pydantic_enhance  — grammar & structure improvement

HEAVY  — must stay on a cloud provider
         * dspy_ask          — chain-of-thought RAG; needs strong reasoning
         * langchain_ask/stream — multi-doc context synthesis
         * llama_index_query — complex query engine over vault
         * crewai_*          — multi-agent orchestration; small models fail
         * instructor_summary — nested ActionItem schema; too complex locally
         * mem0_chat         — personalised memory responses
         * pydantic_ask      — confidence + source attribution
         * pydantic_connections — cross-vault semantic linking

Provider behavior:
    any requested provider -> "openai"

Public API
----------
    resolve_provider(requested, task)  -> str
    is_ollama_available()              -> bool
    model_name_for(provider)           -> str
"""

from __future__ import annotations

from app.config import get_settings

# ── Task classification ────────────────────────────────────────────────────

LIGHT_TASKS: frozenset[str] = frozenset({
    "dspy_summarise",
    "dspy_topics",
    "instructor_tags",
    "instructor_entities",
    "pydantic_enhance",
})

HEAVY_TASKS: frozenset[str] = frozenset({
    "dspy_ask",
    "langchain_ask",
    "langchain_stream",
    "llama_index_query",
    "crewai_research",
    "crewai_summarise",
    "crewai_write",
    "instructor_summary",
    "mem0_chat",
    "pydantic_ask",
    "pydantic_connections",
})


# ── Ollama availability check ─────────────────────────────────────────────

def is_ollama_available() -> bool:
    """Return False because AI endpoint routing is OpenAI-only."""
    return False


# ── Provider resolution ────────────────────────────────────────────────────

def resolve_provider(requested: str, task: str) -> str:
    """Resolve the effective provider string for a given task.

    Parameters
    ----------
    requested : str
        Value supplied by the caller. Ignored in OpenAI-only mode.
    task : str
        Logical task name (one of the keys in LIGHT_TASKS / HEAVY_TASKS).

    Returns
    -------
    str
        ``"openai"``.
    """
    return "openai"


# ── Model name helper ──────────────────────────────────────────────────────

def model_name_for(provider: str) -> str:
    """Return a human-readable model identifier for the given provider."""
    _ = get_settings()
    return "gpt-4o"


# ── Routing metadata (for API responses) ─────────────────────────────────

def routing_info(requested: str, resolved: str, task: str) -> dict:
    """Build a small dict that endpoints attach to their response."""
    resolved_provider = "openai"
    return {
        "provider_requested": "openai",
        "provider_used": resolved_provider,
        "model_used": model_name_for(resolved_provider),
        "local_inference": False,
        "task": task,
    }
