#!/usr/bin/env python3
"""
GT7 Dynamic G-Force Calibrator & Downforce Predictor
Calibrates 3-point in-game rotational G telemetry at reference downforce
and predicts cornering G across the aero adjustment envelope.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any


@dataclass
class GForceCalibrationInput:
    measured_g: Optional[Tuple[float, float, float]] = None
    ref_downforce: Optional[Tuple[int, int]] = None
    base_mu: float = 1.55
    front_weight_ratio: float = 0.50
    mass_kg: float = 1200.0


@dataclass
class GForceModel:
    mu_zero: float
    k_aero: float
    front_weight_ratio: float
    ref_downforce: Tuple[int, int]


def _cp_balance_efficiency(df_front: int, df_rear: int, front_weight_ratio: float) -> float:
    """Calculate aerodynamic Center of Pressure (CP) efficiency multiplier."""
    total_df = df_front + df_rear
    if total_df <= 0:
        return 1.0
    target_share = max(0.32, min(0.46, 1.0 - front_weight_ratio))
    front_share = float(df_front) / float(total_df)
    imbalance = abs(front_share - target_share)
    return max(0.84, 1.0 - 0.55 * imbalance)


def _solve_k_aero_from_telemetry(g_60: float, g_240: float, effective_ref_df: float) -> Tuple[float, float]:
    """Solve baseline mechanical mu and aero scaling constant from 60 and 240 km/h G-forces."""
    delta_g_240 = max(0.0, (g_240 - g_60) / 0.9375)
    mu_zero = g_60 - 0.0625 * delta_g_240
    k_aero = delta_g_240 / max(1.0, effective_ref_df) if effective_ref_df > 0 else 0.0
    return mu_zero, k_aero


def calibrate_g_model(config: GForceCalibrationInput) -> GForceModel:
    """Calibrate G-force model from measured telemetry or fallback baseline."""
    ref_df = config.ref_downforce or (0, 0)
    if not config.measured_g:
        return GForceModel(
            mu_zero=config.base_mu,
            k_aero=0.0012,
            front_weight_ratio=config.front_weight_ratio,
            ref_downforce=ref_df
        )

    g_60, _, g_240 = config.measured_g
    eta_ref = _cp_balance_efficiency(ref_df[0], ref_df[1], config.front_weight_ratio)
    effective_ref_df = float(ref_df[0] + ref_df[1]) * eta_ref
    mu_zero, k_aero = _solve_k_aero_from_telemetry(g_60, g_240, effective_ref_df)
    return GForceModel(
        mu_zero=mu_zero,
        k_aero=k_aero,
        front_weight_ratio=config.front_weight_ratio,
        ref_downforce=ref_df
    )


def _calculate_speed_g(mu_zero: float, delta_g_240: float, speed_kmh: float) -> float:
    """Calculate cornering G at a specific speed from aerodynamic delta G."""
    speed_factor = (speed_kmh / 240.0) ** 2
    return round(mu_zero + speed_factor * delta_g_240, 2)


def predict_g_at_downforce(model: GForceModel, downforce: Tuple[int, int]) -> Dict[str, Any]:
    """Predict 60/120/240 km/h cornering G at a specific (front, rear) downforce."""
    df_f, df_r = downforce
    eta = _cp_balance_efficiency(df_f, df_r, model.front_weight_ratio)
    delta_g_240 = model.k_aero * float(df_f + df_r) * eta
    g_60 = _calculate_speed_g(model.mu_zero, delta_g_240, 60.0)
    g_120 = _calculate_speed_g(model.mu_zero, delta_g_240, 120.0)
    g_240 = _calculate_speed_g(model.mu_zero, delta_g_240, 240.0)
    return {
        'g_60': g_60,
        'g_120': g_120,
        'g_240': g_240,
        'downforce': {'front': df_f, 'rear': df_r},
        'cp_efficiency': round(eta, 3),
        'summary': f"{g_60:.2f}G / {g_120:.2f}G / {g_240:.2f}G @ DF {df_f}/{df_r}"
    }


def build_df_g_profile(
    model: GForceModel,
    df_ranges: Tuple[Tuple[int, int], Tuple[int, int]],
    active_df: Tuple[int, int]
) -> Dict[str, Any]:
    """Build dynamic G-force profile across min, active, and max downforce bounds."""
    (min_f, max_f), (min_r, max_r) = df_ranges
    return {
        'min_aero': predict_g_at_downforce(model, (min_f, min_r)),
        'active': predict_g_at_downforce(model, active_df),
        'max_aero': predict_g_at_downforce(model, (max_f, max_r))
    }
