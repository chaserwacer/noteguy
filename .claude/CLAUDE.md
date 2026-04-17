
--
# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.


### Extra Guidlines
Design clean, well architected code. 
Design code thoughtfully with intelligent, modern design. 
Design reusable components when possible.
Use indicitive variable and method names. 
Prefer docstrings over inline comments. 
Include informative but concise documentation. 
Follow the newest AI/LLM/Agentic coding guidlines and practices. 

#### NoteGuy

NoteGuy is a markdown workspace with LightRAG-powered retrieval, git-backed note history, and optional multimodal processing via RAG-Anything.

The project is organized as a FastAPI backend, a React frontend, and an optional Tauri desktop shell.

#### Features

- Fast markdown editing with folder organization
- LightRAG-powered chat, extraction, and deep analysis over your vault
- Unified LightRAG retrieval across chat and AI tools
- Git-backed version history with diff and restore
- File import support for `.md`, `.txt`, and `.docx`
- Optional multimodal document ingestion (PDF, PPTX, XLSX, images) via RAG-Anything
- Runtime AI settings panel — update OpenAI model names and API key without restarting
- Deferred ingestion with dirty-note tracking (notes re-indexed on demand or after idle)