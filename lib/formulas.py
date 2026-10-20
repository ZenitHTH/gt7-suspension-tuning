#!/usr/bin/env python3
"""
GT7 Race-Engineering Fundamental Physics Formulas
Provides physical primitives: sprung mass calculation, wheel rate Kw,
longitudinal braking pitch dive, lateral cornering roll deflection, and aerodynamic heave.
"""

import math
from typing import Tuple, Optional, Any
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

def calculate_acceleration_squat_dive(
    torque_nm: float,
    power_hp: float,
    mass_kg: float,
    drivetrain: str,
    hcg_m: float,
    wheelbase_m: float,
    wheel_rate_f: float,
    wheel_rate_r: float,
    tire_radius_m: float = 0.315
) -> dict[str, float]:
    """
    Calculate dynamic rear suspension squat and front lift (mm) under maximum tractive acceleration.
    Calculates drive force limited by tire traction, moment balance Mp = m * ax * hcg,
    and suspension deflections dz_r (squat) and dz_f (lift).
    """
    if wheel_rate_f <= 0 or wheel_rate_r <= 0 or wheelbase_m <= 0:
        return {'squat_rear_mm': 0.0, 'lift_front_mm': 0.0, 'ax_accel_g': 0.0, 'dynamic_pitch_transfer_n': 0.0}

    gear_ratio_mult = 10.0 if drivetrain in ['AWD', '4WD'] else (8.5 if drivetrain == 'FF' else 9.5)
    t_wheel = max(100.0, torque_nm) * gear_ratio_mult * 0.90
    f_drive_raw = t_wheel / max(0.20, tire_radius_m)

    max_g_traction = {'AWD': 1.30, '4WD': 1.30, 'MR': 1.10, 'RR': 1.15, 'FR': 1.00, 'FF': 0.80}.get(drivetrain, 0.95)
    f_drive_cap = mass_kg * 9.81 * max_g_traction
    f_drive = min(f_drive_raw, f_drive_cap)

    ax_mps2 = f_drive / max(500.0, mass_kg)
    ax_g = ax_mps2 / 9.81

    delta_fz_r = (mass_kg * ax_mps2 * hcg_m) / max(1.5, wheelbase_m)

    anti_geo = 0.85
    dz_squat_r = ((delta_fz_r * anti_geo) / (2.0 * wheel_rate_r)) * 1000.0
    dz_lift_f = ((delta_fz_r * anti_geo) / (2.0 * wheel_rate_f)) * 1000.0

    return {
        'squat_rear_mm': round(dz_squat_r, 2),
        'lift_front_mm': round(dz_lift_f, 2),
        'ax_accel_g': round(ax_g, 2),
        'dynamic_pitch_transfer_n': round(delta_fz_r, 1)
    }

def calculate_combined_trail_braking_load(
    mass_kg: float,
    mu: float,
    hcg_m: float,
    wheelbase_m: float,
    track_width_m: float,
    lltd_f: float,
    arb_f: int,
    wheel_rate_f: float,
    speed_kmh: float,
    df_front: float
) -> dict[str, float]:
    """
    Calculate combined outside-front suspension stroke deflection (mm) under trail-braking:
    Combines: Longitudinal Braking Dive + Lateral Cornering Roll + Aerodynamic Heave.
    """
    dz_pitch = calculate_braking_pitch_dive(mass_kg, mu, hcg_m, wheelbase_m, wheel_rate_f)
    dz_roll = calculate_cornering_roll_deflection(mass_kg, mu, hcg_m, track_width_m, lltd_f, arb_f, wheel_rate_f)
    dz_aero = calculate_aerodynamic_heave(df_front, speed_kmh, wheel_rate_f)
    dz_total = dz_pitch + dz_roll + dz_aero

    return {
        'total_deflection_mm': round(dz_total, 2),
        'pitch_component_mm': round(dz_pitch, 2),
        'roll_component_mm': round(dz_roll, 2),
        'aero_component_mm': round(dz_aero, 2)
    }

def calculate_tire_wear_index(
    fn_hz_f: float,
    fn_hz_r: float,
    camber_f: Any,
    camber_r: Any,
    toe_f: Any,
    toe_r: Any,
    ptw: float = 200.0,
    is_endurance: bool = False
) -> dict[str, float]:
    """
    Calculate analytical tire wear degradation index.
    Evaluates micro-slip work caused by suspension stiffness (normal load variation),
    wheel alignment slip scrub (toe friction work), and excessive camber inner-edge abrasion.
    Baseline = 1.00 (standard road suspension on neutral alignment).
    """
    def _parse_val(val: Any) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            parts = val.split()
            try:
                num = float(parts[-1])
                return -num if 'out' in val.lower() else num
            except ValueError:
                return 0.0
        return 0.0

    c_f = abs(_parse_val(camber_f))
    c_r = abs(_parse_val(camber_r))
    t_f = _parse_val(toe_f)
    t_r = _parse_val(toe_r)

    base_fn_f = 2.10
    base_fn_r = 2.25

    wear_k_f = (max(1.0, float(fn_hz_f)) / base_fn_f) ** 1.35
    wear_k_r = (max(1.0, float(fn_hz_r)) / base_fn_r) ** 1.35

    toe_scrub_f = 1.0 + 0.35 * abs(t_f)
    toe_scrub_r = 1.0 + 0.35 * abs(t_r)

    cam_scrub_f = 1.0 + 0.04 * max(0.0, c_f - 2.0)
    cam_scrub_r = 1.0 + 0.04 * max(0.0, c_r - 1.8)

    ptw_factor_r = 1.0 + 0.15 * max(0.0, (ptw - 250.0) / 250.0)
    ptw_factor_f = 1.0

    total_wear_f = wear_k_f * toe_scrub_f * cam_scrub_f * ptw_factor_f
    total_wear_r = wear_k_r * toe_scrub_r * cam_scrub_r * ptw_factor_r

    if is_endurance:
        total_wear_f = total_wear_f ** 1.10
        total_wear_r = total_wear_r ** 1.10

    return {
        'front_wear_factor': round(total_wear_f, 2),
        'rear_wear_factor': round(total_wear_r, 2),
        'relative_rear_bias': round(total_wear_r / max(0.1, total_wear_f), 2)
    }
