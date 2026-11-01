#!/usr/bin/env python3
"""
GT7 Drivetrain, Differential & Transmission Module
Calculates Limited Slip Differential (LSD) initial torque, acceleration sensitivity,
braking sensitivity, and transmission auto-set top speed.
"""

from typing import Dict, Tuple, Optional


def _calculate_lsd_braking_sens(
    drivetrain: str, wr: float, is_controller: bool, is_endurance: bool
) -> int:
    """Calculate LSD braking sensitivity based on drivetrain architecture and controller filter."""
    if drivetrain == 'FF':
        return 12
    if drivetrain in ['MR', 'RR']:
        return 100 if is_controller else max(45, min(60, round(40.0 + 60.0 * (wr - 0.45))))
    if is_controller:
        return 85
    t_brake = max(12, min(16, round(12.0 + 30.0 * max(0.0, wr - 0.48))))
    return max(12, t_brake - 1) if is_endurance else t_brake


def _calculate_lsd_accel_sens(ptw: float, is_endurance: bool) -> int:
    """Calculate LSD acceleration sensitivity based on power-to-weight ratio."""
    if is_endurance:
        return max(16, min(30, round(36.0 - (ptw / 22.0))))
    return max(18, min(45, round(45.0 - (ptw / 18.0))))


def _calculate_lsd_init_torque(torque: float, drivetrain: str, is_endurance: bool) -> int:
    """Calculate LSD initial torque based on engine torque and endurance status."""
    mult = 0.8 if drivetrain == 'FF' else 1.0
    t_init = max(4, min(12, round(4.0 + (torque / 180.0) * mult)))
    return max(4, t_init - 1) if is_endurance else t_init


def calculate_differential_lsd(
    torque: float = 400.0, ptw: float = 250.0, wr: float = 0.50,
    drivetrain: str = 'FR', is_endurance: bool = False, is_controller: bool = False
) -> Tuple[Dict[str, int], Optional[Dict[str, int]]]:
    """Calculate LSD Initial Torque (0-30), Accel Sensitivity, and Braking Sensitivity."""
    t_init = _calculate_lsd_init_torque(torque, drivetrain, is_endurance)
    t_accel = _calculate_lsd_accel_sens(ptw, is_endurance)
    t_brake = _calculate_lsd_braking_sens(drivetrain, wr, is_controller, is_endurance)
    lsd_rear = {'init': t_init, 'accel': t_accel, 'brake': t_brake}
    lsd_front = None
    if drivetrain in ['AWD', '4WD', '4x4']:
        lsd_front = {'init': 5, 'accel': 16, 'brake': 20}
        lsd_rear = {'init': 7, 'accel': 28, 'brake': 100 if is_controller else 44}
    return lsd_rear, lsd_front


def _get_base_top_speed(power: float, ptw: float) -> int:
    """Calculate base terminal velocity tier from power-to-weight ratio."""
    if ptw >= 750 or (power >= 700 and ptw >= 550):
        return 330
    if ptw >= 350 or power >= 500:
        return 280
    if ptw >= 220 or power >= 300:
        return 260
    return 230


def _adjust_top_speed_for_track(
    base_v: int,
    straight_m: float,
    is_oval: bool,
    elevation_diff_m: float
) -> int:
    """Adjust top speed for straightaway length and downhill gravity assist."""
    if is_oval or straight_m >= 1100:
        return base_v + 20
    if straight_m >= 750:
        return base_v + (10 if elevation_diff_m >= 40.0 else 0)
    if 0 < straight_m <= 550:
        return max(210, base_v - 15)
    return base_v


def calculate_top_speed(
    power: float = 300.0,
    ptw: float = 200.0,
    longest_straight_m: float = 0.0,
    is_oval: bool = False,
    elevation_diff_m: float = 0.0
) -> int:
    """Calculate transmission auto-set top speed (km/h) based on power tier and circuit layout."""
    base_v = _get_base_top_speed(float(power or 300.0), float(ptw or 200.0))
    return _adjust_top_speed_for_track(
        base_v, float(longest_straight_m or 0.0), is_oval, float(elevation_diff_m or 0.0)
    )
