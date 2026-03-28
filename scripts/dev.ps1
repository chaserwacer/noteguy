# Start both backend and frontend in parallel for local development (Windows).
$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot

Write-Host "Starting NoteGuy development servers..." -ForegroundColor Cyan

# Backend
$backend = Start-Process -NoNewWindow -PassThru -FilePath "python" `
    -ArgumentList "-m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000" `
    -WorkingDirectory "$RootDir\backend"

# Frontend
$frontend = Start-Process -NoNewWindow -PassThru -FilePath "npm" `
    -ArgumentList "run dev" `
    -WorkingDirectory "$RootDir\frontend"

Write-Host "[backend]  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "[frontend] http://localhost:5173"  -ForegroundColor Green
Write-Host "Press Ctrl+C to stop both servers."

Wait-Process -Id $backend.Id, $frontend.Id
