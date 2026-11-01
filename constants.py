#!/usr/bin/env python3
"""
GT7 Race-Engineering Constants (Canonical Root Reference)
"""

from typing import Dict, Tuple

TIRE_MU_MAP: Dict[str, float] = {
    'CH': 0.85, 'CM': 0.95, 'CS': 1.05,
    'SH': 1.15, 'SM': 1.25, 'SS': 1.35,
    'RH': 1.45, 'RM': 1.55, 'RS': 1.65,
    'Dirt': 0.90, 'Wet': 1.00
}

SLIDER_BOUNDS: Dict[str, Tuple[int, int]] = {
    'anti_roll_bar': (1, 10),
    'damping_compression': (20, 40),
    'damping_expansion': (30, 80),
    'lsd_initial_torque': (4, 30),
    'lsd_accel_sensitivity': (5, 65),
    'lsd_braking_sensitivity': (5, 100),
    'brake_bias_ff': (-5, 0),
    'brake_bias_default': (-5, 5),
}

CHASSIS_RATIOS: Dict[str, float] = {
    'wheelbase_from_length': 0.58,
    'track_width_from_width': 0.85,
    'unsprung_mass_ratio_road': 0.12,
    'unsprung_mass_ratio_race': 0.09,
    'default_motion_ratio': 0.95,
}

CG_HEIGHT_RATIOS: Dict[str, float] = {
    'prototype_racecar': 0.32,
    'suv_pickup': 0.46,
    'standard_road': 0.36,
}

AERO_REFERENCE_SPEED_KMH: float = 240.0

STROKE_CLEARANCE_FLOOR_MM: Dict[str, float] = {
    'widebody': 16.0,
    'standard': 22.0
}
