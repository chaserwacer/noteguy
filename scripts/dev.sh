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

echo "[backend] Waiting for health endpoint..."
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

# Frontend
(
  cd "$ROOT_DIR/frontend"
  echo "[frontend] Installing dependencies..."
  npm install --silent
  echo "[frontend] Starting Vite on http://localhost:5173"
  npm run dev
) &

wait
