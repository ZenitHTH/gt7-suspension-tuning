#!/usr/bin/env python3
"""
GT7 Quick-Trims Specification Module
Generates proactive Section 2.F quick-trim adjustments for tire wear and stability.
"""

from typing import Any, Dict, Optional

from lib.tire_wear import calculate_tire_wear_index

ECU_LIMIT_PCT = 70.0
PTW_WEAR_THRESHOLD = 250.0  # below this ptw_factor_r == 1.0, so ECU% cannot help


def _build_ecu_limit_note(p: Dict[str, Any], power_hp: float, mass_kg: float,
                          is_endurance: bool) -> Optional[Dict[str, Any]]:
    """Computed ECU 70% power-limit note: rear wear delta at the final setup.

    None when power is too low for the ptw factor to matter.
    """
    if not power_hp or not mass_kg:
        return None
    # ptw is HP/ton (models.VehicleSpec.power_to_weight), not HP/kg
    ptw = float(power_hp) / max(1.0, float(mass_kg)) * 1000.0
    if ptw <= PTW_WEAR_THRESHOLD:
        return None
    nf, cam, toe = p.get('natural_frequency_hz', {}), p.get('camber_deg', {}), p.get('toe_angle', {})
    fn_f, fn_r = nf.get('front', 2.50), nf.get('rear', 2.70)
    cam_f, cam_r = cam.get('front', -2.5), cam.get('rear', -1.5)
    toe_f, toe_r = toe.get('front', 0.0), toe.get('rear', 0.1)
    now = calculate_tire_wear_index(fn_f, fn_r, cam_f, cam_r, toe_f, toe_r,
                                    ptw=ptw, is_endurance=is_endurance)['rear_wear_factor']
    low = calculate_tire_wear_index(fn_f, fn_r, cam_f, cam_r, toe_f, toe_r,
                                    ptw=ECU_LIMIT_PCT / 100.0 * ptw, is_endurance=is_endurance)['rear_wear_factor']
    if low >= now - 0.005:
        return None
    hp_70 = int(round(ECU_LIMIT_PCT / 100.0 * float(power_hp)))
    return {
        'hp_70': hp_70,
        'rear_wear_now': now,
        'rear_wear_70': low,
        'label': f"ECU 70% ({hp_70} HP) cuts rear wear {now}x -> {low}x on long stints"
    }


def _build_tire_saver_spec(p: Dict[str, Any], drivetrain: str, is_endurance: bool) -> Dict[str, Any]:
    """Build tire-saver quick-trim specification."""
    nf = p.get('natural_frequency_hz', {})
    fn_f, fn_r = nf.get('front', 2.50), nf.get('rear', 2.70)
    lsd_r = p.get('lsd_rear') or {'init': 8, 'accel': 20, 'brake': 50}
    target_fn_f = round(max(1.40, fn_f - (0.0 if is_endurance else 0.20)), 2)
    target_fn_r = round(max(1.40, fn_r - (0.0 if is_endurance else 0.20)), 2)
    cam_f = p.get('camber_deg', {}).get('front', -2.8)
    cam_r = p.get('camber_deg', {}).get('rear', -1.5)
    cam_str = f"{min(-1.4, round(cam_f + 0.5, 1)):.1f}° / {min(-0.8, round(cam_r + 0.3, 1)):.1f}°"
    return {
        'natural_frequency_hz': f"{target_fn_f:.2f} / {target_fn_r:.2f} Hz",
        'negative_camber': cam_str,
        'toe_angle': '0.00° / In 0.12°' if drivetrain in ['MR', 'RR'] else '0.00° / In 0.08°',
        'lsd_accel': max(14, min(20, lsd_r['accel'] - (0 if is_endurance else 4))),
        'description': 'Softer spring rate, reduced camber & zero-scrub toe to eliminate tire overheating on long stints'
    }


def _build_max_stability_spec(p: Dict[str, Any], drivetrain: str) -> Dict[str, Any]:
    """Build max stability quick-trim specification."""
    arb = p.get('anti_roll_bar', {'front': 5, 'rear': 5})
    exp = p.get('damping_expansion_pct', {'front': 48, 'rear': 52})
    lsd_r = p.get('lsd_rear') or {'init': 8, 'accel': 20, 'brake': 50}
    bias = p.get('brake_bias', 0)
    stab_toe_r = 'In 0.20°' if drivetrain in ['MR', 'RR'] else 'In 0.18°'
    return {
        'anti_roll_bar': f"{min(8, arb['front'] + 1)} / {max(3, arb['rear'] - 1)}",
        'damping_expansion_rear': f"{min(80, exp['rear'] + 4)}%",
        'rear_toe_in': stab_toe_r,
        'lsd_braking_sens': min(65, lsd_r['brake'] + 8),
        'brake_bias': -1 if drivetrain == 'FF' else min(0, bias),
        'description': 'Anchors rear axle under braking, stiffens rear rebound, and dampens yaw to prevent snap-oversteer'
    }


def build_quick_trims(
    parameters: Dict[str, Any],
    drivetrain: str = 'FR',
    is_endurance: bool = False,
    power_hp: Optional[float] = None,
    mass_kg: Optional[float] = None
) -> Dict[str, Dict[str, Any]]:
    """Construct Section 2.F proactive quick-trim delta table."""
    tire_saver = _build_tire_saver_spec(parameters, drivetrain, is_endurance)
    ecu = _build_ecu_limit_note(parameters, power_hp, mass_kg, is_endurance)
    if ecu:
        tire_saver['ecu_limit'] = ecu
    return {
        'tire_saver': tire_saver,
        'max_stability': _build_max_stability_spec(parameters, drivetrain)
    }
