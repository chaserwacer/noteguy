"""Dynamic AI model router.

Decides whether a given task should run on a local Ollama model or a cloud
provider (Anthropic / OpenAI).  The key insight is that several tasks in
NoteGuy are self-contained inference jobs — they receive note content directly
and produce structured output without needing retrieval, multi-step reasoning,
or complex tool use.  These *light* tasks run just as well (and far cheaper)
on a capable local model.

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

When provider == "auto":
    light task + Ollama running  → "ollama"
    light task + Ollama absent   → cloud fallback
    heavy task                   → cloud provider (always)

Public API
----------
    resolve_provider(requested, task)  -> str
    is_ollama_available()              -> bool
    model_name_for(provider)           -> str
"""

from __future__ import annotations

import httpx

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
    """Return True if the Ollama daemon is reachable at the configured URL."""
    settings = get_settings()
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


# ── Provider resolution ────────────────────────────────────────────────────

def resolve_provider(requested: str, task: str) -> str:
    """Resolve the effective provider string for a given task.

    Parameters
    ----------
    requested : str
        Value supplied by the caller: ``"auto"``, ``"anthropic"``, or
        ``"openai"``.
    task : str
        Logical task name (one of the keys in LIGHT_TASKS / HEAVY_TASKS).

    Returns
    -------
    str
        ``"ollama"``, ``"anthropic"``, or ``"openai"``.
    """
    if requested != "auto":
        return requested

    # Heavy tasks always go to the cloud.
    if task not in LIGHT_TASKS:
        return _cloud_fallback()

    # Light tasks go local when Ollama is available.
    if is_ollama_available():
        return "ollama"

    return _cloud_fallback()


def _cloud_fallback() -> str:
    """Return the best available cloud provider."""
    settings = get_settings()
    if settings.anthropic_api_key:
        return "anthropic"
    return "openai"


# ── Model name helper ──────────────────────────────────────────────────────

def model_name_for(provider: str) -> str:
    """Return a human-readable model identifier for the given provider."""
    settings = get_settings()
    if provider == "ollama":
        return settings.ollama_model
    if provider == "anthropic":
        return "claude-sonnet-4-20250514"
    return "gpt-4o"


# ── Routing metadata (for API responses) ─────────────────────────────────

def routing_info(requested: str, resolved: str, task: str) -> dict:
    """Build a small dict that endpoints attach to their response."""
    return {
        "provider_requested": requested,
        "provider_used": resolved,
        "model_used": model_name_for(resolved),
        "local_inference": resolved == "ollama",
        "task": task,
    }
