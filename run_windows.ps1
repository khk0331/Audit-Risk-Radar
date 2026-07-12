$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$pythonCommand = if (Get-Command py -ErrorAction SilentlyContinue) {
    @("py", "-3")
} else {
    @("python")
}

function Invoke-ProjectPython {
    param([string[]]$PythonArgs)

    if ($pythonCommand.Length -gt 1) {
        & $pythonCommand[0] $pythonCommand[1] @PythonArgs
    } else {
        & $pythonCommand[0] @PythonArgs
    }
}

try {
    Invoke-ProjectPython @("--version") | Out-Null
} catch {
    Write-Host "Python 3 was not found."
    Write-Host "Install Python 3.10 or newer from https://www.python.org/downloads/"
    Write-Host 'Make sure "Add python.exe to PATH" is checked during installation.'
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating Windows virtual environment..."
    Invoke-ProjectPython @("-m", "venv", ".venv")
}

Write-Host "Installing dashboard dependencies..."
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements-app.txt

Write-Host "Starting Audit Risk Radar..."
Write-Host "Open http://127.0.0.1:8501 if the browser does not open automatically."
& ".venv\Scripts\python.exe" -m streamlit run "audit_risk_radar\app.py" --server.address 127.0.0.1 --server.port 8501
