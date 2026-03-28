# NoteVault

A clean, distraction-free markdown note editor with AI-powered RAG chat. Think OneNote — but simpler and more elegant.

NoteVault is a desktop application with a **Python (FastAPI)** backend and a **React + TypeScript** frontend, wrapped in **Tauri** for a lightweight native desktop experience.

## Features

- **Markdown editor** — CodeMirror 6 with JetBrains Mono, syntax highlighting, and auto-save
- **Folder-based organisation** — nested folder tree with scoped note filtering
- **AI chat assistant** — ask questions and get answers sourced from your own notes (RAG)
- **Vector search** — ChromaDB-powered semantic search over your entire vault
- **Dual LLM support** — Anthropic Claude or OpenAI GPT for answer generation
- **Dark-first UI** — minimal Tailwind CSS theme designed for focus

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLModel (SQLite), ChromaDB |
| Frontend | React 19, TypeScript, Vite, Zustand, Tailwind CSS |
| Editor | CodeMirror 6 (markdown mode) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | Anthropic `claude-sonnet-4` / OpenAI `gpt-4o` |
| Desktop | Tauri v2 |

## Project Structure

```
notevault/
  backend/              # Python FastAPI
    app/
      main.py           # App entry point & middleware
      models.py         # SQLModel data models
      notes.py          # CRUD routes for notes & folders
      chat.py           # Chat API routes
      rag.py            # Vector search + LLM generation
      ingestion.py      # Document chunking & embedding pipeline
      context.py        # Active folder context resolver
      vector_store.py   # ChromaDB initialisation
      config.py         # Pydantic settings from .env
      database.py       # SQLite engine & session
    requirements.txt
  frontend/             # React + TypeScript + Vite
    src/
      components/
        Sidebar/        # File tree navigation
        Editor/         # CodeMirror markdown editor
        Chat/           # AI chat pane
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
git clone https://github.com/<your-username>/notevault.git
cd notevault
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

## Environment Variables

All secrets are loaded from a `.env` file in the project root. **Never commit this file.**

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `OPENAI_API_KEY` | OpenAI API key for embeddings and optional GPT |
| `DATABASE_URL` | SQLite connection string (default: `sqlite:///./notevault.db`) |
| `CHROMA_PERSIST_DIR` | ChromaDB storage directory (default: `./chroma_data`) |

See [.env.example](.env.example) for the full template.

## License

MIT
