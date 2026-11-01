#!/usr/bin/env python3
"""
GT7 Natural Frequencies & Anti-Roll Bar Suspension Module
Calculates front and rear natural frequencies (Hz) using Olley flat ride pitch synchronization,
downforce load coupling, and Lateral Load Transfer Distribution (LLTD) for anti-roll bars.
"""

from typing import Tuple, Optional
from lib.formulas import normalize_group


def _get_ranged_target_pcts(
    mass: float,
    grp: str,
    is_endurance: bool,
    mu: float = 1.25
) -> Tuple[float, float, bool]:
    """Determine target interpolation percentages for explicit slider ranges."""
    if mass >= 2000:
        pct_f, pct_r = (0.82, 0.85) if is_endurance else (0.87, 0.89)
        return pct_f, pct_r, False
    if any(g in grp for g in ['Gr.1', 'Gr.2', 'Gr.3', 'Gr.X']):
        pct_f, pct_r = (0.40, 0.50) if is_endurance else (0.75, 0.78)
        return pct_f, pct_r, False
    mu_shift = max(-0.20, min(0.15, (mu - 1.35) * 0.45))
    base_pct = (0.55 if is_endurance else 0.65) + mu_shift
    return max(0.32, min(0.85, base_pct)), 0.0, True


def _calculate_ranged_frequencies(
    fn_front_range: Tuple[float, float],
    fn_rear_range: Tuple[float, float],
    mass: float,
    grp: str,
    is_endurance: bool,
    aero_boost_f: float,
    aero_boost_r: float,
    mu: float = 1.25,
    wf: float = 0.50
) -> Tuple[float, float, float]:
    """Calculate natural frequencies within explicit in-game slider ranges."""
    f_min_f, f_max_f = fn_front_range
    f_min_r, f_max_r = fn_rear_range
    pct_f, pct_r, is_road = _get_ranged_target_pcts(mass, grp, is_endurance, mu)

    target_f = f_min_f + (f_max_f - f_min_f) * pct_f
    fr_mult = 1.08 if wf < 0.46 else (1.03 if wf > 0.54 else 1.04)
    target_r = (target_f * fr_mult) if is_road else (f_min_r + (f_max_r - f_min_r) * pct_r)
    target_f = min(f_max_f, max(f_min_f, target_f + aero_boost_f))
    target_r = min(f_max_r, max(f_min_r, target_r + aero_boost_r))
    return round(target_f, 2), round(target_r, 2), round(target_r / target_f, 2)


def _calculate_gr4_frequencies(
    mu: float,
    mass: float,
    wf: float,
    is_endurance: bool,
    aero_boost_f: float,
    aero_boost_r: float
) -> Tuple[float, float, float]:
    """Calculate Gr.4 touring car natural frequencies."""
    f_base = (2.45 + (mu - 1.15) * 0.65) * ((mass / 1300.0) ** 0.18)
    if is_endurance:
        f_base *= 0.95
    f_front = f_base * (1.0 + 0.25 * (wf - 0.50)) + aero_boost_f
    f_rear = f_base * 1.04 + aero_boost_r
    return round(f_front, 2), round(f_rear, 2), round(f_rear / f_front, 2)


def _calculate_archetype_frequencies(
    grp: str,
    mu: float,
    mass: float,
    wf: float,
    is_endurance: bool,
    aero_boost_f: float,
    aero_boost_r: float
) -> Optional[Tuple[float, float, float]]:
    """Calculate natural frequencies for homologated racing archetypes."""
    fixed_archetypes = {
        'Gr.X': (3.80, 4.05, 1.07), 'Gr.1': (3.60, 3.80, 1.06),
        'Gr.2': (3.45, 3.65, 1.06), 'Gr.3': (3.35, 3.55, 1.06)
    }
    for tag, (base_f, base_r, ratio) in fixed_archetypes.items():
        if tag in grp:
            return round(base_f + aero_boost_f, 2), round(base_r + aero_boost_r, 2), ratio
    if 'Gr.4' in grp:
        return _calculate_gr4_frequencies(mu, mass, wf, is_endurance, aero_boost_f, aero_boost_r)
    return None


def _calculate_road_frequencies(
    mu: float,
    mass: float,
    wf: float,
    bumpiness: str,
    is_endurance: bool,
    aero_boost_f: float,
    aero_boost_r: float
) -> Tuple[float, float, float]:
    """Calculate natural frequencies for production road cars."""
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
        f_front, f_rear = max(3.05, f_front), max(2.95, f_rear)

    ratio = f_rear / f_front if f_front > 0 else 1.0
    return round(f_front, 2), round(f_rear, 2), round(ratio, 2)


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
    """Calculate front and rear natural frequencies (Hz) using Flat Ride synchronization."""
    if is_dirt:
        return 1.90, 1.65, 0.87

    aero_boost_f = min(0.35, max(0.0, ((df_front or 0) - 100) * 0.00035))
    aero_boost_r = min(0.40, max(0.0, ((df_rear or 0) - 150) * 0.00030))
    grp = normalize_group(group)

    if fn_front_range and fn_rear_range:
        return _calculate_ranged_frequencies(
            fn_front_range, fn_rear_range, mass, grp, is_endurance, aero_boost_f, aero_boost_r, mu, wf
        )
    arch_res = _calculate_archetype_frequencies(
        grp, mu, mass, wf, is_endurance, aero_boost_f, aero_boost_r
    )
    if arch_res:
        return arch_res

    return _calculate_road_frequencies(mu, mass, wf, bumpiness, is_endurance, aero_boost_f, aero_boost_r)


def _calculate_target_lltd(wf: float, drivetrain: str) -> float:
    """Calculate target Lateral Load Transfer Distribution ratio based on weight and drivetrain."""
    if drivetrain == 'RR':
        r_phi = 0.60 + 0.5 * (0.45 - wf)
    elif drivetrain == 'MR':
        r_phi = 0.44 + 0.2 * (0.45 - wf)
    elif drivetrain == 'FF':
        r_phi = max(0.20, 0.50 - 2.2 * (wf - 0.50))
    elif wf >= 0.53:
        r_phi = max(0.22, 0.50 - 2.0 * (wf - 0.50))
    else:
        r_phi = 0.45 + 0.1 * (0.50 - wf)
    return max(0.18, min(0.75, r_phi))


def calculate_anti_roll_bars(
    wf: float = 0.50,
    drivetrain: str = 'FR',
    is_dirt: bool = False
) -> Tuple[int, int, float]:
    """Calculate front and rear ARB (1-10) directly from target LLTD."""
    if is_dirt:
        return 1, 1, 50.0

    r_phi_f = _calculate_target_lltd(wf, drivetrain)
    total_arb = 10.0
    arb_f = max(1, min(10, round(total_arb * r_phi_f)))
    arb_r = max(1, min(10, round(total_arb * (1.0 - r_phi_f))))
    return arb_f, arb_r, round(r_phi_f * 100.0, 1)
