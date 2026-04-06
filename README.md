# NoteGuy

NoteGuy is a local-first markdown workspace with LightRAG-powered retrieval, git-backed note history, and optional multimodal processing via RAG-Anything.

The project is organized as a FastAPI backend, a React frontend, and an optional Tauri desktop shell.

## Features

- Fast markdown editing with folder organization
- LightRAG-powered chat, extraction, and deep analysis over your vault
- Unified LightRAG retrieval across chat and AI tools
- Git-backed version history with diff and restore
- File import support for `.md`, `.txt`, and `.docx`
- Optional multimodal document ingestion (PDF, PPTX, XLSX, images) via RAG-Anything

## AI Architecture

NoteGuy uses a single retrieval path centered on LightRAG.

### LightRAG ingestion and query

For note retrieval and AI operations, note content is indexed into the LightRAG knowledge graph. All primary RAG behavior in the application now resolves through LightRAG query modes (`naive`, `local`, `global`, `hybrid`, `mix`).

Embeddings use a provider abstraction with automatic fallback:

| Provider | Model | Role |
|---|---|---|
| OpenAI | `text-embedding-3-large` | Default provider |
| Ollama (local) | `all-minilm` | Optional fallback when enabled |

### Unified AI router (LightRAG)

The primary AI API is exposed through `/api/ai/*` and powered by LightRAG.

| Endpoint | Purpose |
|---|---|
| `/api/ai/status` | Runtime capabilities and AI config |
| `/api/ai/query` | Knowledge-graph query (`naive`, `local`, `global`, `hybrid`, `mix`) |
| `/api/ai/query/stream` | Streaming graph query (SSE) |
| `/api/ai/ingest/note` | Index a note into the knowledge graph |
| `/api/ai/ingest/all` | Re-index entire vault into the knowledge graph |
| `/api/ai/ingest/document` | Ingest text/multimodal documents |
| `/api/ai/extract` | Entity and relationship extraction |
| `/api/ai/analyze` | Cross-document deep analysis (global mode) |
| `/api/ai/kg/stats` | Knowledge graph statistics |
| `/api/ai/kg/document` | Delete document graph data |

The chat route (`/api/chat` and `/api/chat/stream`) is also LightRAG-backed.

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

## Architecture

### Runtime components

| Component | Responsibility |
|---|---|
| FastAPI backend | API surface, note/folder CRUD, ingestion jobs, RAG chat, history routes |
| SQLite | Metadata for notes, folders, and app state |
| Vault filesystem | Persistent markdown content |
| LightRAG | Knowledge graph build, hybrid query, extraction, deep analysis |
| RAG-Anything (optional) | Multimodal document parsing and ingestion |
| Git service | Versioning, diffs, and restore for note files |
| React frontend | Editor, sidebar, chat panel, and history views |
| Tauri (optional) | Native desktop packaging |

### Data flow

1. User edits a note in the frontend.
2. Backend updates metadata in SQLite and writes markdown to the vault.
3. Background ingestion indexes note content into the LightRAG knowledge graph.
4. AI ingestion routes can index notes/documents into LightRAG's knowledge graph.
5. Git service stages and commits the change for history tracking.
6. Chat and AI routes query the configured retrieval path and call the configured model.
7. Streaming responses are sent to the UI through SSE.

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLModel, GitPython |
| Frontend | React 19, TypeScript, Vite, Zustand, Tailwind CSS |
| Embeddings | OpenAI `text-embedding-3-large` (default) with optional Ollama fallback (`all-minilm`) |
| LLM | OpenAI `gpt-4o` |
| AI frameworks | LightRAG, RAG-Anything (optional) |
| Desktop shell | Tauri v2 (optional) |

## Repository Structure

```
noteguy/
  backend/
    app/
      ai/         # LightRAG and RAG-Anything services + unified AI router
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

Optional: install and run Ollama if you want local embedding fallback.

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

If Ollama is not running, the backend falls back to OpenAI embeddings automatically (when fallback is enabled).

### 6. Optional — multimodal document ingestion

`raganything` is included in backend dependencies. If multimodal parsing dependencies are unavailable in your environment, text-based ingestion still works.

## Configuration

Settings are loaded from `.env` in the project root. Reference: `.env.example`.

### Required

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Required for all AI endpoints and OpenAI embedding fallback |

### Optional

| Variable | Default | Purpose |
|---|---|---|
| `VAULT_PATH` | `~/NoteGuy` (or `./NoteGuy` in `.env.example`) | Root folder for markdown note files |
| `DATABASE_URL` | `sqlite:///./noteguy.db` | SQLModel connection string |
| `EMBEDDING_PROVIDER` | `openai` | Primary embedding provider (`openai` or `ollama`) |
| `EMBEDDING_FALLBACK_PROVIDER` | `ollama` | Fallback embedding provider |
| `EMBEDDING_ALLOW_FALLBACK` | `true` | Enable automatic fallback on embedding errors |
| `EMBEDDING_TIMEOUT_SECONDS` | `8` | Timeout for Ollama embedding requests |
| `EMBEDDING_OLLAMA_MODEL` | `all-minilm` | Ollama embedding model |
| `EMBEDDING_OPENAI_MODEL` | `text-embedding-3-large` | OpenAI embedding model |
| `EMBEDDING_DIMENSION` | `3072` | Embedding vector dimension |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `LLM_MODEL` | `gpt-4o` | Primary chat/completion model |
| `LLM_MAX_TOKENS` | `2048` | Maximum tokens per completion |
| `LIGHTRAG_WORKING_DIR` | `./lightrag_data` | LightRAG persistent working directory |
| `LIGHTRAG_QUERY_MODE` | `hybrid` | Default LightRAG query mode |
| `RAGANYTHING_OUTPUT_DIR` | `./raganything_output` | Output directory for multimodal processing |
| `RAGANYTHING_PARSER` | `mineru` | Multimodal parser backend |

## Troubleshooting

- **Auth errors on chat or search:** confirm `OPENAI_API_KEY` is set in `.env`.
- **Sparse or stale retrieval results:** re-run `/api/ingest/all` or `/api/ai/ingest/all` to rebuild LightRAG indexes.
- **AI tools return sparse graph answers:** run `/api/ai/ingest/all` to rebuild the knowledge graph.
- **Missing file writes:** confirm `VAULT_PATH` exists and is writable.
- **Ollama not available:** set `EMBEDDING_ALLOW_FALLBACK=true` to fall back to OpenAI embeddings automatically.
- **Multimodal upload fails:** verify `raganything` and its parser dependencies are installed in your environment.

## License

MIT
