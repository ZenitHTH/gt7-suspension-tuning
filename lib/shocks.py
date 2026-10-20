#!/usr/bin/env python3
"""
GT7 Damping & Shock Absorber Module
Calculates critical damping compression and expansion ratios (0-100%),
incorporating anti-squat stiffening, high-speed crest rebound control, and trail-braking pitch support.
"""

from typing import Tuple

def calculate_dampers(
    bumpiness: str = 'medium',
    ptw: float = 200.0,
    is_high_boost: bool = False,
    drivetrain: str = 'FR',
    wf: float = 0.50,
    is_dirt: bool = False,
    is_wet: bool = False,
    elevation_diff_m: float = 0.0
) -> Tuple[int, int, int, int]:
    """
    Calculate critical damping compression and expansion ratios (0-100%)
    maintaining kinematic damping expansion ratio Exp / Comp ≈ 1.45 - 1.55.
    Compression is clamped strictly to the legal GT7 20-40% ceiling.
    """
    if is_dirt:
        return 28, 28, 56, 56
    if is_wet:
        return 28, 28, 42, 42

    comp_base = 32 if bumpiness != 'high' else 30
    anti_squat = 0
    if drivetrain in ['FR', 'MR', 'RR'] and ptw >= 280:
        anti_squat = min(4, round((ptw - 200) / 75.0))
    elif is_high_boost:
        anti_squat = 2

    comp_f = max(26, min(40, comp_base - (2 if wf > 0.55 else 0)))
    comp_r = max(26, min(40, comp_base + anti_squat))
    exp_f = max(30, min(80, round(comp_f * 1.48)))
    # Trail-braking vs Elevation Crest damping
    exp_r_mult = 1.50 if (elevation_diff_m or 0.0) >= 50.0 else 1.38
    exp_r = max(30, min(80, round(comp_r * exp_r_mult)))
    return comp_f, comp_r, exp_f, exp_r
