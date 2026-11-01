#!/usr/bin/env python3
"""
GT7 Suspension Equilibrium & Trail-Braking Simulation Module
Simulates outside-front stroke compression under high-speed trail-braking
and solves closed-form suspension equilibrium for optimal clearances and dynamic rake.
"""

import math
from typing import Dict, Tuple, Optional, Any
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from gt7_constants import STROKE_CLEARANCE_FLOOR_MM
from lib.formulas import (
    normalize_group,
    calculate_wheel_rate,
    calculate_sprung_mass,
    calculate_aerodynamic_heave,
    calculate_braking_pitch_dive,
    calculate_cornering_roll_deflection,
    calculate_acceleration_squat_dive,
    calculate_combined_trail_braking_load
)


def _compute_deflections(
    speed_kmh: float,
    mass_kg: float,
    corner_f: float,
    corner_r: float,
    hcg_m: float,
    wheelbase_m: float,
    track_width_m: float,
    mu: float,
    fn_f: float,
    fn_r: float,
    arb_f: int,
    arb_r: int,
    df_f: int,
    df_r: int
) -> Tuple[float, float, float, float, float]:
    """Compute individual deflection components under braking and cornering."""
    kw_f = calculate_wheel_rate(fn_f, corner_f)
    kw_r = calculate_wheel_rate(fn_r, corner_r)

    dz_aero_f = calculate_aerodynamic_heave(df_f, speed_kmh, kw_f)
    dz_aero_r = calculate_aerodynamic_heave(df_r, speed_kmh, kw_r)
    dz_pitch_f = calculate_braking_pitch_dive(mass_kg, mu, hcg_m, wheelbase_m, kw_f)

    lltd_f = float(arb_f) / max(1.0, float(arb_f + arb_r))
    dz_roll_f = calculate_cornering_roll_deflection(mass_kg, mu, hcg_m, track_width_m, lltd_f, arb_f, kw_f)
    return dz_aero_f, dz_aero_r, dz_pitch_f, dz_roll_f, (dz_aero_f + dz_pitch_f + dz_roll_f)


def _evaluate_stroke_clearance(
    rh_front_mm: int,
    rh_rear_mm: int,
    height_min_front_mm: int,
    is_widebody: bool,
    dz_tot_f: float,
    dz_aero_f: float,
    dz_aero_r: float
) -> Tuple[float, float, bool, int]:
    """Calculate dynamic clearance, rake, and bottoming indicators."""
    floor_key = 'widebody' if is_widebody else 'standard'
    stroke_floor = STROKE_CLEARANCE_FLOOR_MM[floor_key]
    z_avail_f = float(rh_front_mm - height_min_front_mm) + stroke_floor
    bottoming = (dz_tot_f >= z_avail_f)
    bump_rh = max(0, math.ceil(dz_tot_f - z_avail_f + 2.0)) if bottoming else 0
    dyn_clearance = z_avail_f - dz_tot_f
    dyn_rake = float(rh_rear_mm - dz_aero_r) - float(rh_front_mm - dz_aero_f)
    return dyn_clearance, dyn_rake, bottoming, bump_rh


def simulate_high_speed_trail_braking(
    speed_kmh: float,
    mass_kg: float,
    corner_front_kg: float,
    corner_rear_kg: float,
    wf: float,
    hcg_m: float,
    wheelbase_m: float,
    track_width_m: float,
    mu: float,
    rh_front_mm: int,
    rh_rear_mm: int,
    fn_front_hz: float,
    fn_rear_hz: float,
    arb_front: int,
    arb_rear: int,
    df_front: int,
    df_rear: int,
    is_widebody: bool = False,
    height_min_front_mm: int = 90
) -> Dict[str, Any]:
    """Simulate outside-front suspension stroke compression under high-speed trail-braking."""
    dz_aero_f, dz_aero_r, dz_pitch_f, dz_roll_f, dz_tot_f = _compute_deflections(
        speed_kmh, mass_kg, corner_front_kg, corner_rear_kg, hcg_m, wheelbase_m, track_width_m,
        mu, fn_front_hz, fn_rear_hz, arb_front, arb_rear, df_front, df_rear
    )
    dyn_clearance, dyn_rake, bottoming, bump_rh = _evaluate_stroke_clearance(
        rh_front_mm, rh_rear_mm, height_min_front_mm, is_widebody, dz_tot_f, dz_aero_f, dz_aero_r
    )
    return {
        'speed_kmh': round(speed_kmh, 1),
        'aero_compression_mm': {'front': round(dz_aero_f, 1), 'rear': round(dz_aero_r, 1)},
        'pitch_compression_front_mm': round(dz_pitch_f, 1),
        'roll_compression_front_mm': round(dz_roll_f, 1),
        'total_outside_front_compression_mm': round(dz_tot_f, 1),
        'dynamic_outside_front_clearance_mm': round(dyn_clearance, 1),
        'dynamic_rake_mm': round(dyn_rake, 1),
        'bottoming_or_fender_hit': bottoming,
        'recommended_front_rh_bump_mm': bump_rh
    }


def _resolve_equilibrium_bounds(
    grp: str,
    is_dirt: bool,
    body_style: str,
    height_range: Optional[Tuple[int, int]],
    height_front_range: Optional[Tuple[int, int]],
    height_rear_range: Optional[Tuple[int, int]]
) -> Tuple[int, int, int, int]:
    """Resolve physical min/max ride height bounds for equilibrium solving."""
    if height_front_range and height_rear_range:
        return height_front_range[0], height_front_range[1], height_rear_range[0], height_rear_range[1]
    if height_range:
        return height_range[0], height_range[1], height_range[0], height_range[1]
    bounds = {
        'Gr.X': (45, 80, 50, 85), 'Gr.1': (45, 80, 50, 85),
        'Gr.2': (55, 95, 60, 100), 'Gr.3': (55, 95, 60, 100),
        'Gr.4': (75, 120, 80, 125)
    }
    if grp in bounds:
        return bounds[grp]
    if is_dirt or grp == 'Gr.B':
        return 130, 175, 135, 180
    if body_style in ['SUV', 'Pickup']:
        return 120, 170, 125, 175
    return 90, 140, 95, 145


def _calculate_optimal_equilibrium_heights(
    h_min_f: int,
    h_max_f: int,
    h_min_r: int,
    h_max_r: int,
    dz_trail_f: float,
    bump_margin: float,
    stroke_floor: float,
    front_ratio: float,
    dz_squat_r: float,
    dz_lift_f: float
) -> Tuple[int, int]:
    """Compute optimal static front and rear ride heights satisfying stroke and squat clearance."""
    h_f_target = h_min_f + max(0.0, dz_trail_f + bump_margin - stroke_floor)
    opt_h_f = min(h_max_f, max(h_min_f, int(round(h_f_target))))

    base_rake = 6 if front_ratio <= 0.50 else min(14, round(6.0 + 16.0 * (front_ratio - 0.50)))
    rake_needed = max(float(base_rake), round(dz_squat_r * 0.75 + dz_lift_f * 0.50 + 4.0))
    opt_h_r = min(h_max_r, max(h_min_r, int(round(opt_h_f + rake_needed))))
    return opt_h_f, opt_h_r


def _compute_equilibrium_deflections(
    mass_kg: float,
    front_ratio: float,
    power_hp: float,
    torque_nm: float,
    drivetrain: str,
    hcg_m: float,
    wheelbase_m: float,
    track_width_m: float,
    mu: float,
    fn_f: float,
    fn_r: float,
    arb_f: int,
    arb_r: int,
    df_f: int,
    df_r: int,
    speed_kmh: float,
    group: str
) -> Tuple[float, float, float, float, float]:
    """Calculate squat, lift, trail deflection, and aero heave for equilibrium solver."""
    _, c_f, c_r = calculate_sprung_mass(mass_kg, front_ratio, group)
    kw_f, kw_r = calculate_wheel_rate(fn_f, c_f), calculate_wheel_rate(fn_r, c_r)

    squat = calculate_acceleration_squat_dive(
        torque_nm=torque_nm, power_hp=power_hp, mass_kg=mass_kg,
        drivetrain=drivetrain, hcg_m=hcg_m, wheelbase_m=wheelbase_m,
        wheel_rate_f=kw_f, wheel_rate_r=kw_r
    )
    lltd_f = float(arb_f) / max(1.0, float(arb_f + arb_r))
    trail = calculate_combined_trail_braking_load(
        mass_kg=mass_kg, mu=mu, hcg_m=hcg_m, wheelbase_m=wheelbase_m,
        track_width_m=track_width_m, lltd_f=lltd_f, arb_f=arb_f,
        wheel_rate_f=kw_f, speed_kmh=speed_kmh, df_front=float(df_f)
    )
    dz_aero_r = calculate_aerodynamic_heave(float(df_r), speed_kmh, kw_r)
    return squat['squat_rear_mm'], squat['lift_front_mm'], trail['total_deflection_mm'], dz_aero_r, kw_f


def _calculate_compliance_status(
    opt_h_f: int,
    h_min_f: int,
    stroke_floor: float,
    dz_trail_f: float
) -> Tuple[float, bool, float]:
    """Calculate front dynamic clearance, feasibility flag, and natural frequency boost."""
    dyn_clearance = float(opt_h_f - h_min_f) + stroke_floor - dz_trail_f
    trail_feasible = (dyn_clearance >= 10.0)
    fn_boost = round(max(0.0, (12.0 - dyn_clearance) * 0.04), 2) if not trail_feasible else 0.0
    return dyn_clearance, trail_feasible, fn_boost


def _format_equilibrium_solution(
    opt_h_f: int,
    opt_h_r: int,
    dyn_clearance_f: float,
    dz_trail_f: float,
    dz_squat_r: float,
    dz_lift_f: float,
    dz_aero_r: float,
    trail_feasible: bool,
    fn_boost: float
) -> Dict[str, Any]:
    """Format equilibrium result payload."""
    return {
        'optimal_rh_front': int(opt_h_f), 'optimal_rh_rear': int(opt_h_r),
        'trail_braking_feasible': trail_feasible,
        'min_dynamic_clearance_mm': round(dyn_clearance_f, 1),
        'total_trail_compression_front_mm': round(dz_trail_f, 1),
        'acceleration_squat_rear_mm': round(dz_squat_r, 1),
        'acceleration_lift_front_mm': round(dz_lift_f, 1),
        'dynamic_rake_accel_mm': round((opt_h_r - dz_squat_r) - (opt_h_f + dz_lift_f), 1),
        'dynamic_rake_brake_mm': round((opt_h_r - dz_aero_r) - (opt_h_f - dz_trail_f), 1),
        'recommended_front_fn_boost_hz': fn_boost
    }


def solve_suspension_equilibrium(
    mass_kg: float,
    front_ratio: float,
    power_hp: float,
    torque_nm: float,
    drivetrain: str,
    hcg_m: float,
    wheelbase_m: float,
    track_width_m: float,
    mu: float,
    fn_f: float,
    fn_r: float,
    arb_f: int,
    arb_r: int,
    df_f: int = 0,
    df_r: int = 0,
    height_range: Optional[Tuple[int, int]] = None,
    height_front_range: Optional[Tuple[int, int]] = None,
    height_rear_range: Optional[Tuple[int, int]] = None,
    speed_kmh: float = 200.0,
    is_widebody: bool = False,
    group: str = 'Road Car',
    body_style: str = 'Coupe',
    bumpiness: str = 'medium',
    is_dirt: bool = False
) -> Dict[str, Any]:
    """Solve closed-form physical suspension equilibrium for static heights and dynamic clearances."""
    grp = normalize_group(group)
    h_min_f, h_max_f, h_min_r, h_max_r = _resolve_equilibrium_bounds(
        grp, is_dirt, body_style, height_range, height_front_range, height_rear_range
    )
    dz_squat_r, dz_lift_f, dz_trail_f, dz_aero_r, _ = _compute_equilibrium_deflections(
        mass_kg, front_ratio, power_hp, torque_nm, drivetrain, hcg_m, wheelbase_m,
        track_width_m, mu, fn_f, fn_r, arb_f, arb_r, df_f, df_r, speed_kmh, group
    )
    stroke_floor = STROKE_CLEARANCE_FLOOR_MM['widebody' if is_widebody else 'standard']
    bump_margin = 14.0 if bumpiness == 'high' else (12.0 if bumpiness == 'medium' else 10.0)
    opt_h_f, opt_h_r = _calculate_optimal_equilibrium_heights(
        h_min_f, h_max_f, h_min_r, h_max_r, dz_trail_f, bump_margin, stroke_floor, front_ratio, dz_squat_r, dz_lift_f
    )
    dyn_clearance, trail_feasible, fn_boost = _calculate_compliance_status(opt_h_f, h_min_f, stroke_floor, dz_trail_f)
    return _format_equilibrium_solution(
        opt_h_f, opt_h_r, dyn_clearance, dz_trail_f, dz_squat_r, dz_lift_f, dz_aero_r, trail_feasible, fn_boost
    )
