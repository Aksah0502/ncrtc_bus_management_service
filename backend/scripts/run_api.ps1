$ErrorActionPreference = "Stop"

# Always run from the backend directory.
$BackendRoot = Split-Path -Parent $PSScriptRoot
Set-Location $BackendRoot

# Use the project's virtual environment.
$Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment Python not found: $Python"
}

# Ensure the API and simulator use the development database.
$env:POSTGRES_DB = "ncrtc_bms"
$env:GPS_SIMULATOR_ENABLED = "true"

# Print the database target without exposing credentials.
& $Python -c "from app.core.config import settings; from sqlalchemy.engine import make_url; u=make_url(settings.database_url); print(f'Configured database: {u.host}:{u.port}/{u.database}')"

if ($LASTEXITCODE -ne 0) {
    throw "Database configuration check failed."
}

# Start FastAPI. Its lifespan starts the GPS simulator automatically.
& $Python -m uvicorn app.main:app --reload
