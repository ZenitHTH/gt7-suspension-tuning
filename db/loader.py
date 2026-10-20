#!/usr/bin/env python3
"""
GT7 Database File & Resource Loader
Handles loading, caching, and fallback parsing for GT7 JSON datasets.
"""

import os
import json
from typing import Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def get_data_dir() -> str:
    """Return the absolute path to the data directory."""
    return DATA_DIR

def load_json(filename: str, default: Any = None) -> Any:
    """Safely load a JSON resource file with typed fallback."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []
