#!/usr/bin/env python3
"""
GT7 Natural Frequencies & Anti-Roll Bar Suspension Module
Calculates front and rear natural frequencies (Hz) using Olley flat ride pitch synchronization,
downforce load coupling, and Lateral Load Transfer Distribution (LLTD) for anti-roll bars.
"""

import math
from typing import Tuple, Optional
from lib.formulas import normalize_group

def calculate_natural_frequencies(
    mu: float = 1.25,
    wf: float = 0.50,
    bumpiness: str = 'medium',
    group: str = 'Road Car',
    mass: float = 1350.0,
    is_dirt: bool = False,
    is_endurance: bool = False,
    fn_front_range: Optional[Tuple[float, float]] = None,
    fn_rear_range: Optional[Tuple[float, float]] = None,
    df_front: int = 0,
    df_rear: int = 0
) -> Tuple[float, float, float]:
    """
    Calculate front and rear natural frequencies (Hz) using Flat Ride synchronization.
    Flat ride principle: rear frequency oscillates ~5-12% faster than front to turn
    pitching over road undulations into a synchronized flat heave.
    Scales dynamically with vehicle mass, aerodynamic downforce load, and supports user-provided slider ranges.
    """
    grp = normalize_group(group)
    aero_boost_f = 0.0 if is_dirt else min(0.35, max(0.0, ((df_front or 0) - 100) * 0.00035))
    aero_boost_r = 0.0 if is_dirt else min(0.40, max(0.0, ((df_rear or 0) - 150) * 0.00030))

    if fn_front_range and fn_rear_range:
        f_min_f, f_max_f = fn_front_range
        f_min_r, f_max_r = fn_rear_range
        span_f = f_max_f - f_min_f
        span_r = f_max_r - f_min_r
        if mass >= 2000:
            # Heavy EV: 85-90% of span to control 2+ ton roll moment
            target_f = f_min_f + span_f * (0.87 if not is_endurance else 0.82)
            target_r = f_min_r + span_r * (0.89 if not is_endurance else 0.85)
        elif any(g in grp for g in ['Gr.1', 'Gr.2', 'Gr.3', 'Gr.X']):
            pct_f, pct_r = (0.40, 0.50) if is_endurance else (0.75, 0.78)
            target_f = f_min_f + span_f * pct_f
            target_r = f_min_r + span_r * pct_r
        else:
            pct = 0.55 if is_endurance else 0.65
            target_f = f_min_f + span_f * pct
            target_r = target_f * 1.04

        target_f = min(f_max_f, max(f_min_f, target_f + aero_boost_f))
        target_r = min(f_max_r, max(f_min_r, target_r + aero_boost_r))
        return round(target_f, 2), round(target_r, 2), round(target_r / target_f, 2)

    if is_dirt:
        return 1.90, 1.65, 0.87
    if 'Gr.X' in grp:
        return round(3.80 + aero_boost_f, 2), round(4.05 + aero_boost_r, 2), 1.07
    if 'Gr.1' in grp:
        return round(3.60 + aero_boost_f, 2), round(3.80 + aero_boost_r, 2), 1.06
    if 'Gr.2' in grp:
        return round(3.45 + aero_boost_f, 2), round(3.65 + aero_boost_r, 2), 1.06
    if 'Gr.3' in grp:
        return round(3.35 + aero_boost_f, 2), round(3.55 + aero_boost_r, 2), 1.06
    if 'Gr.4' in grp:
        # Gr.4 racecars: scale between 2.60 and 2.85 Hz based on mass and compound
        f_base = 2.45 + (mu - 1.15) * 0.65
        mass_scale = (mass / 1300.0) ** 0.18
        f_base *= mass_scale
        if is_endurance:
            f_base *= 0.95  # Compliant suspension saves tire carcass from road shocks
        f_front = f_base * (1.0 + 0.25 * (wf - 0.50)) + aero_boost_f
        f_rear = f_base * 1.04 + aero_boost_r
        return round(f_front, 2), round(f_rear, 2), round(f_rear / f_front, 2)

    # Road Cars: dynamic mass scaling to prevent uniform 2.85 Hz artifact
    mass_scale = max(0.85, min(1.15, (mass / 1350.0) ** 0.20))
    f_base = (2.10 + (mu - 0.85) * 1.05) * mass_scale
    if is_endurance:
        f_base *= 0.94
    if bumpiness == 'high':
        f_base *= 0.92

    f_front = f_base * (1.0 + 0.30 * (wf - 0.50)) + aero_boost_f
    flat_ride_delta = 0.07 if wf <= 0.53 else max(-0.02, 0.07 - 0.40 * (wf - 0.53))
    f_rear = f_base * (1.0 + flat_ride_delta) + aero_boost_r

    if mass >= 2000:
        f_front = max(3.05, f_front)
        f_rear = max(2.95, f_rear)

    ratio = f_rear / f_front if f_front > 0 else 1.0
    return round(f_front, 2), round(f_rear, 2), round(ratio, 2)

def calculate_anti_roll_bars(
    wf: float = 0.50,
    drivetrain: str = 'FR',
    is_dirt: bool = False
) -> Tuple[int, int, float]:
    """
    Calculate front and rear ARB (1-10) directly from target LLTD
    (Lateral Load Transfer Distribution) to eliminate understeer or snap.
    """
    if is_dirt:
        return 1, 1, 50.0

    if drivetrain == 'RR':
        r_phi_f = 0.60 + 0.5 * (0.45 - wf)
    elif drivetrain == 'MR':
        r_phi_f = 0.44 + 0.2 * (0.45 - wf)
    elif drivetrain == 'FF':
        r_phi_f = max(0.20, 0.50 - 2.2 * (wf - 0.50))
    else:  # FR, AWD
        if wf >= 0.53:
            r_phi_f = max(0.22, 0.50 - 2.0 * (wf - 0.50))
        else:
            r_phi_f = 0.45 + 0.1 * (0.50 - wf)

    r_phi_f = max(0.18, min(0.75, r_phi_f))
    total_arb = 10.0
    arb_f = max(1, min(10, round(total_arb * r_phi_f)))
    arb_r = max(1, min(10, round(total_arb * (1.0 - r_phi_f))))
    return arb_f, arb_r, round(r_phi_f * 100.0, 1)
