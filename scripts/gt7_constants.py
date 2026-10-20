#!/usr/bin/env python3
"""Backward-compatibility facade for constants.py"""
import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from constants import (
    TIRE_MU_MAP,
    SLIDER_BOUNDS,
    CHASSIS_RATIOS,
    CG_HEIGHT_RATIOS,
    AERO_REFERENCE_SPEED_KMH,
    STROKE_CLEARANCE_FLOOR_MM
)
