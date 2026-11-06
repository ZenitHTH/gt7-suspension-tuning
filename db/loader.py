#!/usr/bin/env python3
"""
GT7 Database File & Resource Loader
Handles loading, caching, and fallback parsing for GT7 JSON datasets.
"""

import os
import json
import sys
from typing import Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def _frozen_data_dir() -> Optional[str]:
    """Fallback data dir for a frozen (PyInstaller) build: next to the exe."""
    if not getattr(sys, 'frozen', False):
        return None
    return os.path.join(os.path.dirname(os.path.abspath(sys.executable)), 'data')

def get_data_dir() -> str:
    """Return the absolute path to the data directory.

    Precedence: GT7_DATA_DIR env var > bundled/project data dir > frozen
    exe-adjacent data dir. Re-resolved on every call so the env override
    works at runtime and in tests.
    """
    env = os.environ.get('GT7_DATA_DIR')
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    if os.path.isdir(DATA_DIR):
        return DATA_DIR
    frozen = _frozen_data_dir()
    if frozen and os.path.isdir(frozen):
        return frozen
    return DATA_DIR

def load_json(filename: str, default: Any = None) -> Any:
    """Safely load a JSON resource file with typed fallback."""
    path = os.path.join(get_data_dir(), filename)
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []
