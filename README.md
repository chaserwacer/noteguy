# NoteGuy

NoteGuy is a desktop markdown workspace with local-first note storage, semantic retrieval, and AI-assisted workflows.

The project is organized as a FastAPI backend, a React frontend, and an optional Tauri desktop shell.

## Project Overview

NoteGuy combines three capabilities in one application:
- fast markdown note editing with folder organization
- retrieval-augmented chat grounded in your notes
- git-backed note history with restore and diff support

The backend treats markdown files in your vault as the source of truth, while SQLite stores metadata and relationships.

## Architecture

### Runtime Components

| Component | Responsibility |
|---|---|
| FastAPI backend | API surface, note/folder CRUD, ingestion jobs, RAG chat, history routes |
| SQLite (SQLModel) | Metadata for notes/folders and app state |
| Vault filesystem | Persistent markdown content (`.md`) |
| ChromaDB | Vector index for retrieval and semantic search |
| Git service | Versioning, diffs, and restore for note files |
| React frontend | Editor UI, sidebar, chat panel, and history views |
| Tauri (optional) | Native desktop packaging |

### Data and Request Flow

1. User edits a note in the frontend.
2. Backend updates metadata in SQLite and writes markdown to the vault path.
3. Background ingestion re-chunks note content and updates ChromaDB vectors.
4. Git service stages and commits note changes for history tracking.
5. Chat/search routes retrieve relevant chunks and call the selected model provider.
6. Streaming responses are sent to the UI through SSE.

### Backend Module Map

| Module | Responsibility |
|---|---|
| `backend/app/main.py` | App startup, middleware, router composition, lifecycle init |
| `backend/app/config.py` | Environment-driven configuration via `pydantic-settings` |
| `backend/app/notes.py` | Note/folder CRUD, filesystem sync, ingest + git hooks |
| `backend/app/ingestion.py` | Markdown/docx ingestion and chunking pipeline |
| `backend/app/rag.py` | Retrieval + answer generation (standard chat/search path) |
| `backend/app/chat.py` | Chat endpoints and SSE streaming route |
| `backend/app/vector_store.py` | Chroma collection and embedding function wiring |
| `backend/app/history.py` | History, version content, diff, and restore APIs |
| `backend/app/git_service.py` | Git repository management and commit/history operations |
| `backend/app/ai/*` | Extended framework endpoints (LangChain, DSPy, etc.) |

### Frontend Module Map

| Area | Responsibility |
|---|---|
| `frontend/src/components/Editor` | Markdown editor, preview, toolbar, history panel |
| `frontend/src/components/Sidebar` | Folder/note navigation and context actions |
| `frontend/src/components/Chat` | Assistant panel and streaming runtime integration |
| `frontend/src/store/useNoteStore.ts` | Centralized app state and async actions |
| `frontend/src/api/client.ts` | Typed backend client and request helpers |

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, FastAPI, SQLModel, ChromaDB, GitPython |
| Frontend | React, TypeScript, Vite, Zustand, Tailwind |
| Embeddings | Ollama `all-minilm` (default) with optional OpenAI fallback |
| LLM providers | Anthropic, OpenAI, optional local Ollama routing |
| Desktop shell | Tauri v2 |

## Repository Structure

```text
noteguy/
  backend/
    app/
      ai/
      main.py
      config.py
      notes.py
      chat.py
      rag.py
      ingestion.py
      history.py
      git_service.py
      database.py
      models.py
      vector_store.py
      context.py
    requirements.txt
  frontend/
    src/
      api/
      components/
      store/
      styles/
    package.json
  src-tauri/
  scripts/
    dev.ps1
    dev.sh
  .env.example
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm
- Rust toolchain (only for Tauri desktop development/builds)

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

### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
cd ../frontend
npm install
```

### 3. Run development servers

Script-based startup:

Linux/macOS:

```bash
./scripts/dev.sh
```

Windows PowerShell:

```powershell
./scripts/dev.ps1
```

Manual startup:

Backend:

```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

Default local URLs:
- Frontend: `http://localhost:5173`
- Backend: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/health`

### 4. Optional Tauri desktop run

```bash
cargo tauri dev
```

## Configuration

Settings are loaded from `.env` in the project root.

Reference file: `.env.example`

### Required variables

| Variable | Why it is required |
|---|---|
| `OPENAI_API_KEY` | Required only when using OpenAI embeddings or fallback |

### Provider-specific variables

| Variable | Needed when |
|---|---|
| `ANTHROPIC_API_KEY` | You use Anthropic provider routes (`provider=anthropic`) |

### Optional variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./noteguy.db` | SQLModel connection string |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | Chroma persistence path |
| `VAULT_PATH` | `~/NoteGuy` | Root folder for markdown note files |
| `BACKEND_HOST` | `127.0.0.1` | Backend bind host |
| `BACKEND_PORT` | `8000` | Backend bind port |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name for local routing |
| `EMBEDDING_PROVIDER` | `ollama` | Primary embedding provider (`ollama` or `openai`) |
| `EMBEDDING_FALLBACK_PROVIDER` | `openai` | Fallback provider if primary fails |
| `EMBEDDING_ALLOW_FALLBACK` | `true` | Enable automatic fallback on embedding errors |
| `EMBEDDING_TIMEOUT_SECONDS` | `8` | Timeout used for local embedding calls |
| `EMBEDDING_OLLAMA_MODEL` | `all-minilm` | Ollama embedding model for local vectors |
| `EMBEDDING_OPENAI_MODEL` | `text-embedding-3-small` | OpenAI embedding model when selected |

### Provider behavior notes

- `provider=auto` can route selected light tasks to local Ollama if available.
- Heavy orchestration/query tasks remain on cloud providers.
- Embeddings default to local Ollama (`all-minilm`) and can automatically fall back to OpenAI when enabled.
- Embedding provider selection is centralized and swappable without changing ingestion or retrieval code.

## API Overview

### Core Notes and Folders

- `GET /api/notes`
- `POST /api/notes`
- `GET /api/notes/{note_id}`
- `PATCH /api/notes/{note_id}`
- `PUT /api/notes/{note_id}`
- `DELETE /api/notes/{note_id}`
- `GET /api/folders`
- `POST /api/folders`
- `GET /api/folders/{folder_id}/notes`
- `PATCH /api/folders/{folder_id}`
- `DELETE /api/folders/{folder_id}`

### Search, Chat, and Context

- `POST /api/search`
- `POST /api/chat`
- `POST /api/chat/stream`
- `GET /api/context/{folder_id}`

### Ingestion

- `POST /api/ingest/note/{note_id}`
- `POST /api/ingest/all`
- `POST /api/ingest/upload` (multipart `.docx`)

### History

- `GET /api/notes/{note_id}/history`
- `GET /api/notes/{note_id}/versions/{sha}`
- `GET /api/notes/{note_id}/diff/{sha}`
- `POST /api/notes/{note_id}/restore`

### Extended AI Endpoints

- Base path: `/api/ai`
- Families: `langchain`, `llama-index`, `crewai`, `dspy`, `instructor`, `mem0`, `pydantic-ai`
- Discovery routes:
  - `GET /api/ai/frameworks`
  - `GET /api/ai/routing-info`

## Troubleshooting

- Authentication errors on chat/search: confirm API keys in `.env`.
- Empty retrieval results: re-run ingestion with `POST /api/ingest/all`.
- Local Ollama not selected with `provider=auto`: verify daemon availability at `OLLAMA_BASE_URL`.
- Missing file writes: confirm `VAULT_PATH` is valid and writable.

## License

MIT
