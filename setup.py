#!/usr/bin/env python3
"""
GT7 Setup Synthesizer Orchestrator (Root Setup Coordinator)
Coordinates models from models.py and executes calculations through lib/ calculation modules.
"""

from typing import Dict, Optional, Any, Tuple, List
import lib
from setup_notes import (
    generate_chassis_notes,
    generate_simulation_notes,
    generate_trim_notes
)
from setup_engine import (
    resolve_slider_ranges,
    init_vehicle_and_track_specs,
    compute_baseline_suspension
)
from setup_simulation import run_trail_simulations


def _build_telemetry_dict(
    veh: Any,
    telem: Dict[str, Any],
    sim_pack: Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]],
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """Format derived physical telemetry dictionary."""
    sim, eq_proof, tire_wear, g_pred, g_prof = sim_pack
    wf_pct = f"{veh.front_weight_ratio * 100.0:.1f}% F / {veh.rear_weight_ratio * 100.0:.1f}% R"
    lat_g = g_pred['g_240'] if g_pred else round(telem['ay_est'], 2)
    actual_fr = round(params['natural_frequency_hz']['rear'] / max(0.1, params['natural_frequency_hz']['front']), 2)
    return {
        'mass_sprung_total_kg': telem['tot_s'],
        'mass_sprung_corner_f_kg': telem['c_f'],
        'mass_sprung_corner_r_kg': telem['c_r'],
        'weight_dist_pct': wf_pct,
        'tire_friction_mu': telem['mu'],
        'lateral_g_capacity': lat_g,
        'target_lltd_front_pct': telem['lltd_pct'],
        'flat_ride_frequency_ratio': actual_fr,
        'dynamic_braking_pitch_transfer_pct': telem['pitch_transfer_pct'],
        'brake_bias': params['brake_bias'],
        'high_speed_simulation': sim,
        'equilibrium_proof': eq_proof,
        'tire_wear_analysis': tire_wear,
        'dynamic_g_force': g_pred,
        'downforce_g_profile': g_prof
    }


def _assemble_final_result(
    car_data: Dict[str, Any],
    track_meta: Tuple[Optional[Dict[str, Any]], str, str],
    telem_dict: Dict[str, Any],
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """Assemble final standardized setup dictionary and derived physical telemetry."""
    track, tire, mode = track_meta
    return {
        'car': car_data,
        'track': track,
        'tire_compound': tire,
        'setup_mode': mode,
        'telemetry': telem_dict,
        'parameters': params
    }


def _apply_setup_notes(
    veh: Any,
    trk: Any,
    tire: str,
    params: Dict[str, Any],
    telem: Dict[str, Any],
    sim: Dict[str, Any],
    eq_proof: Dict[str, Any],
    sim_spd: float,
    stability: Optional[Tuple[float, float]],
    symptoms: Optional[List[str]],
    is_widebody: bool,
    is_controller: bool
) -> List[str]:
    """Compile all chassis, trim, and simulation notes."""
    fn_f = params['natural_frequency_hz']['front']
    notes = generate_chassis_notes(veh, trk, tire, fn_f, telem['is_no_aero'], is_controller, is_widebody)
    if stability or symptoms:
        notes.extend(generate_trim_notes(stability, symptoms))
    notes.extend(generate_simulation_notes(sim, eq_proof, sim_spd))
    return notes


def _prepare_setup_inputs(
    car: Dict[str, Any],
    custom_mass: Optional[int],
    custom_power: Optional[int],
    custom_torque: Optional[float],
    custom_drivetrain: Optional[str],
    custom_balance: Optional[Tuple[int, int]],
    ranges: Tuple
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Organize raw setup inputs and slider boundaries."""
    keys = ['df_front', 'df_rear', 'height_range', 'height_front', 'height_rear', 'fn_front', 'fn_rear']
    sliders = resolve_slider_ranges(car, dict(zip(keys, ranges)))
    overrides = {
        'mass': custom_mass, 'power': custom_power, 'torque': custom_torque,
        'drivetrain': custom_drivetrain, 'balance': custom_balance
    }
    return sliders, overrides


def _resolve_profile_ranges(sliders: Dict[str, Any], params: Dict[str, Any]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Extract downforce profile ranges from sliders or baseline parameters."""
    if sliders.get('df_front') and sliders.get('df_rear'):
        return sliders['df_front'], sliders['df_rear']
    df = params.get('downforce') or {}
    if 'range_f' in df and 'range_r' in df:
        try:
            rf = tuple(int(x) for x in df['range_f'].split('-'))
            rr = tuple(int(x) for x in df['range_r'].split('-'))
            return rf, rr
        except Exception:
            pass
    active_f, active_r = df.get('front', 0), df.get('rear', 0)
    return (active_f, active_f), (active_r, active_r)


def _solve_or_simulate_dynamics(
    req: lib.SolverRequest,
    solve_obj: Optional[str]
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Solve reverse setup or run baseline simulations."""
    if solve_obj:
        sol = lib.solve_optimal_setup(req)
        return sol.parameters, sol.trail_simulation, sol.equilibrium_proof, sol.tire_wear, sol.g_prediction, sol.df_g_profile
    sim, eq, wear, _ = run_trail_simulations(req.veh, req.trk, req.baseline_params, req.telem, req.sliders, req.speed_kmh, req.veh.is_widebody)
    df = (req.baseline_params['downforce']['front'], req.baseline_params['downforce']['rear']) if req.baseline_params.get('downforce') else (0, 0)
    g_pred = lib.predict_g_at_downforce(req.g_model, df)
    df_ranges = _resolve_profile_ranges(req.sliders, req.baseline_params)
    g_prof = lib.build_df_g_profile(req.g_model, df_ranges, df)
    return req.baseline_params, sim, eq, wear, g_pred, g_prof


def build_setup(
    car: Dict[str, Any],
    track: Optional[Dict[str, Any]] = None,
    tire: str = 'SS',
    custom_mass: Optional[int] = None,
    custom_power: Optional[int] = None,
    custom_torque: Optional[float] = None,
    custom_drivetrain: Optional[str] = None,
    custom_balance: Optional[Tuple[int, int]] = None,
    mode: str = 'grip',
    df_front_range: Optional[Tuple[int, int]] = None,
    df_rear_range: Optional[Tuple[int, int]] = None,
    height_range: Optional[Tuple[int, int]] = None,
    height_front_range: Optional[Tuple[int, int]] = None,
    height_rear_range: Optional[Tuple[int, int]] = None,
    fn_front_range: Optional[Tuple[float, float]] = None,
    fn_rear_range: Optional[Tuple[float, float]] = None,
    stability: Optional[Tuple[float, float]] = None,
    symptoms: Optional[List[str]] = None,
    is_widebody: bool = False,
    speed_kmh: Optional[float] = None,
    is_controller: bool = False,
    g_forces: Optional[Tuple[float, float, float]] = None,
    g_ref_df: Optional[Tuple[int, int]] = None,
    solve_objective: Optional[str] = None
) -> Dict[str, Any]:
    """Coordinate vehicle parameters and compute setup using modular lib/ calculations."""
    ranges = (df_front_range, df_rear_range, height_range, height_front_range, height_rear_range, fn_front_range, fn_rear_range)
    sliders, overrides = _prepare_setup_inputs(car, custom_mass, custom_power, custom_torque, custom_drivetrain, custom_balance, ranges)
    veh, trk, out_car = init_vehicle_and_track_specs(car, track, tire, mode, overrides, is_widebody)
    params, telem = compute_baseline_suspension(veh, trk, tire, sliders, is_widebody, is_controller, g_forces=g_forces)

    sim_spd = float(speed_kmh) if speed_kmh is not None else (240.0 if veh.is_racecar else 200.0)
    base_df = (params['downforce']['front'], params['downforce']['rear']) if params.get('downforce') else (0, 0)
    calib_ref_df = g_ref_df or base_df
    if stability or symptoms:
        params = lib.apply_closed_loop_trim(params, stability, symptoms, veh.drivetrain, veh.group)

    g_cfg = lib.GForceCalibrationInput(g_forces, calib_ref_df, telem['mu'], veh.front_weight_ratio, veh.mass_kg)
    solver_req = lib.SolverRequest(veh, trk, params, telem, sliders, lib.calibrate_g_model(g_cfg), solve_objective or 'balanced', (), sim_spd)
    params, sim, eq, wear, g_pred, g_prof = _solve_or_simulate_dynamics(solver_req, solve_objective)

    params['endurance_notes'] = _apply_setup_notes(
        veh, trk, tire, params, telem, sim, eq, sim_spd, stability, symptoms, is_widebody, is_controller
    )
    params['quick_trims'] = lib.build_quick_trims(params, drivetrain=veh.drivetrain, is_endurance=trk.is_endurance)
    telem_dict = _build_telemetry_dict(veh, telem, (sim, eq, wear, g_pred, g_prof), params)
    return _assemble_final_result(out_car, (track, tire, mode), telem_dict, params)
