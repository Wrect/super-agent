@echo off
REM Omni-OCR Agent Runner
REM Automatically uses the local virtual environment

set VENV_PATH=%~dp0.venv\Scripts\python.exe

if not exist "%VENV_PATH%" (
    echo [ERROR] Virtual environment not found at .venv\
    echo Please ensure the .venv folder exists in this directory.
    exit /b 1
)

"%VENV_PATH%" "%~dp0main.py" %*
