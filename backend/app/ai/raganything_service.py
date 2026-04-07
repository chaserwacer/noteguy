"""RAG-Anything service — multimodal document processing built on LightRAG.

Handles parsing and ingestion of PDFs, images, Office documents, and other
multimodal content. Extends the LightRAG knowledge graph with entities
extracted from tables, figures, and equations.

The vision / LLM provider is determined by the ``llm_provider`` setting.
No fallback is attempted — provider errors are surfaced to the caller.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.ai.lightrag_service import get_lightrag, _ollama_llm_complete

logger = logging.getLogger(__name__)

_rag_anything_instance = None
_rag_anything_lock = asyncio.Lock()


async def _build_vision_model_func():
    """Build the vision model function for multimodal content analysis."""
    settings = get_settings()
    provider = settings.llm_provider.strip().lower()

    if provider == "ollama":
        async def vision_func(
            prompt: str,
            system_prompt: str | None = None,
            history_messages: list[dict] | None = None,
            image_data: str | None = None,
            messages: list | None = None,
            **kwargs,
        ) -> str:
            # Ollama vision models accept images via the /api/chat endpoint
            # with base64 image data. For text-only, use standard chat.
            return await _ollama_llm_complete(
                model=settings.vision_model if (image_data or messages) else settings.ollama_model,
                base_url=settings.ollama_base_url,
                prompt=prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                **kwargs,
            )
        return vision_func

    if provider == "openai":
        from lightrag.llm.openai import openai_complete_if_cache

        async def vision_func(
            prompt: str,
            system_prompt: str | None = None,
            history_messages: list[dict] | None = None,
            image_data: str | None = None,
            messages: list | None = None,
            **kwargs,
        ) -> str:
            if messages:
                return await openai_complete_if_cache(
                    settings.vision_model,
                    "",
                    system_prompt=system_prompt,
                    history_messages=[],
                    messages=messages,
                    api_key=settings.openai_api_key,
                    **kwargs,
                )
            elif image_data:
                img_messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                },
                            },
                        ],
                    }
                ]
                return await openai_complete_if_cache(
                    settings.vision_model,
                    "",
                    system_prompt=system_prompt,
                    history_messages=[],
                    messages=img_messages,
                    api_key=settings.openai_api_key,
                    **kwargs,
                )
            else:
                return await openai_complete_if_cache(
                    settings.llm_model,
                    prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages or [],
                    api_key=settings.openai_api_key,
                    **kwargs,
                )
        return vision_func

    raise ValueError(f"Unsupported LLM provider: {provider}")


async def get_raganything():
    """Return the singleton RAGAnything instance, initializing on first call."""
    global _rag_anything_instance

    if _rag_anything_instance is not None:
        return _rag_anything_instance

    async with _rag_anything_lock:
        if _rag_anything_instance is not None:
            return _rag_anything_instance

        try:
            from raganything import RAGAnything, RAGAnythingConfig
        except ImportError:
            logger.warning(
                "raganything not installed — multimodal document processing "
                "will be unavailable. Install with: pip install raganything"
            )
            return None

        settings = get_settings()
        output_dir = str(
            Path(settings.raganything_output_dir).expanduser().resolve()
        )
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        config = RAGAnythingConfig(
            working_dir=str(
                Path(settings.lightrag_working_dir).expanduser().resolve()
            ),
            parser=settings.raganything_parser,
            parse_method="auto",
            enable_image_processing=settings.raganything_enable_images,
            enable_table_processing=settings.raganything_enable_tables,
            enable_equation_processing=settings.raganything_enable_equations,
        )

        lightrag = await get_lightrag()
        vision_func = await _build_vision_model_func()

        _rag_anything_instance = RAGAnything(
            config=config,
            lightrag=lightrag,
            vision_model_func=vision_func,
        )

        logger.info("RAGAnything instance initialized with parser=%s", settings.raganything_parser)
        return _rag_anything_instance


async def reset_raganything() -> None:
    """Discard the cached instance so the next call reinitializes."""
    global _rag_anything_instance
    _rag_anything_instance = None


# ── Document processing ───────────────────────────────────────────────────────


async def process_document(
    file_path: str,
    output_dir: str | None = None,
) -> dict:
    """Process a multimodal document (PDF, DOCX, PPTX, images, etc.).

    Parses the document, extracts multimodal content, builds entities,
    and inserts everything into the LightRAG knowledge graph.
    """
    rag = await get_raganything()
    if rag is None:
        return {
            "status": "error",
            "error": "RAGAnything not available — install raganything package",
        }

    settings = get_settings()
    if output_dir is None:
        output_dir = str(
            Path(settings.raganything_output_dir).expanduser().resolve()
        )

    await rag.process_document_complete(
        file_path=file_path,
        output_dir=output_dir,
        parse_method="auto",
    )
    return {
        "status": "indexed",
        "file_path": file_path,
    }


async def process_folder(
    folder_path: str,
    file_extensions: list[str] | None = None,
    recursive: bool = True,
) -> dict:
    """Process all documents in a folder."""
    rag = await get_raganything()
    if rag is None:
        return {
            "status": "error",
            "error": "RAGAnything not available — install raganything package",
        }

    settings = get_settings()
    output_dir = str(
        Path(settings.raganything_output_dir).expanduser().resolve()
    )

    extensions = file_extensions or [
        ".pdf", ".docx", ".pptx", ".xlsx",
        ".jpg", ".jpeg", ".png",
        ".md", ".txt",
    ]

    await rag.process_folder_complete(
        folder_path=folder_path,
        output_dir=output_dir,
        file_extensions=extensions,
        recursive=recursive,
    )
    return {
        "status": "indexed",
        "folder_path": folder_path,
        "extensions": extensions,
    }


async def insert_multimodal_content(
    content_list: list[dict],
    file_reference: str = "direct_input",
    doc_id: str | None = None,
) -> dict:
    """Insert pre-parsed multimodal content directly.

    content_list items should have:
        - type: "text" | "image" | "table" | "equation"
        - text/table_body/latex: the content
        - img_path: path to image file (for type=image)
        - page_idx: optional page index
        - image_caption/table_caption: optional captions
    """
    rag = await get_raganything()
    if rag is None:
        return {
            "status": "error",
            "error": "RAGAnything not available — install raganything package",
        }

    await rag.insert_content_list(
        content_list=content_list,
        file_path=file_reference,
        doc_id=doc_id,
    )
    return {
        "status": "indexed",
        "items": len(content_list),
        "file_reference": file_reference,
    }


async def query_multimodal(
    question: str,
    mode: str = "hybrid",
    multimodal_content: list[dict] | None = None,
) -> str:
    """Query with optional multimodal context.

    If multimodal_content is provided and RAG-Anything is available,
    uses VLM-enhanced query.  Otherwise delegates to standard LightRAG.
    Errors are raised directly — no silent fallback.
    """
    rag = await get_raganything()
    if rag is None:
        from app.ai.lightrag_service import query
        return await query(question, mode=mode)

    if multimodal_content:
        result = await rag.aquery_with_multimodal(
            question,
            multimodal_content=multimodal_content,
            mode=mode,
        )
        return result

    # Standard query through RAG-Anything (delegates to LightRAG)
    result = await rag.aquery(question, mode=mode)
    return result


def is_available() -> bool:
    """Check whether RAG-Anything dependencies are installed."""
    try:
        import raganything  # noqa: F401
        return True
    except ImportError:
        return False
