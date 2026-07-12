@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

%PY% --version >nul 2>nul
if errorlevel 1 (
    echo Python 3 was not found.
    echo Install Python 3.10 or newer from https://www.python.org/downloads/
    echo Make sure "Add python.exe to PATH" is checked during installation.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating Windows virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo Installing dashboard dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements-app.txt
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo Starting Audit Risk Radar...
echo Open http://127.0.0.1:8501 if the browser does not open automatically.
python -m streamlit run audit_risk_radar\app.py --server.address 127.0.0.1 --server.port 8501

pause
