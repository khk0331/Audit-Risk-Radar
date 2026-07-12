# Windows Setup Guide

This repository includes pre-collected dashboard data, so a Windows user does not need a DART API key to open the app.

## Recommended Quick Start

1. Install Python 3.10 or newer from <https://www.python.org/downloads/>.
2. During installation, check **Add python.exe to PATH**.
3. Download or clone this repository.
4. Double-click `run_windows.bat`.
5. Open <http://127.0.0.1:8501> if the browser does not open automatically.

The script creates `.venv`, installs dashboard dependencies from `requirements-app.txt`, and starts Streamlit.

## PowerShell Alternative

If Windows blocks double-click execution, open PowerShell in the repository folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_windows.ps1
```

## Manual Commands

```powershell
py -3 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-app.txt
python -m streamlit run audit_risk_radar\app.py --server.address 127.0.0.1 --server.port 8501
```

## Common Issues

- `Python was not found`: install Python again and enable **Add python.exe to PATH**.
- `streamlit is not recognized`: use `python -m streamlit ...` instead of `streamlit ...`.
- App opens but no company appears: make sure the `data/` folder was included when downloading the repository.
- DART API key prompt: the dashboard does not need an API key. API keys are required only for recollecting or updating raw DART data.
