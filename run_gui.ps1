# GT7 Suspension Tuner - GUI launcher (PowerShell 5.1+ / PowerShell 7+)
# Run from the project folder:  powershell -ExecutionPolicy Bypass -File .\run_gui.ps1
Set-Location -LiteralPath $PSScriptRoot

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "First run: creating .venv and installing PyQt6..."
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $launcher) { $launcher = Get-Command python -ErrorAction SilentlyContinue }
    if (-not $launcher) {
        Write-Error "Python not found. Install Python for Windows from python.org (check 'Add to PATH')."
        exit 1
    }
    & $launcher.Source -m venv (Join-Path $PSScriptRoot ".venv")
    & $venvPy -m pip install --upgrade pip "PyQt6>=6.7,<7"
    if (-not (Test-Path $venvPy)) {
        Write-Error ".venv creation failed."
        exit 1
    }
}
& $venvPy -m gui
