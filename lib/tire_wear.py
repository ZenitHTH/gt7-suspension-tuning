#!/usr/bin/env python3
"""
GT7 Tire Wear Analysis Module
Evaluates micro-slip work caused by suspension stiffness, wheel alignment scrub, and camber abrasion.
"""

from typing import Any, Dict, Tuple


def parse_alignment_value(val: Any) -> float:
    """Parse numeric or formatted string alignment value (e.g., 'Out 0.10', '-1.5')."""
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


def calculate_stiffness_wear_factor(fn_hz: float, base_fn: float) -> float:
    """Calculate normal load variation wear factor from natural frequency."""
    return (max(1.0, float(fn_hz)) / base_fn) ** 1.35


def calculate_geometry_scrub_factor(camber: float, toe: float, min_camber: float) -> float:
    """Calculate combined tire wear multiplier from toe slip scrub and camber inner abrasion."""
    toe_scrub = 1.0 + 0.35 * abs(toe)
    cam_scrub = 1.0 + 0.04 * max(0.0, abs(camber) - min_camber)
    return toe_scrub * cam_scrub


def _calculate_total_wear_factors(
    fn_hz_f: float,
    fn_hz_r: float,
    c_f: float,
    c_r: float,
    t_f: float,
    t_r: float,
    ptw: float
) -> Tuple[float, float]:
    """Calculate raw front and rear tire wear degradation factors."""
    wear_k_f = calculate_stiffness_wear_factor(fn_hz_f, base_fn=2.10)
    wear_k_r = calculate_stiffness_wear_factor(fn_hz_r, base_fn=2.25)
    scrub_f = calculate_geometry_scrub_factor(c_f, t_f, min_camber=2.0)
    scrub_r = calculate_geometry_scrub_factor(c_r, t_r, min_camber=1.8)
    ptw_factor_r = 1.0 + 0.15 * max(0.0, (ptw - 250.0) / 250.0)
    return (wear_k_f * scrub_f), (wear_k_r * scrub_r * ptw_factor_r)


def calculate_tire_wear_index(
    fn_hz_f: float,
    fn_hz_r: float,
    camber_f: Any,
    camber_r: Any,
    toe_f: Any,
    toe_r: Any,
    ptw: float = 200.0,
    is_endurance: bool = False
) -> Dict[str, float]:
    """Calculate analytical tire wear degradation index for front and rear tires."""
    c_f, c_r = parse_alignment_value(camber_f), parse_alignment_value(camber_r)
    t_f, t_r = parse_alignment_value(toe_f), parse_alignment_value(toe_r)

    total_wear_f, total_wear_r = _calculate_total_wear_factors(
        fn_hz_f, fn_hz_r, c_f, c_r, t_f, t_r, ptw
    )
    if is_endurance:
        total_wear_f **= 1.10
        total_wear_r **= 1.10

    rel_bias = round(total_wear_r / max(0.1, total_wear_f), 2)
    return {
        'front_wear_factor': round(total_wear_f, 2),
        'rear_wear_factor': round(total_wear_r, 2),
        'relative_rear_bias': rel_bias
    }
