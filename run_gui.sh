#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv && .venv/bin/pip install --upgrade pip 'PyQt6>=6.7,<7'; fi
exec .venv/bin/python -m gui
