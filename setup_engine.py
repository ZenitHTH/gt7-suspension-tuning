#!/usr/bin/env python3
"""
GT7 Setup Engine (Suspension & Physical Dynamics Execution)
Executes physics calculations, merges slider ranges, and runs baseline calculations.
"""

from typing import Dict, Tuple, Optional, Any
from models import VehicleSpec, TrackSpec
import lib


def resolve_slider_ranges(car: Dict[str, Any], explicit: Dict[str, Any]) -> Dict[str, Any]:
    """Merge user explicit slider ranges with pre-seeded or saved vehicle ranges."""
    saved = car.get('slider_ranges') or {}
    resolved = {}
    for key in ['df_front', 'df_rear', 'height_range', 'height_front', 'height_rear', 'fn_front', 'fn_rear', 'compression', 'expansion']:
        val = explicit.get(key)
        if val is None and key in saved:
            val = tuple(saved[key])
        resolved[key] = val
    # Explicit damper ranges win; otherwise fall back to saved DB values.
    resolved['comp_range'] = resolved.get('compression') or (
        tuple(saved['damping_comp']) if 'damping_comp' in saved else None)
    resolved['exp_range'] = resolved.get('expansion') or (
        tuple(saved['damping_exp']) if 'damping_exp' in saved else None)
    return resolved


def init_vehicle_and_track_specs(
    car: Dict[str, Any], track: Optional[Dict[str, Any]], tire: str,
    mode: str, overrides: Dict[str, Any], is_widebody: bool
) -> Tuple[VehicleSpec, TrackSpec, Dict[str, Any]]:
    """Initialize VehicleSpec, TrackSpec, and update car output dict."""
    veh = VehicleSpec.from_dict(car, custom_overrides=overrides, is_widebody=is_widebody)
    trk = TrackSpec.from_dict(track, mode=mode, tire=tire)
    f_pct, r_pct = int(round(veh.front_weight_ratio * 100)), int(round(veh.rear_weight_ratio * 100))
    out_car = {
        **car, 'mass_kg': int(veh.mass_kg), 'drivetrain': veh.drivetrain,
        'balance': {'front_pct': f_pct, 'rear_pct': r_pct, 'ratio_str': f"{f_pct}:{r_pct}"}
    }
    return veh, trk, out_car


def _format_range_dict(
    f_val: Any, r_val: Any, f_range: Optional[Tuple],
    r_range: Optional[Tuple], single_range: Optional[Tuple]
) -> Dict[str, Any]:
    """Format dictionary containing front/rear values and range bounds string."""
    res: Dict[str, Any] = {'front': f_val, 'rear': r_val}
    if single_range:
        res['range'] = f"{single_range[0]}-{single_range[1]}"
    elif f_range and r_range:
        fmt = ".2f" if isinstance(f_range[0], float) else ""
        res['range_f'], res['range_r'] = f"{f_range[0]:{fmt}}-{f_range[1]:{fmt}}", f"{r_range[0]:{fmt}}-{r_range[1]:{fmt}}"
    return res


def _is_no_aero(veh: VehicleSpec, tire: str, df: Dict[str, Any], df_slider: Any) -> bool:
    """Determine if car runs in no-aero high rake configuration."""
    if veh.is_racecar or tire not in ['RS', 'RM', 'RH']:
        return False
    return df_slider == (0, 0) or (df.get('front', 0) == 0 and df.get('rear', 0) == 0)


def _compute_aero_and_height(
    veh: VehicleSpec, trk: TrackSpec, tire: str, sliders: Dict[str, Any],
    is_widebody: bool, is_controller: bool
) -> Tuple[Dict[str, Any], int, int, bool]:
    """Calculate aerodynamic downforce and ground clearance."""
    df = lib.calculate_aerodynamics(
        sliders['df_front'], sliders['df_rear'], veh.front_weight_ratio, veh.group,
        is_oval=trk.is_oval, downforce_demand=trk.downforce_demand, is_endurance=trk.is_endurance,
        width_m=veh.width_m, height_m=veh.height_m, body_style=veh.body_style
    )
    is_no_aero = _is_no_aero(veh, tire, df, sliders['df_front'])
    rh_f, rh_r = lib.calculate_ride_height(
        trk.is_dirt, veh.is_racecar, veh.is_ultralight, veh.body_style, trk.bumpiness,
        veh.power_to_weight, veh.front_weight_ratio, sliders['height_range'], sliders['height_front'],
        sliders['height_rear'], elevation_diff_m=trk.elevation_diff_m, is_widebody=is_widebody,
        height_m=veh.height_m, group=veh.group, is_controller=is_controller, is_no_aero_rake=is_no_aero
    )
    return df, rh_f, rh_r, is_no_aero


def _compute_springs_and_shocks(
    veh: VehicleSpec, trk: TrackSpec, mu: float, sliders: Dict[str, Any], df: Dict[str, Any]
) -> Tuple[float, float, float, int, int, float, Tuple[int, int, int, int]]:
    """Calculate natural frequencies, anti-roll bars, and dampers."""
    fn_f, fn_r, fr_ratio = lib.calculate_natural_frequencies(
        mu, veh.front_weight_ratio, trk.bumpiness, veh.group, veh.mass_kg,
        trk.is_dirt, trk.is_endurance, sliders['fn_front'], sliders['fn_rear'],
        df_front=df['front'], df_rear=df['rear']
    )
    arb_f, arb_r, lltd_pct = lib.calculate_anti_roll_bars(veh.front_weight_ratio, veh.drivetrain, trk.is_dirt)
    is_high_boost = bool('Turbo' in veh.aspiration and veh.power_hp > 450)
    dampers = lib.calculate_dampers(
        trk.bumpiness, veh.power_to_weight, is_high_boost, veh.drivetrain,
        veh.front_weight_ratio, trk.is_dirt, trk.is_wet, elevation_diff_m=trk.elevation_diff_m,
        comp_range=sliders['comp_range'], exp_range=sliders['exp_range']
    )
    return fn_f, fn_r, fr_ratio, arb_f, arb_r, lltd_pct, dampers


def _resolve_differential_and_brakes(
    veh: VehicleSpec,
    trk: TrackSpec,
    is_controller: bool
) -> Tuple[Any, Any, int, float]:
    """Calculate LSD front/rear sensitivities and brake proportioning."""
    lsd_r, lsd_f = lib.calculate_differential_lsd(
        veh.torque_nm, veh.power_to_weight, veh.rear_weight_ratio, veh.drivetrain, trk.is_endurance,
        is_controller=is_controller
    )
    if veh.drivetrain == 'FF':
        lsd_f = dict(lsd_r) if isinstance(lsd_r, dict) else lsd_r
    bias, pitch_trans = lib.calculate_brake_bias(
        veh.front_weight_ratio, veh.hcg_m, veh.wheelbase_m, veh.drivetrain,
        is_endurance=trk.is_endurance, is_controller=is_controller
    )
    return lsd_r, lsd_f, bias, pitch_trans


def _compute_control_and_gearing(
    veh: VehicleSpec,
    trk: TrackSpec,
    ay_est: float,
    is_controller: bool
) -> Tuple[Tuple[float, float, str, str], Any, Any, int, float, int, Optional[str]]:
    """Calculate alignment, differential, brakes, and transmission gearing."""
    alignment = lib.calculate_wheel_alignment(
        ay_est, veh.front_weight_ratio, veh.rear_weight_ratio, veh.drivetrain,
        veh.power_hp, trk.is_dirt, trk.is_wet, trk.is_endurance
    )
    lsd_r, lsd_f, bias, pitch_trans = _resolve_differential_and_brakes(veh, trk, is_controller)
    top_spd = lib.calculate_top_speed(
        veh.power_hp, veh.power_to_weight, trk.longest_straight_m, trk.is_oval, trk.elevation_diff_m
    )
    awd_split = 'Fixed (Homologation / ปรับไม่ได้ใน Gr.4)' if (
        veh.drivetrain in ['AWD', '4WD'] and veh.group == 'Gr.4'
    ) else ('35:65' if veh.drivetrain in ['AWD', '4WD'] else None)
    return alignment, lsd_r, lsd_f, bias, pitch_trans, top_spd, awd_split


def _build_params_dict(
    rh_dict: Dict[str, Any], fn_dict: Dict[str, Any], arb: Tuple[int, int],
    dampers: Tuple[int, int, int, int], align: Tuple[float, float, str, str],
    df: Dict[str, Any], lsd_r: Any, lsd_f: Any, bias: int, awd_split: Optional[str],
    top_spd: int, is_controller: bool = False
) -> Dict[str, Any]:
    """Package baseline parameters into unified dictionary."""
    return {
        'ride_height_mm': rh_dict, 'natural_frequency_hz': fn_dict,
        'anti_roll_bar': {'front': arb[0], 'rear': arb[1]},
        'damping_compression_pct': {'front': dampers[0], 'rear': dampers[1]},
        'damping_expansion_pct': {'front': dampers[2], 'rear': dampers[3]},
        'camber_deg': {'front': align[0], 'rear': align[1]},
        'toe_angle': {'front': align[2], 'rear': align[3]},
        'downforce': df, 'lsd_rear': lsd_r, 'lsd_front': lsd_f, 'brake_bias': bias,
        'awd_torque_split': awd_split, 'transmission_top_speed_kmh': top_spd,
        'is_controller': is_controller, 'endurance_notes': []
    }


def _format_telemetry(
    sprung: Tuple[float, float, float],
    mu_ay: Tuple[float, float, Optional[Tuple[float, float, float]]],
    chassis: Tuple[float, float, float, bool]
) -> Dict[str, Any]:
    """Package baseline telemetry output dictionary."""
    tot_s, c_f, c_r = sprung
    mu, ay_est, g_forces = mu_ay
    lltd_pct, fr_ratio, pitch_pct, is_no_aero = chassis
    return {
        'tot_s': tot_s, 'c_f': c_f, 'c_r': c_r, 'mu': mu, 'ay_est': ay_est,
        'mu_braking': round(float(g_forces[1]), 2) if g_forces else mu,
        'lltd_pct': lltd_pct, 'fr_ratio': fr_ratio, 'pitch_transfer_pct': pitch_pct, 'is_no_aero': is_no_aero
    }


def compute_baseline_suspension(
    veh: VehicleSpec, trk: TrackSpec, tire: str, sliders: Dict[str, Any],
    is_widebody: bool, is_controller: bool, g_forces: Optional[Tuple[float, float, float]] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Compute complete baseline physical suspension parameters and telemetry."""
    # Surface-aware friction: a measured in-game anchor (g_forces) is already
    # calibrated on THIS circuit, so it encodes the surface as-is. The
    # tire-map fallback must instead carry the track's grip_modifier
    # (city asphalt looser, snow/dirt far less, Tokyo Expressway modern tarmac).
    if g_forces:
        mu = round(float(g_forces[0]), 2)
    else:
        mu = round(lib.get_tire_mu(tire) * trk.grip_modifier, 3)
    bump_mult = 0.90 if trk.bumpiness == 'high' else (1.05 if trk.bumpiness == 'low' else 1.00)
    ay_est = (float(g_forces[1]) if g_forces else mu) * bump_mult
    sprung = lib.calculate_sprung_mass(veh.mass_kg, veh.front_weight_ratio, veh.group)
    df, rh_f, rh_r, is_no_aero = _compute_aero_and_height(veh, trk, tire, sliders, is_widebody, is_controller)
    fn_f, fn_r, fr_ratio, arb_f, arb_r, lltd_pct, dampers = _compute_springs_and_shocks(veh, trk, mu, sliders, df)
    align, lsd_r, lsd_f, bias, pitch_pct, top_spd, awd_split = _compute_control_and_gearing(veh, trk, ay_est, is_controller)
    rh_dict = _format_range_dict(rh_f, rh_r, sliders['height_front'], sliders['height_rear'], sliders['height_range'])
    fn_dict = _format_range_dict(fn_f, fn_r, sliders['fn_front'], sliders['fn_rear'], None)
    params = _build_params_dict(
        rh_dict, fn_dict, (arb_f, arb_r), dampers, align, df, lsd_r, lsd_f, bias, awd_split, top_spd, is_controller
    )
    telem = _format_telemetry(sprung, (mu, ay_est, g_forces), (lltd_pct, fr_ratio, pitch_pct, is_no_aero))
    return params, telem
