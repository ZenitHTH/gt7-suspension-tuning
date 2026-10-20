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

def apply_closed_loop_trim(
    parameters: Dict[str, Any],
    stability: Optional[Tuple[float, float]] = None,
    symptoms: Optional[List[str]] = None,
    drivetrain: str = 'FR',
    group: str = 'Road Car'
) -> Dict[str, Any]:
    """
    Apply closed-loop trim adjustments to suspension and chassis parameters
    based on in-game Stability Index (-1.00 to +1.00) and reported handling symptoms.
    Clamps all modified parameters strictly within GT7 in-game legal bounds.
    """
    p = parameters

    # 1. Stability Index Trims
    if stability:
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

    # 2. Symptom Trims
    for sym in (symptoms or []):
        s = sym.lower()
        if s == 'entry_push':
            p['anti_roll_bar']['front'] = max(1, p['anti_roll_bar']['front'] - 1)
            p['anti_roll_bar']['rear'] = min(10, p['anti_roll_bar']['rear'] + 1)
            for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
                lsd['brake'] = max(5, lsd['brake'] - 4)
            p['ride_height_mm']['rear'] = p['ride_height_mm']['rear'] + 3
            if drivetrain != 'FF':
                p['brake_bias'] = max(-5, p['brake_bias'] - 1)
        elif s == 'exit_snap':
            for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
                lsd['accel'] = max(5, lsd['accel'] - 4)
            p['damping_compression_pct']['rear'] = min(80, p['damping_compression_pct']['rear'] + 2)
            p['anti_roll_bar']['rear'] = max(1, p['anti_roll_bar']['rear'] - 1)
        elif s == 'bottoming':
            p['ride_height_mm']['front'] = p['ride_height_mm']['front'] + 5
            p['ride_height_mm']['rear'] = p['ride_height_mm']['rear'] + 5
            p['damping_compression_pct']['front'] = min(80, p['damping_compression_pct']['front'] + 2)
            p['damping_compression_pct']['rear'] = min(80, p['damping_compression_pct']['rear'] + 2)
        elif s == 'curb_hop':
            p['anti_roll_bar']['front'] = max(1, p['anti_roll_bar']['front'] - 1)
            p['anti_roll_bar']['rear'] = max(1, p['anti_roll_bar']['rear'] - 1)
            p['damping_compression_pct']['front'] = max(20, p['damping_compression_pct']['front'] - 2)
            p['damping_compression_pct']['rear'] = max(20, p['damping_compression_pct']['rear'] - 2)
            p['ride_height_mm']['front'] = p['ride_height_mm']['front'] + 3
            p['ride_height_mm']['rear'] = p['ride_height_mm']['rear'] + 3

    # 3. Final Boundary Clamps & Homologation Invariants
    arb_min, arb_max = SLIDER_BOUNDS['anti_roll_bar']
    comp_min, comp_max = SLIDER_BOUNDS['damping_compression']
    exp_min, exp_max = SLIDER_BOUNDS['damping_expansion']
    lsd_init_min, lsd_init_max = SLIDER_BOUNDS['lsd_initial_torque']
    lsd_accel_min, lsd_accel_max = SLIDER_BOUNDS['lsd_accel_sensitivity']
    lsd_brake_min, lsd_brake_max = SLIDER_BOUNDS['lsd_braking_sensitivity']

    p['anti_roll_bar']['front'] = max(arb_min, min(arb_max, p['anti_roll_bar']['front']))
    p['anti_roll_bar']['rear'] = max(arb_min, min(arb_max, p['anti_roll_bar']['rear']))
    p['damping_compression_pct']['front'] = max(comp_min, min(comp_max, p['damping_compression_pct']['front']))
    p['damping_compression_pct']['rear'] = max(comp_min, min(comp_max, p['damping_compression_pct']['rear']))
    p['damping_expansion_pct']['front'] = max(exp_min, min(exp_max, p['damping_expansion_pct']['front']))
    p['damping_expansion_pct']['rear'] = max(exp_min, min(exp_max, p['damping_expansion_pct']['rear']))

    for lsd in [p[k] for k in ('lsd_rear', 'lsd_front') if k in p and isinstance(p[k], dict)]:
        lsd['init'] = max(lsd_init_min, min(lsd_init_max, lsd['init']))
        lsd['accel'] = max(lsd_accel_min, min(lsd_accel_max, lsd['accel']))
        lsd['brake'] = max(lsd_brake_min, min(lsd_brake_max, lsd['brake']))

    if drivetrain == 'FF':
        bb_min, bb_max = SLIDER_BOUNDS['brake_bias_ff']
        p['brake_bias'] = max(bb_min, min(bb_max, p['brake_bias']))
    else:
        bb_min, bb_max = SLIDER_BOUNDS['brake_bias_default']
        p['brake_bias'] = max(bb_min, min(bb_max, p['brake_bias']))

    if 'range' in p.get('ride_height_mm', {}):
        try:
            parts = [int(x) for x in str(p['ride_height_mm']['range']).split('-')]
            if len(parts) == 2:
                p['ride_height_mm']['front'] = max(parts[0], min(parts[1], p['ride_height_mm']['front']))
                p['ride_height_mm']['rear'] = max(parts[0], min(parts[1], p['ride_height_mm']['rear']))
        except Exception:
            pass

    if group == 'Gr.4' and drivetrain in ['AWD', '4WD']:
        p['awd_torque_split'] = 'Fixed (Homologation / ปรับไม่ได้ใน Gr.4)'

    return p

def build_quick_trims(
    parameters: Dict[str, Any],
    drivetrain: str = 'FR',
    is_endurance: bool = False
) -> Dict[str, Dict[str, Any]]:
    """
    Generate proactive dual Quick-Trims delta specifications (Section 2.F):
    1. Tire-Saver Spec (โหมดถนอมยาง / WTC Endurance)
    2. Max Stability Spec (โหมดเน้นความนิ่ง / Anti-Snap & High-Speed Calm)
    """
    p = parameters
    nf = p.get('natural_frequency_hz', {})
    fn_f = nf.get('front', 2.50)
    fn_r = nf.get('rear', 2.70)
    arb = p.get('anti_roll_bar', {'front': 5, 'rear': 5})
    exp = p.get('damping_expansion_pct', {'front': 48, 'rear': 52})
    lsd_r = p.get('lsd_rear') or {'init': 8, 'accel': 20, 'brake': 50}
    bias = p.get('brake_bias', 0)

    # 1. Tire-Saver Spec
    target_fn_f = round(max(1.40, fn_f - (0.0 if is_endurance else 0.20)), 2)
    target_fn_r = round(max(1.40, fn_r - (0.0 if is_endurance else 0.20)), 2)
    tire_saver_toe = '0.00° / In 0.12°' if drivetrain in ['MR', 'RR'] else '0.00° / In 0.08°'
    tire_saver = {
        'natural_frequency_hz': f"{target_fn_f:.2f} / {target_fn_r:.2f} Hz",
        'negative_camber': '-2.2° / -1.2°',
        'toe_angle': tire_saver_toe,
        'lsd_accel': max(14, min(20, lsd_r['accel'] - (0 if is_endurance else 4))),
        'description': 'Softer spring rate, reduced camber & zero-scrub toe to eliminate tire overheating on long stints'
    }

    # 2. Max Stability Spec
    stab_arb_f = min(8, arb['front'] + 1)
    stab_arb_r = max(3, arb['rear'] - 1)
    stab_exp_r = min(80, exp['rear'] + 4)
    stab_toe_r = 'In 0.20°' if drivetrain in ['MR', 'RR'] else 'In 0.18°'
    stab_lsd_brake = min(65, lsd_r['brake'] + 8)
    stab_bias = min(2, bias + 1) if drivetrain == 'FF' else min(1, bias + 1)
    max_stability = {
        'anti_roll_bar': f"{stab_arb_f} / {stab_arb_r}",
        'damping_expansion_rear': f"{stab_exp_r}%",
        'rear_toe_in': stab_toe_r,
        'lsd_braking_sens': stab_lsd_brake,
        'brake_bias': stab_bias,
        'description': 'Anchors rear axle under braking, stiffens rear rebound, and dampens yaw to prevent snap-oversteer'
    }

    return {
        'tire_saver': tire_saver,
        'max_stability': max_stability
    }
