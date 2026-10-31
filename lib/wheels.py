#!/usr/bin/env python3
"""
GT7 Wheel Alignment, Tires & Brake Proportioning Module
Calculates negative camber, toe angles (In / Out degrees), mechanical tire grip (mu),
and dynamic brake balance controller setting.
"""

import math
from typing import Tuple
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from gt7_constants import TIRE_MU_MAP


def get_tire_mu(compound: str) -> float:
    """Return mechanical friction coefficient (mu) for GT7 tire compound."""
    return TIRE_MU_MAP.get(compound, 1.25)


def _calculate_endurance_alignment(
    ay_est: float,
    wf: float,
    wr: float,
    drivetrain: str
) -> Tuple[float, float, str, str]:
    """Calculate tire-saver endurance alignment to reduce inner wear and straight scrub."""
    cam_f = - round(min(2.4, max(1.8, 0.85 + 0.90 * ay_est * math.sqrt(max(0.46, wf) / 0.50))), 1)
    eta_long = 0.70 if drivetrain in ['FR', 'MR', 'RR'] else 0.50
    cam_r = - round(0.45 + 0.65 * ay_est * math.sqrt(wr / 0.50) * eta_long, 1)

    toe_f_val = round(min(0.02, 0.00 + 0.05 * max(0.0, wf - 0.50)), 2)
    if drivetrain in ['MR', 'RR']:
        toe_r_val = round(min(0.22, max(0.12, 0.12 + 2.0 * max(0.0, wr - 0.54))), 2)
    else:
        toe_r_val = round(max(0.06, min(0.14, 0.06 + 0.15 * max(0.0, wr - 0.45))), 2)

    toe_f_str = f'Out {toe_f_val:.2f}' if toe_f_val > 0 else '0.00'
    return cam_f, cam_r, toe_f_str, f'In {toe_r_val:.2f}'


def _calculate_sprint_alignment(
    ay_est: float,
    wf: float,
    wr: float,
    drivetrain: str,
    power: float
) -> Tuple[float, float, str, str]:
    """Calculate maximum grip sprint alignment for sharp turn-in bite."""
    cam_f = - round(1.2 + 1.35 * ay_est * math.sqrt(wf / 0.50), 1)
    eta_long = 0.85 if drivetrain in ['FR', 'MR', 'RR'] else 0.60
    cam_r = - round(0.6 + 0.95 * ay_est * math.sqrt(wr / 0.50) * eta_long, 1)

    toe_f_val = round(max(0.04, min(0.10, 0.04 + 0.25 * max(0.0, wf - 0.48))), 2)
    p_factor = (power / 3000.0) * (0.10 if drivetrain != 'FF' else 0.0)
    toe_r_val = round(max(0.08, min(0.28, 0.08 + 0.35 * max(0.0, wr - 0.42) + p_factor)), 2)

    toe_f_str = f'Out {toe_f_val:.2f}' if toe_f_val > 0 else '0.00'
    return cam_f, cam_r, toe_f_str, f'In {toe_r_val:.2f}'


def calculate_wheel_alignment(
    ay_est: float = 1.30,
    wf: float = 0.50,
    wr: float = 0.50,
    drivetrain: str = 'FR',
    power: float = 300.0,
    is_dirt: bool = False,
    is_wet: bool = False,
    is_endurance: bool = False
) -> Tuple[float, float, str, str]:
    """Calculate negative camber (degrees) and toe alignment (In / Out degrees)."""
    if is_dirt:
        return 0.0, 0.0, '0.00', 'In 0.18'
    if is_wet:
        return -1.8, -1.0, 'Out 0.04', 'In 0.16'
    if is_endurance:
        return _calculate_endurance_alignment(ay_est, wf, wr, drivetrain)
    return _calculate_sprint_alignment(ay_est, wf, wr, drivetrain, power)


def calculate_brake_bias(
    wf: float = 0.50,
    hcg_m: float = 0.45,
    wheelbase_m: float = 2.60,
    drivetrain: str = 'FR',
    is_endurance: bool = False
) -> Tuple[int, float]:
    """Calculate Brake Balance Controller (-5 to +5) and dynamic load transfer (%)."""
    dynamic_pitch_transfer = (1.2 * hcg_m) / wheelbase_m
    if drivetrain == 'FF':
        return 1, round(dynamic_pitch_transfer * 100.0, 1)

    bias = max(-3, min(1, round(12.0 * (0.50 - wf))))
    if wf >= 0.56:
        bias = min(bias, -2)
    if is_endurance and wf >= 0.45:
        bias = max(-3, bias - 1)
    return bias, round(dynamic_pitch_transfer * 100.0, 1)
