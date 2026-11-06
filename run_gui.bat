@echo off
REM GT7 Suspension Tuner - GUI launcher (Windows cmd / double-click)
REM Self-diagnosing: pre-checks Python bitness + PyQt6 import, so a failure
REM prints the real cause instead of a silent "fatal error" crash.
setlocal
cd /d "%~dp0"

REM UTF-8 console output so Thai/symbol text cannot abort the launcher
set PYTHONIOENCODING=utf-8

REM --- resolve a Python launcher --------------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo.
    echo [FATAL] Python for Windows not found on PATH.
    echo   Install 64-bit Python 3.12+ from https://python.org
    echo   and tick "Add to PATH" during install. Reopen this folder, retry.
    pause
    exit /b 1
)

REM --- ensure venv exists (created if missing) --------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo First run: creating .venv...
    %PY% -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo [FATAL] Could not create .venv. Try running this from an admin cmd.
        pause
        exit /b 1
    )
)
set "VPY=.venv\Scripts\python.exe"

REM --- preflight 1: 64-bit check (PyQt6 is 64-bit ONLY) ----------------------
"%VPY%" -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8==64 else 3)"
if errorlevel 3 (
    echo.
    echo [FATAL] 32-bit Python detected - PyQt6 requires 64-bit Python.
    echo   This is the most common cause of a "fatal error" on Windows.
    echo   Uninstall the 32-bit Python, install the 64-bit one from python.org,
    echo   then delete this .venv folder and re-run run_gui.bat.
    pause
    exit /b 1
)

REM --- install PyQt6 only if missing (repairs half-built venvs) --------------
"%VPY%" -c "import PyQt6" >nul 2>nul
if errorlevel 1 (
    echo Installing PyQt6 into .venv (first time, ~1 minute)...
    "%VPY%" -m pip install --upgrade pip
    "%VPY%" -m pip install "PyQt6>=6.7,<7"
    if errorlevel 1 (
        echo.
        echo [FATAL] pip install failed (see above). Usually a network/proxy issue.
        pause
        exit /b 1
    )
)

REM --- preflight 2: PyQt6 actually imports (catches DLL / VC++-runtime crash) --
"%VPY%" -c "from PyQt6 import QtCore, QtWidgets, QtGui; print('PyQt6', QtCore.PYQT_VERSION_STR, 'imports OK')"
if errorlevel 1 (
    echo.
    echo [FATAL] PyQt6 failed to import (DLL load error / missing VC++ runtime).
    echo   1) Re-run this script once more (the .venv may be half-built).
    echo   2) If it persists, install the latest "Microsoft Visual C++ Redistributable".
    echo   3) Still failing: delete the .venv folder and re-run run_gui.bat.
    pause
    exit /b 1
)

REM --- launch (any traceback goes to this console, not a silent crash) -------
echo Launching GT7 Suspension Tuner...
"%VPY%" -m gui
set "RC=%errorlevel%"
if not "%RC%"=="0" (
    echo.
    echo [FATAL] GUI exited with code %RC%. Traceback (if any) is above.
    echo   Send that text to the maintainer to pin the exact fix.
)
pause
exit /b %RC%
