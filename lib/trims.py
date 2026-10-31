#!/usr/bin/env python3
"""
GT7 Closed-Loop Trims & Quick-Trims Delta Module
Applies handling symptom adjustments and in-game stability index corrections,
and constructs Section 2.F proactive dual setup variations (Tire-Saver and Max-Stability).
"""

from typing import Dict, Tuple, Optional, Any, List
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from gt7_constants import SLIDER_BOUNDS


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
        if drivetrain != 'FF':
            p['brake_bias'] = max(-5, p['brake_bias'] - 1)
    if high_s is not None and high_s >= 0.20:
        p['damping_expansion_pct']['rear'] = min(80, p['damping_expansion_pct']['rear'] + 4)
        for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
            lsd['brake'] = min(65, lsd['brake'] + 6)


def _apply_corner_symptom(p: Dict[str, Any], s: str, drivetrain: str) -> None:
    """Apply cornering entry push or exit snap adjustments."""
    if s == 'entry_push':
        p['anti_roll_bar']['front'] = max(1, p['anti_roll_bar']['front'] - 1)
        p['anti_roll_bar']['rear'] = min(10, p['anti_roll_bar']['rear'] + 1)
        for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
            lsd['brake'] = max(5, lsd['brake'] - 4)
        p['ride_height_mm']['rear'] += 3
        if drivetrain != 'FF':
            p['brake_bias'] = max(-5, p['brake_bias'] - 1)
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


def _apply_tire_wear_symptom(p: Dict[str, Any], s: str, drivetrain: str) -> None:
    """Apply severe tire wear rebalancing adjustments."""
    if s in ['front_tire_wear', 'front_wear', 'tire_wear_front']:
        p['anti_roll_bar']['front'] = max(1, p['anti_roll_bar']['front'] - 1)
        p['anti_roll_bar']['rear'] = min(10, p['anti_roll_bar']['rear'] + 2)
        if p.get('downforce') and isinstance(p['downforce'], dict) and p['downforce'].get('front'):
            p['downforce']['front'] = max(10, int(round(p['downforce']['front'] * 0.92)))
        p['camber_deg']['front'] = max(-1.4, round(p['camber_deg']['front'] + 0.5, 1))
        p['toe_angle']['front'] = '0.00'
        if drivetrain != 'FF':
            p['brake_bias'] = max(-3, p['brake_bias'] - 1)
        for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
            lsd['brake'] = max(20, lsd['brake'] - 4)
    elif s in ['rear_tire_wear', 'rear_wear', 'tire_wear_rear']:
        for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
            lsd['accel'] = max(16, min(24, lsd['accel'] - 4))
        p['camber_deg']['rear'] = max(-1.0, round(p['camber_deg']['rear'] + 0.4, 1))
        p['anti_roll_bar']['front'] = min(10, p['anti_roll_bar']['front'] + 1)
        p['anti_roll_bar']['rear'] = max(1, p['anti_roll_bar']['rear'] - 1)
        p['damping_compression_pct']['rear'] = min(80, p['damping_compression_pct']['rear'] + 2)


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

    bb_bounds = SLIDER_BOUNDS['brake_bias_ff'] if drivetrain == 'FF' else SLIDER_BOUNDS['brake_bias_default']
    p['brake_bias'] = max(bb_bounds[0], min(bb_bounds[1], p['brake_bias']))
    _clamp_ride_height_range(p)

    if group == 'Gr.4' and drivetrain in ['AWD', '4WD']:
        p['awd_torque_split'] = 'Fixed (Homologation / ปรับไม่ได้ใน Gr.4)'


def apply_closed_loop_trim(
    parameters: Dict[str, Any],
    stability: Optional[Tuple[float, float]] = None,
    symptoms: Optional[List[str]] = None,
    drivetrain: str = 'FR',
    group: str = 'Road Car'
) -> Dict[str, Any]:
    """Apply closed-loop trim adjustments to suspension and chassis parameters."""
    p = parameters
    if stability:
        _apply_stability_trims(p, stability, drivetrain)
    for sym in (symptoms or []):
        s = sym.lower()
        _apply_corner_symptom(p, s, drivetrain)
        _apply_bump_symptom(p, s)
        _apply_tire_wear_symptom(p, s, drivetrain)
    _clamp_suspension_sliders(p)
    _clamp_drivetrain_and_brakes(p, drivetrain, group)
    return p


def _build_tire_saver_spec(p: Dict[str, Any], drivetrain: str, is_endurance: bool) -> Dict[str, Any]:
    """Build tire-saver quick-trim specification."""
    nf = p.get('natural_frequency_hz', {})
    fn_f, fn_r = nf.get('front', 2.50), nf.get('rear', 2.70)
    lsd_r = p.get('lsd_rear') or {'init': 8, 'accel': 20, 'brake': 50}

    target_fn_f = round(max(1.40, fn_f - (0.0 if is_endurance else 0.20)), 2)
    target_fn_r = round(max(1.40, fn_r - (0.0 if is_endurance else 0.20)), 2)
    toe_str = '0.00° / In 0.12°' if drivetrain in ['MR', 'RR'] else '0.00° / In 0.08°'
    accel_val = max(14, min(20, lsd_r['accel'] - (0 if is_endurance else 4)))

    cam_f = p.get('camber_deg', {}).get('front', -2.8)
    cam_r = p.get('camber_deg', {}).get('rear', -1.5)
    cam_str = f"{min(-1.4, round(cam_f + 0.5, 1)):.1f}° / {min(-0.8, round(cam_r + 0.3, 1)):.1f}°"
    return {
        'natural_frequency_hz': f"{target_fn_f:.2f} / {target_fn_r:.2f} Hz",
        'negative_camber': cam_str,
        'toe_angle': toe_str,
        'lsd_accel': accel_val,
        'description': 'Softer spring rate, reduced camber & zero-scrub toe to eliminate tire overheating on long stints'
    }


def _build_max_stability_spec(p: Dict[str, Any], drivetrain: str) -> Dict[str, Any]:
    """Build max stability quick-trim specification."""
    arb = p.get('anti_roll_bar', {'front': 5, 'rear': 5})
    exp = p.get('damping_expansion_pct', {'front': 48, 'rear': 52})
    lsd_r = p.get('lsd_rear') or {'init': 8, 'accel': 20, 'brake': 50}
    bias = p.get('brake_bias', 0)

    stab_arb_f = min(8, arb['front'] + 1)
    stab_arb_r = max(3, arb['rear'] - 1)
    stab_exp_r = min(80, exp['rear'] + 4)
    stab_toe_r = 'In 0.20°' if drivetrain in ['MR', 'RR'] else 'In 0.18°'
    stab_lsd_brake = min(65, lsd_r['brake'] + 8)
    stab_bias = min(2, bias + 1) if drivetrain == 'FF' else min(1, bias + 1)

    return {
        'anti_roll_bar': f"{stab_arb_f} / {stab_arb_r}",
        'damping_expansion_rear': f"{stab_exp_r}%",
        'rear_toe_in': stab_toe_r,
        'lsd_braking_sens': stab_lsd_brake,
        'brake_bias': stab_bias,
        'description': 'Anchors rear axle under braking, stiffens rear rebound, and dampens yaw to prevent snap-oversteer'
    }


def build_quick_trims(
    parameters: Dict[str, Any],
    drivetrain: str = 'FR',
    is_endurance: bool = False
) -> Dict[str, Dict[str, Any]]:
    """Construct Section 2.F proactive quick-trim delta table."""
    return {
        'tire_saver': _build_tire_saver_spec(parameters, drivetrain, is_endurance),
        'max_stability': _build_max_stability_spec(parameters, drivetrain)
    }
