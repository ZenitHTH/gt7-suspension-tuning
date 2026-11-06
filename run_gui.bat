@echo off
REM GT7 Suspension Tuner - GUI launcher (Windows cmd / double-click)
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :run

echo First run: creating .venv and installing PyQt6...
where py >nul 2>nul
if %errorlevel%==0 (
    py -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip "PyQt6>=6.7,<7"
) else (
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip "PyQt6>=6.7,<7"
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo ERROR: .venv\Scripts\python.exe not found after creation.
    echo Install Python for Windows from python.org (check "Add to PATH") and retry.
    pause
    exit /b 1
)

:run
".venv\Scripts\python.exe" -m gui
