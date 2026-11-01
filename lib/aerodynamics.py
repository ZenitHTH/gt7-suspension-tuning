#!/usr/bin/env python3
"""
GT7 Aerodynamics & Downforce Module
Calculates front and rear downforce matching Center of Pressure (CP)
to vehicle mass distribution, frontal area, and track downforce demand.
"""

import math
from typing import Dict, Tuple, Optional, Any
from lib.formulas import normalize_group


def _get_endurance_aero_ratios(grp: str, wf: float) -> Tuple[float, float, str]:
    """Determine endurance CP balancing ratios."""
    if grp == 'Gr.X':
        return 0.45, 0.55, 'Tire-Saver Center-of-Pressure (CP) Balanced'
    r_rear = 0.70 if wf <= 0.46 else 0.60
    r_front = 0.40 if wf <= 0.46 else 0.45
    return r_front, r_rear, 'Tire-Saver Center-of-Pressure (CP) Balanced'


def _get_ranged_aero_ratios(
    span_f: int,
    f_min: int,
    r_min: int,
    wf: float,
    demand: str,
    grp: str,
    is_oval: bool,
    is_endurance: bool
) -> Tuple[float, float, str]:
    """Determine downforce range interpolation ratios and preset label."""
    if is_oval:
        return 0.15, 0.15, 'Low Drag Oval / Super Speedway Spec'
    if span_f == 0 and f_min > 0 and r_min > f_min:
        return 1.0, 0.0, 'Fixed Front Floor Balance (Anti-High-Speed-Push)'
    if is_endurance:
        return _get_endurance_aero_ratios(grp, wf)
    if wf >= 0.55:
        r_rear = 0.30 if demand == 'low' else (0.45 if demand == 'high' else 0.35)
        return 0.80, r_rear, 'Anti-Understeer Front-Biased'
    ratios = {'low': (0.40, 0.40), 'medium': (0.60, 0.60), 'high': (0.80, 0.75)}.get(demand, (0.60, 0.60))
    return ratios[0], ratios[1], f'Physics First-Principles Optimized ({demand.capitalize()} Downforce)'


def _calculate_ranged_downforce(
    df_front_range: Tuple[int, int],
    df_rear_range: Tuple[int, int],
    wf: float,
    demand: str,
    grp: str,
    is_oval: bool,
    is_endurance: bool
) -> Dict[str, Any]:
    """Calculate downforce when user or car record supplies slider min/max bounds."""
    f_min, f_max = df_front_range
    r_min, r_max = df_rear_range
    span_f = f_max - f_min
    span_r = r_max - r_min

    ratio_f, ratio_r, preset = _get_ranged_aero_ratios(
        span_f, f_min, r_min, wf, demand, grp, is_oval, is_endurance
    )
    front_val = round(f_min + span_f * ratio_f)
    rear_val = round(r_min + span_r * ratio_r)

    # Invariant: On road circuits, front downforce must not exceed rear downforce
    # unless front aero is locked by fixed factory aero.
    if not is_oval and front_val > rear_val and span_f > 0:
        front_val = max(f_min, min(f_max, rear_val))

    return {
        'front': front_val,
        'rear': rear_val,
        'range_f': f'{f_min}-{f_max}',
        'range_r': f'{r_min}-{r_max}',
        'preset': preset
    }


def _estimate_frontal_area_scale(
    width_m: float,
    height_m: float,
    body_style: str,
    grp: str
) -> float:
    """Estimate dynamic frontal area scaling factor k_area from dimensions and body style."""
    k_body = 0.88 if body_style in ['SUV', 'Pickup', 'Van'] else (
        0.78 if grp in ['Gr.X', 'Gr.1'] else (
            0.82 if grp in ['Gr.2', 'Gr.3'] else 0.84
        )
    )
    a_frontal = (width_m or 1.80) * (height_m or 1.30) * k_body
    return max(0.85, min(1.20, math.sqrt(a_frontal / 2.0)))


def _get_archetype_aero_baselines(
    grp: str,
    is_oval: bool,
    is_endurance: bool,
    wf: float
) -> Tuple[Tuple[int, int], Tuple[int, int], int, int, str]:
    """Retrieve archetype downforce spans, base points, and preset descriptions."""
    if grp == 'Gr.X':
        return (800, 1200), (1200, 1600), (980 if is_endurance else 1040), (1420 if is_endurance else 1440), 'Physics Prototype High Downforce'
    if grp == 'Gr.1':
        return (700, 1000), (1100, 1600), 850, 1350, 'Physics Prototype Le Mans Downforce'
    if grp == 'Gr.2':
        return (500, 700), (800, 1100), 620, 950, 'Physics Super GT / DTM Aerodynamic Balance'
    if grp == 'Gr.3':
        return (350, 450), (500, 700), 430, 630, 'Physics FIA GT3 Aerodynamic Balance'
    if grp == 'Gr.4':
        return (80, 180), (150, 320), 125, 220, 'Physics FIA GT4 Aerodynamic Spec'
    if grp == 'Gr.B':
        return (100, 150), (150, 250), 120, 180, 'Physics Rally Aerodynamic Spec'
    if is_oval:
        return (50, 150), (100, 300), 60, 90, 'Low Drag Oval Spec'
    if wf >= 0.55:
        return (0, 100), (50, 200), 95, 105, 'Anti-Understeer Front-Biased Road Aero'
    return (50, 150), (100, 300), 75, 110, 'Balanced Road Aero'


def _apply_cp_trim(df_f: int, df_r: int, wf: float, is_oval: bool) -> Tuple[int, int]:
    """Apply Center-of-Pressure (CP) bias adjustments for weight distribution."""
    if is_oval:
        return df_f, df_r
    if wf >= 0.55:
        return round(df_f * 1.05), round(df_r * 0.95)
    if wf <= 0.44:
        return df_f, round(df_r * 1.05)
    return df_f, df_r


def _calculate_first_principles_downforce(
    grp: str,
    width_m: float,
    height_m: float,
    body_style: str,
    demand: str,
    is_oval: bool,
    is_endurance: bool,
    wf: float
) -> Dict[str, Any]:
    """Compute first-principles downforce when no explicit slider bounds exist."""
    k_area = _estimate_frontal_area_scale(width_m, height_m, body_style, grp)
    k_demand = 0.60 if is_oval else {'low': 0.88, 'medium': 1.00, 'high': 1.15}.get(demand, 1.00)

    span_f, span_r, base_f, base_r, preset = _get_archetype_aero_baselines(grp, is_oval, is_endurance, wf)
    demand_mult = 1.0 if is_oval else k_demand
    df_f = round(base_f * k_area * demand_mult)
    df_r = round(base_r * k_area * demand_mult)

    df_f, df_r = _apply_cp_trim(df_f, df_r, wf, is_oval)
    df_f = max(span_f[0], min(span_f[1], df_f))
    df_r = max(span_r[0], min(span_r[1], df_r))

    return {
        'front': df_f, 'rear': df_r,
        'range_f': f'{span_f[0]}-{span_f[1]}', 'range_r': f'{span_r[0]}-{span_r[1]}',
        'preset': preset
    }


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
    """Calculate front and rear downforce matching Center of Pressure (CP) to vehicle specs."""
    demand = (downforce_demand or 'medium').lower()
    grp = normalize_group(group)

    if df_front_range and df_rear_range:
        return _calculate_ranged_downforce(
            df_front_range, df_rear_range, wf, demand, grp, is_oval, is_endurance
        )

    return _calculate_first_principles_downforce(
        grp, width_m, height_m, body_style, demand, is_oval, is_endurance, wf
    )
