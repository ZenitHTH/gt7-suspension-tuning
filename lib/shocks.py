#!/usr/bin/env python3
"""
GT7 Damping & Shock Absorber Module
Calculates critical damping compression and expansion ratios (0-100%),
incorporating anti-squat stiffening, high-speed crest rebound control, and trail-braking pitch support.
"""

from typing import Tuple, Optional


def _calculate_condition_dampers(
    is_dirt: bool,
    is_wet: bool
) -> Optional[Tuple[int, int, int, int]]:
    """Determine fixed damping presets for specialized track surface conditions."""
    if is_dirt:
        return 28, 28, 56, 56
    if is_wet:
        return 28, 28, 42, 42
    return None


def _calculate_compression_rates(
    bumpiness: str,
    ptw: float,
    is_high_boost: bool,
    drivetrain: str,
    wf: float,
    elevation_diff_m: float
) -> Tuple[int, int]:
    """Calculate front and rear compression damping percentages."""
    comp_base = 32 if bumpiness != 'high' else 30
    anti_squat = 0
    if drivetrain in ['FR', 'MR', 'RR'] and ptw >= 280:
        anti_squat = min(4, round((ptw - 200) / 75.0))
    elif is_high_boost:
        anti_squat = 2

    comp_f = max(26, min(40, comp_base - (2 if wf > 0.55 else 0)))
    if (elevation_diff_m or 0.0) >= 50.0:
        comp_f = max(31, min(40, comp_f + 1))
    comp_r = max(26, min(40, comp_base + anti_squat))
    return comp_f, comp_r


def _calculate_expansion_rates(
    comp_f: int,
    comp_r: int,
    elevation_diff_m: float
) -> Tuple[int, int]:
    """Calculate kinematic expansion (rebound) damping percentages."""
    exp_f = max(30, min(80, round(comp_f * 1.48)))
    exp_r_mult = 1.52 if (elevation_diff_m or 0.0) >= 50.0 else 1.38
    exp_r = max(30, min(80, round(comp_r * exp_r_mult)))
    return exp_f, exp_r


def _calculate_dry_dampers(
    bumpiness: str,
    ptw: float,
    is_high_boost: bool,
    drivetrain: str,
    wf: float,
    elevation_diff_m: float
) -> Tuple[int, int, int, int]:
    """Calculate baseline dry asphalt compression and expansion percentages."""
    comp_f, comp_r = _calculate_compression_rates(bumpiness, ptw, is_high_boost, drivetrain, wf, elevation_diff_m)
    exp_f, exp_r = _calculate_expansion_rates(comp_f, comp_r, elevation_diff_m)
    return comp_f, comp_r, exp_f, exp_r


def _apply_damper_ranges(
    comp_f: int,
    comp_r: int,
    exp_f: int,
    exp_r: int,
    comp_range: Optional[Tuple[int, int]],
    exp_range: Optional[Tuple[int, int]]
) -> Tuple[int, int, int, int]:
    """Clamp calculated damper values strictly within user-provided slider ranges."""
    if comp_range:
        comp_f = max(comp_range[0], min(comp_range[1], comp_f))
        comp_r = max(comp_range[0], min(comp_range[1], comp_r))
    if exp_range:
        exp_f = max(exp_range[0], min(exp_range[1], exp_f))
        exp_r = max(exp_range[0], min(exp_range[1], exp_r))
    return comp_f, comp_r, exp_f, exp_r


def calculate_dampers(
    bumpiness: str = 'medium',
    ptw: float = 200.0,
    is_high_boost: bool = False,
    drivetrain: str = 'FR',
    wf: float = 0.50,
    is_dirt: bool = False,
    is_wet: bool = False,
    elevation_diff_m: float = 0.0,
    comp_range: Optional[Tuple[int, int]] = None,
    exp_range: Optional[Tuple[int, int]] = None
) -> Tuple[int, int, int, int]:
    """Calculate critical damping compression and expansion ratios (0-100%)."""
    cond_res = _calculate_condition_dampers(is_dirt, is_wet)
    if cond_res:
        comp_f, comp_r, exp_f, exp_r = cond_res
    else:
        comp_f, comp_r, exp_f, exp_r = _calculate_dry_dampers(
            bumpiness, ptw, is_high_boost, drivetrain, wf, elevation_diff_m
        )

    return _apply_damper_ranges(comp_f, comp_r, exp_f, exp_r, comp_range, exp_range)
