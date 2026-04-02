"""Mem0 memory layer for persistent conversational context.

Integrates Mem0's intelligent memory system to give the AI assistant
persistent recall across chat sessions.  Features:

- **Conversation memory** — Remembers past interactions and preferences
- **Fact extraction** — Automatically extracts and stores key facts from chats
- **Contextual recall** — Retrieves relevant memories for each new query
- **User-scoped storage** — Memories are isolated per user/session

Public API:

    add_memory(content, user_id, metadata) -> dict
    search_memories(query, user_id) -> list[dict]
    get_all_memories(user_id) -> list[dict]
    chat_with_memory(message, user_id, provider) -> dict
    clear_memories(user_id) -> dict
"""

from __future__ import annotations

from typing import Optional

from mem0 import Memory

from app.config import get_settings


# ── Mem0 configuration ─────────────────────────────────────────────────────


def _get_memory_config() -> dict:
    """Build Mem0 configuration using app settings."""
    settings = get_settings()
    return {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o",
                "api_key": settings.openai_api_key,
                "max_tokens": 1024,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small",
                "api_key": settings.openai_api_key,
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "noteguy_memories",
                "path": settings.chroma_persist_dir,
            },
        },
        "version": "v1.1",
    }


_memory_instance: Memory | None = None


def _get_memory() -> Memory:
    """Return a singleton Mem0 Memory instance."""
    global _memory_instance
    if _memory_instance is None:
        config = _get_memory_config()
        _memory_instance = Memory.from_config(config)
    return _memory_instance


# ── Public API ──────────────────────────────────────────────────────────────


def add_memory(
    content: str,
    user_id: str = "default",
    metadata: dict | None = None,
) -> dict:
    """Store a new memory for the given user.

    Parameters
    ----------
    content : str
        The information to remember (e.g., a user preference or fact).
    user_id : str
        The user identifier for scoping memories.
    metadata : dict | None
        Optional metadata to attach to the memory.

    Returns
    -------
    dict
        ``{"status": "stored", "framework": "mem0"}``
    """
    memory = _get_memory()
    result = memory.add(content, user_id=user_id, metadata=metadata or {})
    return {
        "status": "stored",
        "result": result,
        "framework": "mem0",
    }


def search_memories(
    query: str,
    user_id: str = "default",
    limit: int = 5,
) -> list[dict]:
    """Search for relevant memories matching a query.

    Returns a list of memory dicts with ``memory``, ``score``, and metadata.
    """
    memory = _get_memory()
    results = memory.search(query, user_id=user_id, limit=limit)

    memories = []
    for item in results.get("results", results) if isinstance(results, dict) else results:
        memories.append({
            "memory": item.get("memory", str(item)),
            "score": item.get("score", 0.0),
            "metadata": item.get("metadata", {}),
        })
    return memories


def get_all_memories(user_id: str = "default") -> list[dict]:
    """Retrieve all stored memories for a user.

    Returns a list of memory dicts.
    """
    memory = _get_memory()
    results = memory.get_all(user_id=user_id)

    memories = []
    for item in results.get("results", results) if isinstance(results, dict) else results:
        memories.append({
            "memory": item.get("memory", str(item)),
            "metadata": item.get("metadata", {}),
            "created_at": item.get("created_at", ""),
        })
    return memories


def chat_with_memory(
    message: str,
    user_id: str = "default",
    conversation_history: list[dict] | None = None,
    provider: str = "openai",
) -> dict:
    """Chat with memory-augmented context.

    Searches for relevant memories, includes them in the prompt context,
    and stores the new interaction as a memory.

    Returns ``{"answer": str, "memories_used": list, "framework": "mem0"}``.
    """
    import openai as openai_mod

    settings = get_settings()
    memory = _get_memory()

    # Retrieve relevant memories
    relevant = search_memories(message, user_id=user_id, limit=5)
    memory_context = "\n".join(
        f"- {m['memory']}" for m in relevant if m.get("memory")
    )

    system_prompt = (
        "You are NoteGuy Assistant with persistent memory. "
        "You remember past conversations and user preferences.\n\n"
    )
    if memory_context:
        system_prompt += (
            f"Relevant memories from past interactions:\n{memory_context}\n\n"
        )
    system_prompt += "Use these memories to provide personalised responses."

    client = openai_mod.OpenAI(api_key=settings.openai_api_key)
    messages = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1024,
    )
    answer = response.choices[0].message.content

    # Store this interaction as a memory
    memory.add(
        f"User asked: {message}\nAssistant answered: {answer[:200]}",
        user_id=user_id,
    )

    return {
        "answer": answer,
        "memories_used": relevant,
        "framework": "mem0",
    }


def clear_memories(user_id: str = "default") -> dict:
    """Clear all memories for a user.

    Returns ``{"status": "cleared", "framework": "mem0"}``.
    """
    memory = _get_memory()
    memory.delete_all(user_id=user_id)
    return {"status": "cleared", "framework": "mem0"}
