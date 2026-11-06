#!/usr/bin/env bash
# GT7 Suspension Tuner - GUI launcher (macOS/Linux).
# Always runs from .venv: creates it if missing, and installs PyQt6 into it
# if missing (a pre-existing half-built venv is repaired, not skipped).
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "First run: creating .venv..."
    python3 -m venv .venv
fi

# Import-based check: repairs venvs that exist but lack PyQt6.
if ! .venv/bin/python -c "import PyQt6" >/dev/null 2>&1; then
    echo "Installing PyQt6 into .venv (first time, ~1 minute)..."
    .venv/bin/pip install --upgrade pip 'PyQt6>=6.7,<7'
fi

exec .venv/bin/python -m gui
