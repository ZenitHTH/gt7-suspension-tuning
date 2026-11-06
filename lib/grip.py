#!/usr/bin/env python3
"""
GT7 Tire Grip Limit Checker (Closed-Form Friction-Circle Check)
Per-corner vertical loads under lateral acceleration, load-sensitive tire
friction, saturation direction (which axle gives up first), and a signed
understeer gradient.
"""

from typing import Any, Dict

G = 9.81
LOAD_SENSITIVITY_EXP = 0.15            # mu_eff = mu_ref * (Fz_ref/Fz)**0.15
C_ALPHA_TIRE_ROAD_N_PER_RAD = 2.0e5    # generic road tire, per tire
C_ALPHA_TIRE_RACE_N_PER_RAD = 3.0e5    # generic race tire, per tire


def _load_sensitivity_mu(mu_ref: float, fz_n: float, fz_ref_n: float) -> float:
    """Per-kg tire friction drops as corner load rises."""
    fz = max(10.0, fz_n)
    return mu_ref * (fz_ref_n / fz) ** LOAD_SENSITIVITY_EXP


def calculate_grip_check(
    veh: Any,
    mu: float,
    ay_g: float,
    lltd_f: float
) -> Dict[str, Any]:
    """Check tire grip limit at ay_g lateral acceleration.

    veh: VehicleSpec (mass_kg, front_weight_ratio, hcg_m, track_width_m, wheelbase_m, is_racecar)
    mu: tire friction coefficient (constants.TIRE_MU_MAP)
    ay_g: target cornering G (typically predicted g_240)
    lltd_f: front share of lateral load transfer (0.0-1.0)
    """
    m = float(veh.mass_kg)
    wf = min(0.85, max(0.15, float(veh.front_weight_ratio)))
    lltd_f = min(1.0, max(0.0, float(lltd_f)))
    ay = max(0.05, float(ay_g))

    # 1. Static axle loads (N)
    wf_n = m * G * wf
    wr_n = m * G * (1.0 - wf)

    # 2. Lateral load transfer (N) via CG height
    ay_mps2 = ay * G
    total_transfer = m * ay_mps2 * veh.hcg_m / max(1.0, veh.track_width_m)
    d_f = total_transfer * lltd_f
    d_r = total_transfer * (1.0 - lltd_f)

    # 3. Per-corner vertical load (N)
    fz_f_out = wf_n / 2.0 + d_f / 2.0
    fz_f_in = max(0.0, wf_n / 2.0 - d_f / 2.0)
    fz_r_out = wr_n / 2.0 + d_r / 2.0
    fz_r_in = max(0.0, wr_n / 2.0 - d_r / 2.0)

    # 4. Load-sensitive friction limit (outside tire binds first)
    fz_ref = m * G / 4.0
    mu_f_out = _load_sensitivity_mu(mu, fz_f_out, fz_ref)
    mu_r_out = _load_sensitivity_mu(mu, fz_r_out, fz_ref)
    margin_f = mu_f_out / ay
    margin_r = mu_r_out / ay
    min_margin = min(margin_f, margin_r)

    # 5. Understeer gradient K (rad per G): >0 understeer, <0 oversteer
    ca_tire = C_ALPHA_TIRE_RACE_N_PER_RAD if veh.is_racecar else C_ALPHA_TIRE_ROAD_N_PER_RAD
    ca_f = 2.0 * ca_tire
    ca_r = 2.0 * ca_tire
    k_gradient = (wf_n / ca_f - wr_n / ca_r
                  + m * ay_mps2 * veh.hcg_m / (max(1.5, veh.wheelbase_m) * ca_r))
    if k_gradient > 0.002:
        balance = 'understeer'
    elif k_gradient < -0.002:
        balance = 'oversteer'
    else:
        balance = 'neutral'

    if margin_f < margin_r:
        saturation = 'front'
    elif margin_r < margin_f:
        saturation = 'rear'
    else:
        saturation = 'balanced'
    status = 'pass' if min_margin >= 1.0 else 'warn'

    return {
        'ay_check_g': round(ay, 2),
        'mu_ref': round(float(mu), 2),
        'static_load_n': {'front': int(round(wf_n)), 'rear': int(round(wr_n))},
        'corner_fz_n': {
            'front_outside': int(round(fz_f_out)), 'front_inside': int(round(fz_f_in)),
            'rear_outside': int(round(fz_r_out)), 'rear_inside': int(round(fz_r_in))
        },
        'transfer_front_n': int(round(d_f)),
        'margins': {'front': round(margin_f, 2), 'rear': round(margin_r, 2), 'min': round(min_margin, 2)},
        'saturation': saturation,
        'handling_balance': balance,
        'understeer_gradient': round(k_gradient, 4),
        'status': status
    }