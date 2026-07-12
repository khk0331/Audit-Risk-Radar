$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

try {
    python --version
} catch {
    Write-Host 'Python is installed but the "python" command is not available in this terminal.'
    Write-Host "Open PowerShell and check: python --version"
    Write-Host 'If it fails, add Python to PATH or reinstall Python with "Add python.exe to PATH" enabled.'
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating Windows virtual environment..."
    python -m venv .venv
}

Write-Host "Installing dashboard dependencies..."
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements-app.txt

Write-Host "Starting Audit Risk Radar..."
Write-Host "Open http://127.0.0.1:8501 if the browser does not open automatically."
& ".venv\Scripts\python.exe" -m streamlit run "audit_risk_radar\app.py" --server.address 127.0.0.1 --server.port 8501
