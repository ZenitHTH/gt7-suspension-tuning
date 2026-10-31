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
    base_g: Tuple[float, float, float]
    k_aero: float
    front_weight_ratio: float
    ref_downforce: Tuple[int, int]
    ref_eff_df: float


def _cp_balance_efficiency(df_front: int, df_rear: int, front_weight_ratio: float) -> float:
    """Calculate aerodynamic Center of Pressure (CP) efficiency multiplier."""
    total_df = df_front + df_rear
    if total_df <= 0:
        return 1.0
    target_share = max(0.32, min(0.46, 1.0 - front_weight_ratio))
    front_share = float(df_front) / float(total_df)
    imbalance = abs(front_share - target_share)
    return max(0.75, 1.0 - 0.65 * imbalance)


def calibrate_g_model(config: GForceCalibrationInput) -> GForceModel:
    """Calibrate G-force model anchored to measured 60/120/240 km/h telemetry."""
    ref_df = config.ref_downforce or (0, 0)
    eta_ref = _cp_balance_efficiency(ref_df[0], ref_df[1], config.front_weight_ratio)
    eff_ref = float(ref_df[0] + ref_df[1]) * eta_ref
    mass_scale = 1200.0 / max(500.0, float(config.mass_kg))
    k_aero = round(0.00048 * mass_scale, 6)

    if not config.measured_g:
        mu = config.base_mu
        base_g = (mu, round(mu + 0.08 * (eff_ref / 300.0), 2), round(mu + 0.22 * (eff_ref / 300.0), 2))
        return GForceModel(base_g, k_aero, config.front_weight_ratio, ref_df, eff_ref)

    return GForceModel(config.measured_g, k_aero, config.front_weight_ratio, ref_df, eff_ref)


def _calculate_speed_g(ref_g: float, delta_eff_df: float, k_aero: float, speed_kmh: float) -> float:
    """Calculate cornering G at speed from reference G and effective downforce delta."""
    speed_factor = max(0.12, (speed_kmh / 240.0) ** 2)
    return round(ref_g + speed_factor * k_aero * delta_eff_df, 2)


def predict_g_at_downforce(model: GForceModel, downforce: Tuple[int, int]) -> Dict[str, Any]:
    """Predict 60/120/240 km/h cornering G at a specific (front, rear) downforce."""
    df_f, df_r = downforce
    eta = _cp_balance_efficiency(df_f, df_r, model.front_weight_ratio)
    eff_df = float(df_f + df_r) * eta
    delta_eff = eff_df - model.ref_eff_df
    g_60 = _calculate_speed_g(model.base_g[0], delta_eff, model.k_aero, 60.0)
    g_120 = _calculate_speed_g(model.base_g[1], delta_eff, model.k_aero, 120.0)
    g_240 = _calculate_speed_g(model.base_g[2], delta_eff, model.k_aero, 240.0)
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
