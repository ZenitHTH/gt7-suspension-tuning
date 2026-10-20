#!/usr/bin/env python3
"""
GT7 Race-Engineering Setup Synthesizer & Auto-Tuner (Backward Compatibility Facade)
Re-exports build_setup from root setup.py and format_setup_sheet, main from cli.py.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from setup import build_setup
from cli import format_setup_sheet, main

if __name__ == '__main__':
    main()
