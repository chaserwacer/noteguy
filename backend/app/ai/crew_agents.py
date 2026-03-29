"""CrewAI multi-agent system for advanced note operations.

Defines a crew of specialised AI agents that collaborate on complex tasks:

- **Researcher** — Searches and retrieves relevant information from notes
- **Summariser** — Condenses content into concise, structured summaries
- **Writer** — Generates new note content based on research findings

The crew can handle tasks like:
- Deep research across the note vault
- Multi-note summarisation
- Content generation informed by existing notes

Public API:

    run_research_crew(question, notes_context) -> dict
    run_summary_crew(content) -> dict
    run_writing_crew(topic, notes_context) -> dict
"""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.llm import LLM

from app.config import get_settings


# ── LLM configuration ──────────────────────────────────────────────────────


def _get_crew_llm(provider: str = "anthropic") -> LLM:
    """Return a CrewAI-compatible LLM instance."""
    settings = get_settings()
    if provider == "anthropic":
        return LLM(
            model="anthropic/claude-sonnet-4-20250514",
            api_key=settings.anthropic_api_key,
            max_tokens=1024,
        )
    return LLM(
        model="openai/gpt-4o",
        api_key=settings.openai_api_key,
        max_tokens=1024,
    )


# ── Agent definitions ──────────────────────────────────────────────────────


def _make_researcher(llm: LLM) -> Agent:
    return Agent(
        role="Note Researcher",
        goal="Find and analyse relevant information from the user's notes",
        backstory=(
            "You are an expert researcher who excels at finding connections "
            "and patterns across a collection of notes and documents. You "
            "identify the most relevant pieces of information and present "
            "them with clear citations."
        ),
        llm=llm,
        verbose=False,
    )


def _make_summariser(llm: LLM) -> Agent:
    return Agent(
        role="Content Summariser",
        goal="Create concise, well-structured summaries of note content",
        backstory=(
            "You are a skilled editor who distils complex information into "
            "clear, actionable summaries. You preserve key insights while "
            "eliminating redundancy, and you organise content with headings "
            "and bullet points for easy scanning."
        ),
        llm=llm,
        verbose=False,
    )


def _make_writer(llm: LLM) -> Agent:
    return Agent(
        role="Note Writer",
        goal="Generate well-written note content on a given topic",
        backstory=(
            "You are a talented technical writer who creates clear, "
            "informative content. You structure notes with proper markdown "
            "formatting, include relevant examples, and build on existing "
            "knowledge from the user's vault."
        ),
        llm=llm,
        verbose=False,
    )


# ── Crew runners ───────────────────────────────────────────────────────────


def run_research_crew(
    question: str,
    notes_context: str,
    provider: str = "anthropic",
) -> dict:
    """Run a research crew that analyses notes to answer a question.

    Returns ``{"result": str, "framework": "crewai"}``.
    """
    llm = _get_crew_llm(provider)
    researcher = _make_researcher(llm)
    summariser = _make_summariser(llm)

    research_task = Task(
        description=(
            f"Analyse the following notes to answer this question: {question}\n\n"
            f"Notes context:\n{notes_context}\n\n"
            "Identify the most relevant information, note any connections "
            "between different notes, and highlight key findings."
        ),
        expected_output=(
            "A detailed analysis with cited sources from the notes, "
            "organised by relevance."
        ),
        agent=researcher,
    )

    synthesis_task = Task(
        description=(
            "Take the research findings and create a clear, well-organised "
            "answer to the user's question.  Use bullet points and headings "
            "where appropriate.  Cite which notes the information came from."
        ),
        expected_output=(
            "A concise, well-structured answer in markdown format with "
            "source attributions."
        ),
        agent=summariser,
    )

    crew = Crew(
        agents=[researcher, summariser],
        tasks=[research_task, synthesis_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    return {
        "result": str(result),
        "framework": "crewai",
    }


def run_summary_crew(
    content: str,
    provider: str = "anthropic",
) -> dict:
    """Run a summarisation crew on the given content.

    Returns ``{"result": str, "framework": "crewai"}``.
    """
    llm = _get_crew_llm(provider)
    summariser = _make_summariser(llm)

    task = Task(
        description=(
            f"Summarise the following content into a concise overview:\n\n"
            f"{content}\n\n"
            "Create a structured summary with:\n"
            "1. A one-sentence TL;DR\n"
            "2. Key points as bullet items\n"
            "3. Any action items or takeaways"
        ),
        expected_output=(
            "A markdown-formatted summary with TL;DR, key points, "
            "and action items sections."
        ),
        agent=summariser,
    )

    crew = Crew(
        agents=[summariser],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    return {"result": str(result), "framework": "crewai"}


def run_writing_crew(
    topic: str,
    notes_context: str = "",
    provider: str = "anthropic",
) -> dict:
    """Run a writing crew to generate new note content on a topic.

    Returns ``{"result": str, "framework": "crewai"}``.
    """
    llm = _get_crew_llm(provider)
    researcher = _make_researcher(llm)
    writer = _make_writer(llm)

    context_section = ""
    if notes_context:
        context_section = (
            f"\n\nExisting notes for reference:\n{notes_context}\n\n"
            "Build on this existing knowledge where relevant."
        )

    research_task = Task(
        description=(
            f"Research the topic: {topic}{context_section}\n\n"
            "Identify key concepts, structure, and relevant information "
            "that should be covered in a comprehensive note."
        ),
        expected_output="An outline of key points and structure for the note.",
        agent=researcher,
    )

    writing_task = Task(
        description=(
            f"Write a comprehensive, well-structured markdown note about: {topic}\n\n"
            "Use the research findings to create content that is:\n"
            "- Well-organised with clear headings\n"
            "- Informative with examples where appropriate\n"
            "- Connected to the user's existing knowledge base\n"
            "- Formatted in clean markdown"
        ),
        expected_output="A complete markdown note ready to save to the vault.",
        agent=writer,
    )

    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    return {"result": str(result), "framework": "crewai"}
