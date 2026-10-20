#!/usr/bin/env python3
"""
GT7 Drivetrain, Differential & Transmission Module
Calculates Limited Slip Differential (LSD) initial torque, acceleration sensitivity,
braking sensitivity, and transmission auto-set top speed.
"""

from typing import Dict, Tuple, Optional

def calculate_differential_lsd(
    torque: float = 400.0,
    ptw: float = 250.0,
    wr: float = 0.50,
    drivetrain: str = 'FR',
    is_endurance: bool = False
) -> Tuple[Dict[str, int], Optional[Dict[str, int]]]:
    """
    Calculate LSD Initial Torque (0-30), Accel Sensitivity (0-100), and Braking Sensitivity (0-100)
    for GT7 Update 1.71+ physics.
    """
    t_init = max(4, min(12, round(4.0 + (torque / 180.0) * (0.8 if drivetrain == 'FF' else 1.0))))
    if is_endurance:
        t_init = max(4, t_init - 1)

    if is_endurance:
        t_accel = max(16, min(30, round(36.0 - (ptw / 22.0))))
    else:
        t_accel = max(18, min(45, round(45.0 - (ptw / 18.0))))

    if drivetrain == 'FF':
        t_brake = 12
    elif drivetrain in ['MR', 'RR']:
        t_brake = max(45, min(60, round(40.0 + 60.0 * (wr - 0.45))))
    else:  # FR, AWD
        t_brake = max(12, min(16, round(12.0 + 30.0 * max(0.0, wr - 0.48))))
    if is_endurance and drivetrain not in ['MR', 'RR']:
        t_brake = max(12, t_brake - 1)

    lsd_rear = {'init': t_init, 'accel': t_accel, 'brake': t_brake}
    lsd_front = None
    if drivetrain in ['AWD', '4WD']:
        lsd_front = {'init': 5, 'accel': 16, 'brake': 20}
        lsd_rear = {'init': 7, 'accel': 28, 'brake': 44}

    return lsd_rear, lsd_front

def calculate_top_speed(
    power: float = 300.0,
    ptw: float = 200.0,
    longest_straight_m: float = 0.0,
    is_oval: bool = False
) -> int:
    """Calculate transmission auto-set top speed (km/h) based on power, weight, and circuit straight length."""
    if power >= 650:
        base_v = 310
    elif power >= 450:
        base_v = 280
    elif power >= 300:
        base_v = 260
    else:
        base_v = 230

    straight_m = float(longest_straight_m or 0.0)
    if is_oval or straight_m >= 1100:
        base_v += 20
    elif 0 < straight_m <= 550:
        base_v = max(210, base_v - 15)

    return base_v
