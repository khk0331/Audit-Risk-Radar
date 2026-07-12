# Windows Setup Guide

This repository includes pre-collected dashboard data, so a Windows user does not need a DART API key to open the app.

## Assumption

This guide assumes Python is already installed and available from the terminal.

## Recommended Quick Start

1. Download or clone this repository.
2. Open PowerShell in the repository folder.
3. Run:

```powershell
.\run_windows.bat
```

4. Open <http://127.0.0.1:8501> if the browser does not open automatically.

The script creates `.venv`, installs dashboard dependencies from `requirements-app.txt`, and starts Streamlit.

After this step, no macOS/Linux setup command is needed. The full development commands in the main README are optional and only for running tests or data collection scripts.

## PowerShell Alternative

If Windows blocks double-click execution, open PowerShell in the repository folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_windows.ps1
```

## Manual Commands

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-app.txt
python -m streamlit run audit_risk_radar\app.py --server.address 127.0.0.1 --server.port 8501
```

## Common Issues

- `python is not recognized`: Python is not available from PATH. Add Python to PATH or reinstall Python with **Add python.exe to PATH** enabled.
- `streamlit is not recognized`: use `python -m streamlit ...` instead of `streamlit ...`.
- App opens but no company appears: make sure the `data/` folder was included when downloading the repository.
- DART API key prompt: the dashboard does not need an API key. API keys are required only for recollecting or updating raw DART data.
