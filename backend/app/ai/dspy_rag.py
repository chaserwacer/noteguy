"""DSPy programmatic RAG module.

Uses DSPy's declarative approach to define optimisable RAG signatures
instead of hand-crafting prompts.  Key concepts used:

- ``dspy.Signature`` — Declarative input/output specification
- ``dspy.Module`` — Composable, learnable program
- ``dspy.ChainOfThought`` — Built-in reasoning module
- ``dspy.Retrieve`` — Declarative retrieval step

The module can be optimised with DSPy's teleprompters (e.g. BootstrapFewShot)
to automatically improve prompt quality from examples.

Public API:

    dspy_ask(question, context_chunks) -> dict
    dspy_summarise(content) -> dict
    dspy_extract_topics(content) -> dict
"""

from __future__ import annotations

import dspy

from app.config import get_settings


# ── DSPy LM configuration ──────────────────────────────────────────────────


def _configure_dspy(provider: str = "anthropic") -> None:
    """Configure the global DSPy language model."""
    settings = get_settings()
    if provider == "ollama":
        lm = dspy.LM(
            model=f"ollama_chat/{settings.ollama_model}",
            api_base=settings.ollama_base_url,
            max_tokens=1024,
        )
    elif provider == "anthropic":
        lm = dspy.LM(
            model="anthropic/claude-sonnet-4-20250514",
            api_key=settings.anthropic_api_key,
            max_tokens=1024,
        )
    else:
        lm = dspy.LM(
            model="openai/gpt-4o",
            api_key=settings.openai_api_key,
            max_tokens=1024,
        )
    dspy.configure(lm=lm)


# ── Signatures ──────────────────────────────────────────────────────────────


class NoteQA(dspy.Signature):
    """Answer a question using context from the user's notes."""

    context: str = dspy.InputField(desc="Relevant excerpts from the user's notes")
    question: str = dspy.InputField(desc="The user's question")
    answer: str = dspy.OutputField(desc="A detailed answer citing note sources")


class NoteSummary(dspy.Signature):
    """Summarise note content into a structured overview."""

    content: str = dspy.InputField(desc="The note content to summarise")
    tldr: str = dspy.OutputField(desc="A one-sentence TL;DR")
    key_points: str = dspy.OutputField(desc="Bullet-pointed key takeaways")
    action_items: str = dspy.OutputField(desc="Any action items or next steps")


class TopicExtraction(dspy.Signature):
    """Extract key topics and themes from note content."""

    content: str = dspy.InputField(desc="The note content to analyse")
    topics: str = dspy.OutputField(desc="Comma-separated list of key topics")
    theme: str = dspy.OutputField(desc="The overarching theme of the content")
    connections: str = dspy.OutputField(
        desc="Suggested connections to other potential topics"
    )


# ── Modules ─────────────────────────────────────────────────────────────────


class NoteQAModule(dspy.Module):
    """Chain-of-thought RAG module for answering questions from notes."""

    def __init__(self):
        self.generate_answer = dspy.ChainOfThought(NoteQA)

    def forward(self, context: str, question: str):
        return self.generate_answer(context=context, question=question)


class NoteSummaryModule(dspy.Module):
    """Module for generating structured note summaries."""

    def __init__(self):
        self.summarise = dspy.ChainOfThought(NoteSummary)

    def forward(self, content: str):
        return self.summarise(content=content)


class TopicExtractionModule(dspy.Module):
    """Module for extracting topics and themes from notes."""

    def __init__(self):
        self.extract = dspy.ChainOfThought(TopicExtraction)

    def forward(self, content: str):
        return self.extract(content=content)


# ── Public API ──────────────────────────────────────────────────────────────


def dspy_ask(
    question: str,
    context_chunks: list[dict],
    provider: str = "anthropic",
) -> dict:
    """Answer a question using DSPy's ChainOfThought RAG module.

    Parameters
    ----------
    question : str
        The user's question.
    context_chunks : list[dict]
        Retrieved context chunks (each with ``content`` and ``note_title``).
    provider : str
        LLM provider (``"anthropic"`` or ``"openai"``).

    Returns
    -------
    dict
        ``{"answer": str, "reasoning": str, "framework": "dspy"}``
    """
    _configure_dspy(provider)

    context_block = "\n\n---\n\n".join(
        f"[{c.get('note_title', 'Untitled')}]\n{c.get('content', '')}"
        for c in context_chunks
    )

    module = NoteQAModule()
    result = module(context=context_block, question=question)

    return {
        "answer": result.answer,
        "reasoning": getattr(result, "reasoning", ""),
        "framework": "dspy",
    }


def dspy_summarise(
    content: str,
    provider: str = "anthropic",
) -> dict:
    """Summarise content using DSPy's structured output module.

    Returns
    -------
    dict
        ``{"tldr": str, "key_points": str, "action_items": str,
          "framework": "dspy"}``
    """
    _configure_dspy(provider)
    module = NoteSummaryModule()
    result = module(content=content)

    return {
        "tldr": result.tldr,
        "key_points": result.key_points,
        "action_items": result.action_items,
        "framework": "dspy",
    }


def dspy_extract_topics(
    content: str,
    provider: str = "anthropic",
) -> dict:
    """Extract topics and themes using DSPy.

    Returns
    -------
    dict
        ``{"topics": str, "theme": str, "connections": str,
          "framework": "dspy"}``
    """
    _configure_dspy(provider)
    module = TopicExtractionModule()
    result = module(content=content)

    return {
        "topics": result.topics,
        "theme": result.theme,
        "connections": result.connections,
        "framework": "dspy",
    }
