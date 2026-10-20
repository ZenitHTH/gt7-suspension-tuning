#!/usr/bin/env python3
"""
GT7 Aerodynamics & Body Clearance Module
Calculates front and rear ground clearance (ride height), downforce mapping with Center of Pressure (CP),
and simulates outside-front suspension stroke bottoming under high-speed trail-braking.
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

def calculate_ride_height(
    is_dirt: bool = False,
    is_racecar: bool = False,
    is_ultralight: bool = False,
    body_style: str = 'Coupe',
    bumpiness: str = 'medium',
    ptw: float = 200.0,
    wf: float = 0.50,
    height_range: Optional[Tuple[int, int]] = None,
    height_front_range: Optional[Tuple[int, int]] = None,
    height_rear_range: Optional[Tuple[int, int]] = None,
    elevation_diff_m: float = 0.0,
    is_widebody: bool = False,
    height_m: float = 1.30,
    group: str = 'Road Car'
) -> Tuple[int, int]:
    """Calculate front ground clearance and positive rake angle (mm) from vehicle geometry."""
    elev_buf = 4 if (not is_dirt and (elevation_diff_m or 0.0) >= 50.0) else 0
    wide_buf = 5 if (is_widebody and not is_dirt) else 0
    total_buf = elev_buf + wide_buf
    grp = normalize_group(group)

    if height_front_range and height_rear_range:
        h_min_f, h_max_f = height_front_range
        h_min_r, h_max_r = height_rear_range
        base_f = h_min_f + (3 if is_racecar or is_ultralight else (12 if bumpiness == 'high' else 10)) + total_buf
        base_f = min(h_max_f, base_f)
        rake = 7 if wf <= 0.53 else min(12, round(7.0 + 15.0 * (wf - 0.50)))
        base_r = min(h_max_r, max(h_min_r, base_f + rake))
        return base_f, base_r

    if height_range:
        h_min, h_max = height_range
        base_f = h_min + (4 if is_racecar or is_ultralight else (12 if bumpiness == 'high' else 10)) + total_buf
        base_f = min(h_max, base_f)
        rake = 7 if wf <= 0.53 else min(12, round(7.0 + 15.0 * (wf - 0.50)))
        return base_f, min(h_max, base_f + rake)

    if is_dirt:
        return 150, 155

    # Group & Silhouette Physical Height Modeling (GT7 Update 1.72 Spec)
    if grp in ['Gr.X', 'Gr.1']:
        base_f = (50 if bumpiness != 'high' else 55) + total_buf
        return base_f, base_f + 5
    if grp in ['Gr.2', 'Gr.3']:
        base_f = (65 if bumpiness != 'high' else 70) + total_buf
        return base_f, base_f + 7
    if grp == 'Gr.4':
        # Gr.4 uses production-car chassis geometry with cup suspension (slider floor 85-95mm)
        base_f = (85 if bumpiness != 'high' else 90) + total_buf
        rake = round(6.0 + 14.0 * max(0.0, wf - 0.45))
        rake = max(6, min(12, rake))
        return base_f, base_f + rake
    if grp == 'Gr.B':
        base_f = (90 if bumpiness != 'high' else 95) + total_buf
        return base_f, base_f + 8

    if is_ultralight:
        base_f = (60 if bumpiness != 'high' else 65) + total_buf
        rake = 12 if ptw >= 500 else 10
        return base_f, base_f + rake
    if is_racecar:
        base_f = (65 if bumpiness != 'high' else 70) + total_buf
        return base_f, base_f + 7
    if body_style in ['SUV', 'Pickup'] or (height_m or 1.30) >= 1.65:
        base_f = (135 if bumpiness != 'high' else 140) + total_buf
        return base_f, base_f + 10

    # Road cars: Physically scaled by roofline silhouette (height_m) and weight distribution
    h_val = height_m or 1.30
    if body_style in ['SUV', 'Pickup', 'Minivan', 'Van'] or h_val >= 1.60:
        base_f = (135 if bumpiness != 'high' else 140) + total_buf
    elif h_val >= 1.48:
        base_f = (105 if bumpiness != 'high' else 110) + total_buf
    else:
        # Standard road sports, coupes and sedans (slider floor typically 90-100mm)
        base_f = (100 if bumpiness != 'high' else 105) + total_buf

    rake = round(6.0 + 16.0 * max(0.0, wf - 0.45))
    rake = max(5, min(14, rake))
    return base_f, base_f + rake

def calculate_aerodynamics(
    df_front_range: Optional[Tuple[int, int]] = None,
    df_rear_range: Optional[Tuple[int, int]] = None,
    wf: float = 0.50,
    group: str = 'Road Car',
    is_oval: bool = False,
    downforce_demand: str = 'medium',
    is_endurance: bool = False,
    width_m: float = 1.80,
    height_m: float = 1.30,
    body_style: str = 'Coupe'
) -> Dict[str, Any]:
    """Calculate front and rear downforce matching Center of Pressure (CP) to mass distribution and frontal area."""
    demand = (downforce_demand or 'medium').lower()
    grp = normalize_group(group)

    if df_front_range and df_rear_range:
        f_min, f_max = df_front_range
        r_min, r_max = df_rear_range
        span_f = f_max - f_min
        span_r = r_max - r_min

        if is_oval:
            ratio_f = 0.15
            ratio_r = 0.15
            preset = 'Low Drag Oval / Super Speedway Spec'
        elif span_f == 0 and f_min > 0 and r_min > f_min:
            ratio_f = 1.0
            ratio_r = 0.0
            preset = 'Fixed Front Floor Balance (Anti-High-Speed-Push)'
        elif wf >= 0.55:
            ratio_f = 0.80
            ratio_r = 0.30 if demand == 'low' else (0.45 if demand == 'high' else 0.35)
            preset = 'Anti-Understeer Front-Biased'
        elif is_endurance:
            if grp == 'Gr.X':
                ratio_f, ratio_r = (0.45, 0.55)
            elif wf <= 0.46:
                ratio_f, ratio_r = (0.40, 0.70)
            else:
                ratio_f, ratio_r = (0.45, 0.60)
            preset = 'Tire-Saver Center-of-Pressure (CP) Balanced'
        else:
            ratio_f, ratio_r = {'low': (0.40, 0.40), 'medium': (0.60, 0.60), 'high': (0.80, 0.75)}.get(demand, (0.60, 0.60))
            preset = f'Physics First-Principles Optimized ({demand.capitalize()} Downforce)'

        df_f = round(f_min + span_f * ratio_f)
        df_r = round(r_min + span_r * ratio_r)
        return {
            'front': df_f, 'rear': df_r,
            'range_f': f'{f_min}-{f_max}', 'range_r': f'{r_min}-{r_max}',
            'preset': preset
        }

    # First-Principles Aerodynamic Calculation when slider ranges are not provided:
    # 1. Frontal Area Estimation (A = width * height * shape_factor)
    k_body = 0.88 if body_style in ['SUV', 'Pickup', 'Van'] else (
        0.78 if grp in ['Gr.X', 'Gr.1'] else (
            0.82 if grp in ['Gr.2', 'Gr.3'] else 0.84
        )
    )
    w_val = width_m or 1.80
    h_val = height_m or 1.30
    a_frontal = w_val * h_val * k_body
    k_area = max(0.85, min(1.20, math.sqrt(a_frontal / 2.0)))
    k_demand = 0.60 if is_oval else {'low': 0.88, 'medium': 1.00, 'high': 1.15}.get(demand, 1.00)

    # 2. Physics Category Archetype Spans & Baselines
    if grp == 'Gr.X':
        span_f, span_r = (800, 1200), (1200, 1600)
        base_f = 980 if is_endurance else 1040
        base_r = 1420 if is_endurance else 1440
        preset = 'Physics Prototype High Downforce'
    elif grp == 'Gr.1':
        span_f, span_r = (700, 1000), (1100, 1600)
        base_f, base_r = 850, 1350
        preset = 'Physics Prototype Le Mans Downforce'
    elif grp == 'Gr.2':
        span_f, span_r = (500, 700), (800, 1100)
        base_f, base_r = 620, 950
        preset = 'Physics Super GT / DTM Aerodynamic Balance'
    elif grp == 'Gr.3':
        span_f, span_r = (350, 450), (500, 700)
        base_f, base_r = 430, 630
        preset = 'Physics FIA GT3 Aerodynamic Balance'
    elif grp == 'Gr.4':
        # Gr.4 FIA GT4 / Touring Aerodynamics: Splitter + Production Rear Wing
        span_f, span_r = (80, 180), (150, 320)
        base_f, base_r = 125, 220
        preset = 'Physics FIA GT4 Aerodynamic Spec'
    elif grp == 'Gr.B':
        span_f, span_r = (100, 150), (150, 250)
        base_f, base_r = 120, 180
        preset = 'Physics Rally Aerodynamic Spec'
    elif is_oval:
        span_f, span_r = (50, 150), (100, 300)
        base_f, base_r = 60, 90
        preset = 'Low Drag Oval Spec'
    elif wf >= 0.55:
        span_f, span_r = (0, 100), (50, 200)
        base_f, base_r = 95, 105
        preset = 'Anti-Understeer Front-Biased Road Aero'
    else:
        span_f, span_r = (50, 150), (100, 300)
        base_f, base_r = 75, 110
        preset = 'Balanced Road Aero'

    # 3. Dynamic Scaling via Frontal Area & Track Demand
    df_f = round(base_f * k_area * (k_demand if not is_oval else 1.0))
    df_r = round(base_r * k_area * (k_demand if not is_oval else 1.0))

    # 4. Center-of-Pressure (CP) Trim
    if wf >= 0.55 and not is_oval:
        df_f = round(df_f * 1.05)
        df_r = round(df_r * 0.95)
    elif wf <= 0.44 and not is_oval:
        df_r = round(df_r * 1.05)

    df_f = max(span_f[0], min(span_f[1], df_f))
    df_r = max(span_r[0], min(span_r[1], df_r))

    return {
        'front': df_f,
        'rear': df_r,
        'range_f': f'{span_f[0]}-{span_f[1]}',
        'range_r': f'{span_r[0]}-{span_r[1]}',
        'preset': preset
    }

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
    """
    Simulate outside-front suspension stroke compression under high-speed trail-braking:
    Combines Aerodynamic Heave (v^2) + Longitudinal Braking Pitch Dive (ax) + Lateral Turn-in Roll (ay).
    Detects bump-stop bottoming, fender-arch clipping, and dynamic rake reversal at velocity v.
    """
    kw_f = calculate_wheel_rate(fn_front_hz, corner_front_kg)
    kw_r = calculate_wheel_rate(fn_rear_hz, corner_rear_kg)

    dz_aero_f = calculate_aerodynamic_heave(df_front, speed_kmh, kw_f)
    dz_aero_r = calculate_aerodynamic_heave(df_rear, speed_kmh, kw_r)

    dz_pitch_f = calculate_braking_pitch_dive(mass_kg, mu, hcg_m, wheelbase_m, kw_f)

    lltd_f = float(arb_front) / max(1.0, float(arb_front + arb_rear))
    dz_roll_f = calculate_cornering_roll_deflection(
        mass_kg, mu, hcg_m, track_width_m, lltd_f, arb_front, kw_f
    )

    dz_tot_f = dz_aero_f + dz_pitch_f + dz_roll_f

    stroke_floor = STROKE_CLEARANCE_FLOOR_MM['widebody'] if is_widebody else STROKE_CLEARANCE_FLOOR_MM['standard']
    z_avail_f = float(rh_front_mm - height_min_front_mm) + stroke_floor
    dyn_clearance_f = z_avail_f - dz_tot_f

    dyn_rake = float(rh_rear_mm - dz_aero_r) - float(rh_front_mm - dz_aero_f)

    bottoming = (dz_tot_f >= z_avail_f)
    bump_rh = max(0, math.ceil(dz_tot_f - z_avail_f + 2.0)) if bottoming else 0

    return {
        'speed_kmh': round(speed_kmh, 1),
        'aero_compression_mm': {'front': round(dz_aero_f, 1), 'rear': round(dz_aero_r, 1)},
        'pitch_compression_front_mm': round(dz_pitch_f, 1),
        'roll_compression_front_mm': round(dz_roll_f, 1),
        'total_outside_front_compression_mm': round(dz_tot_f, 1),
        'dynamic_outside_front_clearance_mm': round(dyn_clearance_f, 1),
        'dynamic_rake_mm': round(dyn_rake, 1),
        'bottoming_or_fender_hit': bottoming,
        'recommended_front_rh_bump_mm': bump_rh
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
    """
    Solve closed-form physical suspension equilibrium:
    Calculates optimal static ride heights (h_f, h_r) and dynamic clearances satisfying:
    1. Pitch dive + corner roll + aero heave <= Available stroke margin under trail-braking.
    2. Rear squat under peak engine acceleration does not cause negative aerodynamic rake.
    """
    grp = normalize_group(group)
    if height_front_range and height_rear_range:
        h_min_f, h_max_f = height_front_range
        h_min_r, h_max_r = height_rear_range
    elif height_range:
        h_min_f, h_max_f = height_range
        h_min_r, h_max_r = height_range
    elif grp in ['Gr.X', 'Gr.1']:
        h_min_f, h_max_f = (45, 80)
        h_min_r, h_max_r = (50, 85)
    elif grp in ['Gr.2', 'Gr.3']:
        h_min_f, h_max_f = (55, 95)
        h_min_r, h_max_r = (60, 100)
    elif grp == 'Gr.4':
        h_min_f, h_max_f = (75, 120)
        h_min_r, h_max_r = (80, 125)
    elif is_dirt or grp == 'Gr.B':
        h_min_f, h_max_f = (130, 175)
        h_min_r, h_max_r = (135, 180)
    elif body_style in ['SUV', 'Pickup']:
        h_min_f, h_max_f = (120, 170)
        h_min_r, h_max_r = (125, 175)
    else:
        h_min_f, h_max_f = (90, 140)
        h_min_r, h_max_r = (95, 145)

    tot_s, c_f, c_r = calculate_sprung_mass(mass_kg, front_ratio, group)
    kw_f = calculate_wheel_rate(fn_f, c_f)
    kw_r = calculate_wheel_rate(fn_r, c_r)

    squat_res = calculate_acceleration_squat_dive(
        torque_nm=torque_nm, power_hp=power_hp, mass_kg=mass_kg,
        drivetrain=drivetrain, hcg_m=hcg_m, wheelbase_m=wheelbase_m,
        wheel_rate_f=kw_f, wheel_rate_r=kw_r
    )
    dz_squat_r = squat_res['squat_rear_mm']
    dz_lift_f = squat_res['lift_front_mm']

    lltd_f = float(arb_f) / max(1.0, float(arb_f + arb_r))
    trail_res = calculate_combined_trail_braking_load(
        mass_kg=mass_kg, mu=mu, hcg_m=hcg_m, wheelbase_m=wheelbase_m,
        track_width_m=track_width_m, lltd_f=lltd_f, arb_f=arb_f,
        wheel_rate_f=kw_f, speed_kmh=speed_kmh, df_front=float(df_f)
    )
    dz_trail_f = trail_res['total_deflection_mm']

    dz_aero_r = calculate_aerodynamic_heave(float(df_r), speed_kmh, kw_r)

    stroke_floor = STROKE_CLEARANCE_FLOOR_MM['widebody'] if is_widebody else STROKE_CLEARANCE_FLOOR_MM['standard']
    bump_margin = 14.0 if bumpiness == 'high' else (12.0 if bumpiness == 'medium' else 10.0)

    h_f_target = h_min_f + max(0.0, dz_trail_f + bump_margin - stroke_floor)
    opt_h_f = min(h_max_f, max(h_min_f, int(round(h_f_target))))

    z_avail_f = float(opt_h_f - h_min_f) + stroke_floor
    dyn_clearance_f = z_avail_f - dz_trail_f
    trail_feasible = (dyn_clearance_f >= 10.0)

    base_rake = 6 if front_ratio <= 0.50 else min(14, round(6.0 + 16.0 * (front_ratio - 0.50)))
    rake_needed = max(float(base_rake), round(dz_squat_r * 0.75 + dz_lift_f * 0.50 + 4.0))
    opt_h_r = min(h_max_r, max(h_min_r, int(round(opt_h_f + rake_needed))))

    dyn_rake_accel = (opt_h_r - dz_squat_r) - (opt_h_f + dz_lift_f)
    dyn_rake_brake = (opt_h_r - dz_aero_r) - (opt_h_f - dz_trail_f)

    fn_boost = round(max(0.0, (12.0 - dyn_clearance_f) * 0.04), 2) if not trail_feasible else 0.0

    return {
        'optimal_rh_front': int(opt_h_f),
        'optimal_rh_rear': int(opt_h_r),
        'trail_braking_feasible': trail_feasible,
        'min_dynamic_clearance_mm': round(dyn_clearance_f, 1),
        'total_trail_compression_front_mm': round(dz_trail_f, 1),
        'acceleration_squat_rear_mm': round(dz_squat_r, 1),
        'acceleration_lift_front_mm': round(dz_lift_f, 1),
        'dynamic_rake_accel_mm': round(dyn_rake_accel, 1),
        'dynamic_rake_brake_mm': round(dyn_rake_brake, 1),
        'recommended_front_fn_boost_hz': fn_boost
    }
