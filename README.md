# NoteGuy

A clean, distraction-free markdown note editor with AI-powered RAG chat and built-in version history. Think OneNote — but simpler and more elegant.

NoteGuy is a desktop application with a **Python (FastAPI)** backend and a **React + TypeScript** frontend, wrapped in **Tauri** for a lightweight native desktop experience.

## Features

- **Markdown editor** — CodeMirror 6 with JetBrains Mono, syntax highlighting, formatting toolbar, and auto-save
- **Live preview** — side-by-side markdown rendering with GitHub-flavoured markdown support
- **Folder-based organisation** — nested folder tree with drag-and-drop, context menus, and scoped note filtering
- **Version history** — automatic git-backed versioning on every change with diff view and one-click restore
- **AI chat assistant** — streaming answers sourced from your own notes (RAG) with source attribution pills
- **Folder-scoped search** — limit AI chat and semantic search to the active folder tree
- **Document upload** — import `.docx` files with heading hierarchy preserved as markdown notes
- **Vector search** — ChromaDB-powered semantic search over your entire vault
- **Dual LLM support** — Anthropic Claude or OpenAI GPT for answer generation
- **Dark-first UI** — minimal Tailwind CSS theme designed for focus

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLModel (SQLite), ChromaDB, GitPython |
| Frontend | React 19, TypeScript, Vite 6, Zustand 5, Tailwind CSS |
| Editor | CodeMirror 6 (markdown mode) |
| Chat UI | @assistant-ui/react with streaming SSE |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | Anthropic `claude-sonnet-4` / OpenAI `gpt-4o` |
| Desktop | Tauri v2 |

## Project Structure

```
noteguy/
  backend/              # Python FastAPI
    app/
      main.py           # App entry point & middleware
      models.py         # SQLModel data models
      notes.py          # CRUD routes for notes & folders
      chat.py           # Chat API routes (streaming SSE)
      rag.py            # Vector search + LLM generation
      ingestion.py      # Document chunking & embedding pipeline
      context.py        # Active folder context resolver
      vector_store.py   # ChromaDB initialisation
      config.py         # Pydantic settings from .env
      database.py       # SQLite engine & session
      git_service.py    # Automatic git versioning for notes
      history.py        # Version history & restore routes
    requirements.txt
  frontend/             # React + TypeScript + Vite
    src/
      components/
        Sidebar/        # File tree, context menus, drag-and-drop
        Editor/         # CodeMirror editor, toolbar, preview, history panel
        Chat/           # Streaming AI chat with source pills
        Layout/         # Split-pane application shell
      store/            # Zustand state management
      api/              # Typed backend HTTP client
  src-tauri/            # Tauri v2 desktop wrapper
  .env.example          # Template for required environment variables
  .gitignore
```

## Getting Started

### Prerequisites

- **Python 3.11+** and `pip`
- **Node.js 18+** and `npm`
- **Rust toolchain** (for Tauri desktop builds — optional for dev)

### 1. Clone and configure

```bash
git clone https://github.com/<your-username>/noteguy.git
cd noteguy
cp .env.example .env
# Edit .env and add your API keys
```

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/health` to verify.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173` with API requests proxied to the backend.

### 4. (Optional) Build the desktop app

```bash
cd src-tauri
cargo tauri dev      # development mode
cargo tauri build    # production build
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Create new note |
| `Ctrl+Shift+P` | Toggle markdown preview |
| `Ctrl+Shift+H` | Toggle version history panel |
| `Ctrl+Shift+C` | Toggle chat pane |

## API Overview

### Notes & Folders

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/notes` | List notes (optional `folder_id` filter) |
| `POST` | `/api/notes` | Create a note |
| `GET` | `/api/notes/{id}` | Get a note |
| `PATCH` | `/api/notes/{id}` | Update a note |
| `DELETE` | `/api/notes/{id}` | Delete a note |
| `GET` | `/api/folders` | List all folders |
| `POST` | `/api/folders` | Create a folder |
| `PATCH` | `/api/folders/{id}` | Rename or move a folder |
| `DELETE` | `/api/folders/{id}` | Delete folder and contents recursively |

### Version History

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/notes/{id}/history` | Commit history for a note |
| `GET` | `/api/notes/{id}/versions/{sha}` | Note content at a specific commit |
| `GET` | `/api/notes/{id}/diff/{sha}` | Unified diff for a commit |
| `POST` | `/api/notes/{id}/restore` | Restore note to a previous version |

### Chat & Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a chat message (non-streaming) |
| `POST` | `/api/chat/stream` | Streaming SSE chat with source attribution |
| `POST` | `/api/search` | Semantic search over notes |
| `GET` | `/api/context/{folder_id}` | Folder context for scoped search |

### Ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ingest/note/{id}` | Re-index a single note |
| `POST` | `/api/ingest/all` | Re-index all notes |
| `POST` | `/api/ingest/upload` | Upload a `.docx` file as a new note |

## Environment Variables

All secrets are loaded from a `.env` file in the project root. **Never commit this file.**

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | — |
| `OPENAI_API_KEY` | OpenAI API key for embeddings and optional GPT | — |
| `DATABASE_URL` | SQLite connection string | `sqlite:///./noteguy.db` |
| `CHROMA_PERSIST_DIR` | ChromaDB storage directory | `./chroma_data` |
| `VAULT_PATH` | Directory where note `.md` files are stored | `~/NoteGuy` |
| `BACKEND_HOST` | Backend server host | `127.0.0.1` |
| `BACKEND_PORT` | Backend server port | `8000` |

See [.env.example](.env.example) for the full template.

## License

MIT
