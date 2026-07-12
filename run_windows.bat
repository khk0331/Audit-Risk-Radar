@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Windows virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Installing dashboard dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements-app.txt
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo Starting Audit Risk Radar...
echo Open http://127.0.0.1:8501 if the browser does not open automatically.
".venv\Scripts\python.exe" -m streamlit run audit_risk_radar\app.py --server.address 127.0.0.1 --server.port 8501

pause
