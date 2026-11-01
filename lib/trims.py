#!/usr/bin/env python3
"""
GT7 Closed-Loop Trims & Handling Diagnostics Module
Applies handling symptom adjustments and in-game stability index corrections.
"""

from typing import Dict, Tuple, Optional, Any, List
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from gt7_constants import SLIDER_BOUNDS
from lib.quick_trims import build_quick_trims


def _apply_stability_trims(
    p: Dict[str, Any],
    stability: Tuple[float, float],
    drivetrain: str
) -> None:
    """Apply stability index corrections for loose low-speed or twitchy high-speed handling."""
    low_s, high_s = stability
    if low_s is not None and low_s <= -0.25:
        p['anti_roll_bar']['front'] = max(1, p['anti_roll_bar']['front'] - 1)
        p['anti_roll_bar']['rear'] = min(10, p['anti_roll_bar']['rear'] + 1)
        for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
            lsd['brake'] = max(5, lsd['brake'] - 4)
        if drivetrain == 'FR':
            max_shift = 1 if p.get('is_controller') else 5
            p['brake_bias'] = min(max_shift, p['brake_bias'] + 1)
    if high_s is not None and high_s >= 0.20:
        p['damping_expansion_pct']['rear'] = min(80, p['damping_expansion_pct']['rear'] + 4)
        for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
            lsd['brake'] = min(65, lsd['brake'] + 6)
        p['brake_bias'] = max(-5, p['brake_bias'] - 1)


def _apply_corner_symptom(p: Dict[str, Any], s: str, drivetrain: str) -> None:
    """Apply cornering entry push or exit snap adjustments."""
    if s == 'entry_push':
        p['anti_roll_bar']['front'] = max(1, p['anti_roll_bar']['front'] - 1)
        p['anti_roll_bar']['rear'] = min(10, p['anti_roll_bar']['rear'] + 1)
        for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
            lsd['brake'] = max(5, lsd['brake'] - 4)
        p['ride_height_mm']['rear'] += 3
        if drivetrain == 'FR':
            max_shift = 1 if p.get('is_controller') else 5
            p['brake_bias'] = min(max_shift, p['brake_bias'] + 1)
    elif s == 'exit_snap':
        for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
            lsd['accel'] = max(5, lsd['accel'] - 4)
        p['damping_compression_pct']['rear'] = min(80, p['damping_compression_pct']['rear'] + 2)
        p['anti_roll_bar']['rear'] = max(1, p['anti_roll_bar']['rear'] - 1)


def _apply_bump_symptom(p: Dict[str, Any], s: str) -> None:
    """Apply suspension bottoming or curb hopping adjustments."""
    if s == 'bottoming':
        p['ride_height_mm']['front'] += 5
        p['ride_height_mm']['rear'] += 5
        p['damping_compression_pct']['front'] = min(80, p['damping_compression_pct']['front'] + 2)
        p['damping_compression_pct']['rear'] = min(80, p['damping_compression_pct']['rear'] + 2)
    elif s == 'curb_hop':
        p['anti_roll_bar']['front'] = max(1, p['anti_roll_bar']['front'] - 1)
        p['anti_roll_bar']['rear'] = max(1, p['anti_roll_bar']['rear'] - 1)
        p['damping_compression_pct']['front'] = max(20, p['damping_compression_pct']['front'] - 2)
        p['damping_compression_pct']['rear'] = max(20, p['damping_compression_pct']['rear'] - 2)
        p['ride_height_mm']['front'] += 3
        p['ride_height_mm']['rear'] += 3


def _trim_front_tire_wear(p: Dict[str, Any], drivetrain: str) -> None:
    """Rebalance front-axle tire wear: soften front roll stiffness and preserve front brake load."""
    p['anti_roll_bar']['front'] = max(1, p['anti_roll_bar']['front'] - 1)
    p['anti_roll_bar']['rear'] = min(10, p['anti_roll_bar']['rear'] + 2)
    if p.get('downforce') and isinstance(p['downforce'], dict) and p['downforce'].get('front'):
        p['downforce']['front'] = max(10, int(round(p['downforce']['front'] * 0.92)))
    p['camber_deg']['front'] = max(-1.4, round(p['camber_deg']['front'] + 0.5, 1))
    p['toe_angle']['front'] = '0.00'
    if drivetrain == 'FR':
        p['brake_bias'] = min(2, p['brake_bias'] + 1)
    elif drivetrain != 'FF':
        p['brake_bias'] = min(0, p['brake_bias'] + 1)
    for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
        lsd['brake'] = max(20, lsd['brake'] - 4)


def _trim_rear_tire_wear(p: Dict[str, Any], drivetrain: str) -> None:
    """Rebalance rear-axle tire wear: soften rear acceleration locking and shift braking load forward."""
    for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
        lsd['accel'] = max(16, min(24, lsd['accel'] - 4))
    p['camber_deg']['rear'] = max(-1.0, round(p['camber_deg']['rear'] + 0.4, 1))
    p['anti_roll_bar']['front'] = min(10, p['anti_roll_bar']['front'] + 1)
    p['anti_roll_bar']['rear'] = max(1, p['anti_roll_bar']['rear'] - 1)
    p['damping_compression_pct']['rear'] = min(80, p['damping_compression_pct']['rear'] + 2)
    if drivetrain in ['FR', 'MR', 'RR']:
        p['brake_bias'] = max(-2, p['brake_bias'] - 1)


def _apply_tire_wear_symptom(p: Dict[str, Any], s: str, drivetrain: str) -> None:
    """Apply severe tire wear rebalancing adjustments."""
    if s in ['front_tire_wear', 'front_wear', 'tire_wear_front']:
        _trim_front_tire_wear(p, drivetrain)
    elif s in ['rear_tire_wear', 'rear_wear', 'tire_wear_rear']:
        _trim_rear_tire_wear(p, drivetrain)


def _clamp_suspension_sliders(p: Dict[str, Any]) -> None:
    """Clamp ARB and dampers within legal GT7 limits."""
    arb_min, arb_max = SLIDER_BOUNDS['anti_roll_bar']
    comp_min, comp_max = SLIDER_BOUNDS['damping_compression']
    exp_min, exp_max = SLIDER_BOUNDS['damping_expansion']

    p['anti_roll_bar']['front'] = max(arb_min, min(arb_max, p['anti_roll_bar']['front']))
    p['anti_roll_bar']['rear'] = max(arb_min, min(arb_max, p['anti_roll_bar']['rear']))
    p['damping_compression_pct']['front'] = max(comp_min, min(comp_max, p['damping_compression_pct']['front']))
    p['damping_compression_pct']['rear'] = max(comp_min, min(comp_max, p['damping_compression_pct']['rear']))
    p['damping_expansion_pct']['front'] = max(exp_min, min(exp_max, p['damping_expansion_pct']['front']))
    p['damping_expansion_pct']['rear'] = max(exp_min, min(exp_max, p['damping_expansion_pct']['rear']))


def _clamp_ride_height_range(p: Dict[str, Any]) -> None:
    """Clamp ride height within explicit range string if present."""
    rh = p.get('ride_height_mm', {})
    if 'range' not in rh:
        return
    try:
        parts = [int(x) for x in str(rh['range']).split('-')]
        if len(parts) == 2:
            rh['front'] = max(parts[0], min(parts[1], rh['front']))
            rh['rear'] = max(parts[0], min(parts[1], rh['rear']))
    except Exception:
        pass


def _clamp_drivetrain_and_brakes(p: Dict[str, Any], drivetrain: str, group: str) -> None:
    """Clamp LSD, brake bias, and ride height range bounds."""
    for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
        lsd['init'] = max(SLIDER_BOUNDS['lsd_initial_torque'][0], min(SLIDER_BOUNDS['lsd_initial_torque'][1], lsd['init']))
        lsd['accel'] = max(SLIDER_BOUNDS['lsd_accel_sensitivity'][0], min(SLIDER_BOUNDS['lsd_accel_sensitivity'][1], lsd['accel']))
        lsd['brake'] = max(SLIDER_BOUNDS['lsd_braking_sensitivity'][0], min(SLIDER_BOUNDS['lsd_braking_sensitivity'][1], lsd['brake']))

    is_ctrl = p.get('is_controller', False)
    if drivetrain in ['FF', 'MR', 'RR', 'AWD', '4WD', '4x4']:
        max_bb = 0
    elif is_ctrl:
        max_bb = 1
    else:
        max_bb = 5
    p['brake_bias'] = max(-5, min(max_bb, p['brake_bias']))
    _clamp_ride_height_range(p)

    if group == 'Gr.4' and drivetrain in ['AWD', '4WD', '4x4']:
        p['awd_torque_split'] = 'Fixed (Homologation / ปรับไม่ได้ใน Gr.4)'


def _apply_symptoms_list(p: Dict[str, Any], symptoms: Optional[List[str]], drivetrain: str) -> None:
    """Iterate and apply handling, bump, and wear symptoms."""
    for sym in (symptoms or []):
        s = sym.lower()
        _apply_corner_symptom(p, s, drivetrain)
        _apply_bump_symptom(p, s)
        _apply_tire_wear_symptom(p, s, drivetrain)


def apply_closed_loop_trim(
    parameters: Dict[str, Any], stability: Optional[Tuple[float, float]] = None,
    symptoms: Optional[List[str]] = None, drivetrain: str = 'FR',
    group: str = 'Road Car', is_controller: Optional[bool] = None
) -> Dict[str, Any]:
    """Apply closed-loop trim adjustments to suspension and chassis parameters."""
    p = parameters
    if is_controller is not None:
        p['is_controller'] = is_controller
    if stability:
        _apply_stability_trims(p, stability, drivetrain)
    _apply_symptoms_list(p, symptoms, drivetrain)
    _clamp_suspension_sliders(p)
    _clamp_drivetrain_and_brakes(p, drivetrain, group)
    return p
