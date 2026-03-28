#!/usr/bin/env bash
# Start both backend and frontend in parallel for local development.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting NoteGuy development servers..."

# Backend
(
  cd "$ROOT_DIR/backend"
  echo "[backend] Installing dependencies..."
  pip install -q -r requirements.txt
  echo "[backend] Starting FastAPI on http://127.0.0.1:8000"
  python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &

# Frontend
(
  cd "$ROOT_DIR/frontend"
  echo "[frontend] Installing dependencies..."
  npm install --silent
  echo "[frontend] Starting Vite on http://localhost:5173"
  npm run dev
) &

wait
