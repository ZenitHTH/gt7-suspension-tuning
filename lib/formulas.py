#!/usr/bin/env python3
"""
GT7 Race-Engineering Fundamental Physics Formulas
Provides physical primitives: sprung mass calculation, wheel rate Kw,
longitudinal braking pitch dive, lateral cornering roll deflection, and aerodynamic heave.
"""

import math
from typing import Tuple, Optional
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from gt7_constants import CHASSIS_RATIOS, AERO_REFERENCE_SPEED_KMH

def normalize_group(group: Optional[str]) -> str:
    """Normalize raw DB group strings ('X' -> 'Gr.X', 'B' -> 'Gr.B', 'N' -> 'Road Car')."""
    if not group:
        return 'Road Car'
    g = str(group).strip()
    if g == 'X':
        return 'Gr.X'
    if g == 'B':
        return 'Gr.B'
    if g == 'N':
        return 'Road Car'
    return g

def calculate_wheel_rate(fn_hz: float, corner_mass_kg: float) -> float:
    """Calculate effective suspension wheel rate Kw (N/m) from natural frequency and corner mass."""
    return ((2.0 * math.pi * fn_hz) ** 2) * max(50.0, corner_mass_kg)

def calculate_sprung_mass(total_mass_kg: float, front_pct: float, group: str = 'Road Car') -> Tuple[float, float, float]:
    """
    Calculate total sprung mass and per-corner sprung mass (kg).
    Unsprung mass is ~12% on road cars and ~9% on purpose-built racecars.
    """
    grp = normalize_group(group)
    is_race = (grp in ['Gr.1', 'Gr.2', 'Gr.3', 'Gr.X'] or 'Racecar' in grp)
    unsprung_ratio = CHASSIS_RATIOS['unsprung_mass_ratio_race'] if is_race else CHASSIS_RATIOS['unsprung_mass_ratio_road']
    sprung_ratio = 1.0 - unsprung_ratio
    total_sprung = total_mass_kg * sprung_ratio
    corner_front = (total_sprung * front_pct) / 2.0
    corner_rear = (total_sprung * (1.0 - front_pct)) / 2.0
    return round(total_sprung, 1), round(corner_front, 1), round(corner_rear, 1)

def calculate_aerodynamic_heave(df_kg: float, speed_kmh: float, wheel_rate_N_per_m: float) -> float:
    """Calculate suspension aerodynamic heave compression (mm) at velocity v."""
    if wheel_rate_N_per_m <= 0:
        return 0.0
    v_ratio = (speed_kmh / AERO_REFERENCE_SPEED_KMH) ** 2
    f_df_corner = (float(df_kg) * 9.81 * v_ratio) / 2.0
    return (f_df_corner / wheel_rate_N_per_m) * 1000.0

def calculate_braking_pitch_dive(
    mass_kg: float,
    mu: float,
    hcg_m: float,
    wheelbase_m: float,
    wheel_rate_f: float
) -> float:
    """Calculate front corner pitch compression (mm) under 0.55*mu G longitudinal deceleration."""
    if wheel_rate_f <= 0:
        return 0.0
    ax_mps2 = 0.55 * mu * 9.81
    f_pitch_f = (mass_kg * ax_mps2 * hcg_m) / (2.0 * max(1.5, wheelbase_m))
    return (f_pitch_f / wheel_rate_f) * 1000.0

def calculate_cornering_roll_deflection(
    mass_kg: float,
    mu: float,
    hcg_m: float,
    track_width_m: float,
    lltd_f: float,
    arb_f: int,
    wheel_rate_f: float
) -> float:
    """Calculate outside front corner roll compression (mm) under 0.80*mu G lateral acceleration with ARB coupling."""
    if wheel_rate_f <= 0:
        return 0.0
    ay_mps2 = 0.80 * mu * 9.81
    f_roll_f = (lltd_f * mass_kg * ay_mps2 * hcg_m) / max(1.0, track_width_m)
    arb_stiffness_factor = 1.0 + 0.12 * float(arb_f)
    return (f_roll_f / (2.0 * wheel_rate_f * arb_stiffness_factor)) * 1000.0
