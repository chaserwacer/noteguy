# NoteGuy

NoteGuy is a markdown workspace with LightRAG-powered retrieval, git-backed note history, and optional multimodal processing via RAG-Anything.

The project is organized as a FastAPI backend, a React frontend, and an optional Tauri desktop shell.

## Features

- Fast markdown editing with folder organization
- LightRAG-powered chat, extraction, and deep analysis over your vault
- Unified LightRAG retrieval across chat and AI tools
- Git-backed version history with diff and restore
- File import support for `.md`, `.txt`, and `.docx`
- Optional multimodal document ingestion (PDF, PPTX, XLSX, images) via RAG-Anything
- Runtime AI settings panel — choose LLM and embedding providers without restarting
- Deferred ingestion with dirty-note tracking (notes re-indexed on demand or after idle)

## AI Architecture

NoteGuy uses a single retrieval path centered on LightRAG.

### Provider model

LLM and embedding providers are user-configurable at runtime through the Settings panel or the `/api/settings` endpoint. There is no automatic fallback between providers — if the configured provider is unavailable, the error is reported directly to the user and the operation stops.

Settings are persisted to `user_settings.json` and take priority over `.env` values.

| Provider | LLM Models | Embedding Models |
|---|---|---|
| OpenAI | `gpt-4o` (default), any OpenAI model | `text-embedding-3-large` (default) |
| Ollama (local) | `llama3.2` (default), any pulled model | `all-minilm` (default), any pulled model |

### LightRAG ingestion and query

Note content is indexed into the LightRAG knowledge graph. All RAG behavior resolves through LightRAG query modes (`naive`, `local`, `global`, `hybrid`, `mix`).

Notes are marked dirty on edit and re-indexed either:
- Immediately before any AI query (flush on demand)
- Automatically after being idle for one hour (background sweep)

### Unified AI router (LightRAG)

The primary AI API is exposed through `/api/ai/*` and powered by LightRAG.

| Endpoint | Purpose |
|---|---|
| `GET /api/ai/status` | Runtime capabilities and AI config |
| `POST /api/ai/query` | Knowledge-graph query (`naive`, `local`, `global`, `hybrid`, `mix`) |
| `POST /api/ai/query/stream` | Streaming graph query (SSE) |
| `POST /api/ai/ingest/note` | Index a note into the knowledge graph |
| `POST /api/ai/ingest/all` | Re-index entire vault into the knowledge graph |
| `POST /api/ai/ingest/document` | Ingest text/multimodal documents |
| `POST /api/ai/extract` | Entity and relationship extraction |
| `POST /api/ai/extract/note` | Extract entities from a specific note |
| `POST /api/ai/analyze` | Cross-document deep analysis (global mode) |
| `GET /api/ai/kg/stats` | Knowledge graph statistics |
| `DELETE /api/ai/kg/document` | Delete document graph data |

The chat route (`/api/chat` and `/api/chat/stream`) is also LightRAG-backed.

### Settings API

| Endpoint | Purpose |
|---|---|
| `GET /api/settings` | Fetch current AI provider and model configuration |
| `PUT /api/settings` | Update providers, models, and keys at runtime (persisted to `user_settings.json`) |

Changing a provider resets the LightRAG and RAG-Anything singletons so the new configuration takes effect immediately.

### Optional multimodal processing (RAG-Anything)

When `raganything` is installed, document ingestion can process multimodal content and feed the LightRAG knowledge graph. If unavailable, NoteGuy still supports text workflows (`.md`, `.txt`, `.docx`).

## API Surface (High Level)

| Group | Routes |
|---|---|
| Notes/Folders | CRUD routes under `/api/notes` and `/api/folders` |
| History | Git-backed version endpoints under `/api/notes/{id}/...` |
| Chat | `/api/chat`, `/api/chat/stream` |
| Ingestion | `/api/ingest/note/{id}`, `/api/ingest/all`, `/api/ingest/upload` |
| AI Tools | `/api/ai/*` (LightRAG + optional RAG-Anything) |
| Settings | `/api/settings` (runtime AI configuration) |

## Architecture

### Runtime components

| Component | Responsibility |
|---|---|
| FastAPI backend | API surface, note/folder CRUD, ingestion jobs, RAG chat, history routes, settings API |
| SQLite | Metadata for notes, folders, and app state |
| Vault filesystem | Persistent markdown content |
| LightRAG | Knowledge graph build, hybrid query, extraction, deep analysis |
| RAG-Anything (optional) | Multimodal document parsing and ingestion |
| Git service | Versioning, diffs, and restore for note files |
| Ingestion tracker | Dirty-note debouncing — defers LightRAG re-indexing until query or idle timeout |
| React frontend | Editor, sidebar, chat panel, AI tools, and settings views |
| Tauri (optional) | Native desktop packaging |

### Data flow

1. User edits a note in the frontend.
2. Backend updates metadata in SQLite and writes markdown to the vault.
3. The ingestion tracker marks the note as dirty for deferred LightRAG indexing.
4. Git service stages and commits the change for history tracking (batched to avoid input lag).
5. When the user triggers a chat or AI query, all dirty notes are flushed into the knowledge graph first.
6. Chat and AI routes query LightRAG and call the user-configured LLM provider.
7. Streaming responses are sent to the UI through SSE.

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLModel, GitPython |
| Frontend | React 19, TypeScript, Vite, Zustand, Tailwind CSS |
| Embeddings | OpenAI `text-embedding-3-large` or Ollama `all-minilm` (user-selected, no fallback) |
| LLM | OpenAI `gpt-4o` or Ollama `llama3.2` (user-selected, no fallback) |
| AI frameworks | LightRAG, RAG-Anything (optional) |
| Desktop shell | Tauri v2 (optional) |

## Repository Structure

```
noteguy/
  backend/
    app/
      ai/             # LightRAG and RAG-Anything services + unified AI router
      config.py       # Pydantic settings with user_settings.json override
      settings_api.py # Runtime settings REST API
      embeddings.py   # Pluggable embedding providers (OpenAI, Ollama)
      notes.py        # Note CRUD and file I/O
      chat.py         # Conversational LightRAG interface
      ingestion.py    # Document ingestion pipeline
      ingestion_tracker.py  # Dirty-note debouncing and background sweep
      history.py      # Git-backed version history endpoints
      git_service.py  # Git repository wrapper with batched commits
      models.py       # SQLModel data entities
      database.py     # SQLite engine and session
      main.py         # FastAPI app entry, lifespan, routers
    requirements.txt
  frontend/
    src/
      components/     # Editor, Sidebar, Chat, AITools, Settings
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

Add your `OPENAI_API_KEY` to `.env` (or configure it later in the Settings panel).

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

### 5. Optional — Ollama for local models

Install [Ollama](https://ollama.com) and pull models:

```bash
ollama pull llama3.2        # LLM
ollama pull all-minilm      # Embeddings
```

Then switch to Ollama in the Settings panel or set `LLM_PROVIDER=ollama` and `EMBEDDING_PROVIDER=ollama` in `.env`.

### 6. Optional — multimodal document ingestion

`raganything` is included in backend dependencies. If multimodal parsing dependencies are unavailable in your environment, text-based ingestion still works.

## Configuration

Settings are loaded with the following priority:

1. `user_settings.json` (runtime overrides saved via Settings panel or API)
2. Environment variables
3. `.env` file
4. Defaults

Reference: `.env.example`.

### Required

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Required when using OpenAI as LLM or embedding provider |

### Provider selection

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `openai` | LLM provider (`openai` or `ollama`) |
| `EMBEDDING_PROVIDER` | `openai` | Embedding provider (`openai` or `ollama`) |

### Models

| Variable | Default | Purpose |
|---|---|---|
| `LLM_MODEL` | `gpt-4o` | Chat/completion model |
| `LLM_MAX_TOKENS` | `2048` | Maximum tokens per completion |
| `VISION_MODEL` | `gpt-4o` | Vision model for multimodal analysis |
| `EMBEDDING_OPENAI_MODEL` | `text-embedding-3-large` | OpenAI embedding model |
| `EMBEDDING_OLLAMA_MODEL` | `all-minilm` | Ollama embedding model |
| `EMBEDDING_DIMENSION` | `3072` | Embedding vector dimension |
| `EMBEDDING_TIMEOUT_SECONDS` | `8` | Timeout for Ollama embedding requests |

### Infrastructure

| Variable | Default | Purpose |
|---|---|---|
| `VAULT_PATH` | `./NoteGuy` | Root folder for markdown note files |
| `DATABASE_URL` | `sqlite:///./noteguy.db` | SQLModel connection string |
| `BACKEND_HOST` | `127.0.0.1` | Server bind address |
| `BACKEND_PORT` | `8000` | Server port |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Default Ollama LLM model |

### LightRAG tuning

| Variable | Default | Purpose |
|---|---|---|
| `LIGHTRAG_WORKING_DIR` | `./lightrag_data` | LightRAG persistent working directory |
| `LIGHTRAG_CHUNK_TOKEN_SIZE` | `1200` | Chunk size for text splitting |
| `LIGHTRAG_CHUNK_OVERLAP_TOKEN_SIZE` | `100` | Overlap between chunks |
| `LIGHTRAG_TOP_K` | `60` | Number of results for graph retrieval |
| `LIGHTRAG_QUERY_MODE` | `hybrid` | Default query mode |

### RAG-Anything (optional)

| Variable | Default | Purpose |
|---|---|---|
| `RAGANYTHING_OUTPUT_DIR` | `./raganything_output` | Output directory for multimodal processing |
| `RAGANYTHING_PARSER` | `mineru` | Multimodal parser backend |
| `RAGANYTHING_ENABLE_IMAGES` | `true` | Process images in documents |
| `RAGANYTHING_ENABLE_TABLES` | `true` | Process tables in documents |
| `RAGANYTHING_ENABLE_EQUATIONS` | `true` | Process equations in documents |

## Troubleshooting

- **Auth errors on chat or search:** confirm `OPENAI_API_KEY` is set in `.env` or via the Settings panel.
- **Sparse or stale retrieval results:** re-run `/api/ai/ingest/all` or use the AI Tools panel to rebuild the knowledge graph.
- **Provider errors:** check that the selected provider is running and reachable. Ollama must be started separately (`ollama serve`). Errors are reported directly — there is no automatic fallback.
- **Missing file writes:** confirm `VAULT_PATH` exists and is writable.
- **Multimodal upload fails:** verify `raganything` and its parser dependencies are installed in your environment.
- **Settings not taking effect:** the Settings panel persists changes to `user_settings.json` and resets internal caches automatically. If editing `.env` directly, restart the backend.

## License

MIT
