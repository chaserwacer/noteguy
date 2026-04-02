# NoteGuy

NoteGuy is a local-first markdown workspace with semantic retrieval, git-backed note history, and a multi-framework AI layer for question answering, structured extraction, and persistent memory.

The project is organized as a FastAPI backend, a React frontend, and an optional Tauri desktop shell.

## Features

- Fast markdown editing with folder organization
- Retrieval-augmented chat grounded in your notes
- Semantic search across your vault
- Git-backed version history with diff and restore
- Seven AI framework integrations for extended workflows
- File import support for `.md` and `.docx`

## AI Architecture

The AI layer is a pipeline: embed → chunk → retrieve → generate. Seven framework integrations sit above the core RAG path, each targeting a distinct use case.

### Embedding and ingestion

Notes are split at markdown headings, then subdivided into ~400-token paragraph chunks. Each chunk is stored in ChromaDB with source metadata so retrieval results always link back to the originating note.

Embeddings use a provider abstraction with automatic fallback:

| Provider | Model | Role |
|---|---|---|
| Ollama (local) | `all-minilm` | Default — private, no API cost |
| OpenAI | `text-embedding-3-small` | Automatic fallback if Ollama is unavailable |

### Core RAG

Chat queries retrieve the most semantically similar chunks (optionally scoped to a folder) and pass them as context to `gpt-4o`. The streaming endpoint emits tokens, source attribution, and a completion signal over SSE so the UI can render progressively.

### Framework integrations

Seven frameworks are available as independent endpoints, each bringing a different paradigm to note-aware AI:

**LangChain** — standard `RetrievalQA` chain backed by the same ChromaDB index, useful as a well-understood baseline.

**LlamaIndex** — maintains its own index with a dedicated query engine and response synthesis, independent of the core retrieval path.

**CrewAI** — multi-agent orchestration. Sequential agent crews (Researcher → Summariser, Researcher → Writer) collaborate to produce research summaries and long-form content from note context.

**DSPy** — declarative prompt programming. QA, summarization, and topic extraction are expressed as typed signatures and wrapped with chain-of-thought reasoning. Prompts are optimizable via DSPy's teleprompter framework without manual rewriting.

**Instructor** — structured extraction with guaranteed schema compliance. Extracts tags, entities, and summaries into validated Pydantic models, automatically retrying on malformed responses.

**Mem0** — persistent, user-scoped memory stored in a dedicated vector collection. The AI accumulates facts across sessions and uses them to personalize responses over time.

**PydanticAI** — type-safe agents with dependency injection. Context (active note, vault titles) is passed into agents through a typed dataclass, and responses carry confidence scores, source references, and suggested follow-up questions.

A model router classifies tasks as light (local-capable) or heavy (cloud-required), providing a clear integration point for routing summarization and extraction tasks to a local model in the future.

## Architecture

### Runtime components

| Component | Responsibility |
|---|---|
| FastAPI backend | API surface, note/folder CRUD, ingestion jobs, RAG chat, history routes |
| SQLite | Metadata for notes, folders, and app state |
| Vault filesystem | Persistent markdown content |
| ChromaDB | Vector index for retrieval and semantic search |
| Git service | Versioning, diffs, and restore for note files |
| React frontend | Editor, sidebar, chat panel, and history views |
| Tauri (optional) | Native desktop packaging |

### Data flow

1. User edits a note in the frontend.
2. Backend updates metadata in SQLite and writes markdown to the vault.
3. Background ingestion re-chunks the note and updates the ChromaDB index.
4. Git service stages and commits the change for history tracking.
5. Chat and search routes retrieve relevant chunks and call the configured model.
6. Streaming responses are sent to the UI through SSE.

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLModel, ChromaDB, GitPython |
| Frontend | React 19, TypeScript, Vite, Zustand, Tailwind CSS |
| Embeddings | Ollama `all-minilm` (default) with OpenAI fallback |
| LLM | OpenAI `gpt-4o` |
| AI frameworks | LangChain, LlamaIndex, CrewAI, DSPy, Instructor, Mem0, PydanticAI |
| Desktop shell | Tauri v2 (optional) |

## Repository Structure

```
noteguy/
  backend/
    app/
      ai/         # Framework integrations and model router
      ...         # Core modules: notes, chat, RAG, ingestion, history, git
    requirements.txt
  frontend/
    src/
      components/ # Editor, Sidebar, Chat, AITools
      store/
      api/
    package.json
  scripts/
    dev.sh
    dev.ps1
  .env.example
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm
- Rust toolchain (only for Tauri desktop builds)

### 1. Clone and configure

```bash
git clone https://github.com/chaserwacer/noteguy.git
cd noteguy
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Add your `OPENAI_API_KEY` to `.env`.

### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
cd ../frontend
npm install
```

### 3. Run development servers

Script-based startup:

```bash
./scripts/dev.sh       # Linux/macOS
./scripts/dev.ps1      # Windows PowerShell
```

Manual startup:

```bash
# Terminal 1
cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2
cd frontend && npm run dev
```

Default local URLs:
- Frontend: `http://localhost:5173`
- Backend: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/health`

### 4. Optional — Tauri desktop

```bash
cargo tauri dev
```

### 5. Optional — local embeddings

Install [Ollama](https://ollama.com) and pull the embedding model:

```bash
ollama pull all-minilm
```

If Ollama is not running, the backend falls back to OpenAI embeddings automatically.

## Configuration

Settings are loaded from `.env` in the project root. Reference: `.env.example`.

### Required

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Required for all AI endpoints and OpenAI embedding fallback |

### Optional

| Variable | Default | Purpose |
|---|---|---|
| `VAULT_PATH` | `~/NoteGuy` | Root folder for markdown note files |
| `DATABASE_URL` | `sqlite:///./noteguy.db` | SQLModel connection string |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB persistence path |
| `EMBEDDING_PROVIDER` | `ollama` | Primary embedding provider (`ollama` or `openai`) |
| `EMBEDDING_ALLOW_FALLBACK` | `true` | Enable automatic fallback on embedding errors |
| `EMBEDDING_OLLAMA_MODEL` | `all-minilm` | Ollama embedding model |
| `EMBEDDING_OPENAI_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |

## Troubleshooting

- **Auth errors on chat or search:** confirm `OPENAI_API_KEY` is set in `.env`.
- **Empty retrieval results:** re-run full ingestion via the API or the ingest button in the UI.
- **Missing file writes:** confirm `VAULT_PATH` exists and is writable.
- **Ollama not available:** set `EMBEDDING_ALLOW_FALLBACK=true` to fall back to OpenAI embeddings automatically.

## License

MIT
