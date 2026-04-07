# Start both backend and frontend in parallel for local development (Windows).
$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot

Write-Host "Starting NoteGuy development servers..." -ForegroundColor Cyan

# Ensure backend Python dependencies are present in the active environment.
Write-Host "Checking backend dependencies..." -ForegroundColor DarkCyan
python -m pip install -r "$RootDir\backend\requirements.txt"

# Backend
$backend = Start-Process -NoNewWindow -PassThru -FilePath "python" `
    -ArgumentList "-m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000" `
    -WorkingDirectory "$RootDir\backend"

# Wait for backend readiness to avoid startup proxy ECONNREFUSED noise in Vite.
$maxAttempts = 60
$attempt = 0
while ($attempt -lt $maxAttempts) {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/health" -TimeoutSec 1 | Out-Null
        break
    } catch {
        Start-Sleep -Milliseconds 500
        $attempt++
    }
}
if ($attempt -ge $maxAttempts) {
    Write-Warning "Backend health check timed out after 30 seconds; starting frontend anyway."
}

# Frontend
$frontend = Start-Process -NoNewWindow -PassThru -FilePath "npm" `
    -ArgumentList "run dev" `
    -WorkingDirectory "$RootDir\frontend"

Write-Host "[backend]  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "[frontend] http://localhost:5173"  -ForegroundColor Green
Write-Host "Press Ctrl+C to stop both servers."

Wait-Process -Id $backend.Id, $frontend.Id
