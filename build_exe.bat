@echo off
REM Build a standalone Windows app (dist\GT7Tuner\GT7Tuner.exe) of the GT7
REM Suspension Tuner GUI. Run from the project folder on a Windows machine
REM (PyInstaller cannot cross-compile from macOS/Linux).
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip "PyQt6>=6.7,<7"
)

echo [1/3] Installing PyInstaller into .venv...
".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller
if errorlevel 1 goto :fail

echo [2/3] Building GT7Tuner (a few minutes; console shows progress)...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed ^
  --name GT7Tuner ^
  --paths . ^
  --add-data "data;data" ^
  --hidden-import scripts.gt7_db ^
  --hidden-import setup ^
  gui\__main__.py
if errorlevel 1 goto :fail

echo [3/3] Done.
echo     App:  dist\GT7Tuner\GT7Tuner.exe
echo     To share: zip the whole dist\GT7Tuner folder (target PC needs nothing installed).
echo     Saved slider ranges persist in dist\GT7Tuner\_internal\data\cars_master.json.
echo     Override the data location with the GT7_DATA_DIR env var if needed.
echo     To debug a silent crash: remove --windowed, rebuild, and run the exe from cmd.
pause
exit /b 0

:fail
echo BUILD FAILED - read the error above.
pause
exit /b 1
