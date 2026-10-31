#!/usr/bin/env python3
"""
GT7 Constrained Multi-Variable Reverse Suspension Solver
Optimizes ride height, spring frequency, downforce, and roll balance
under aerodynamic load and high-speed trail braking constraints.
"""

from dataclasses import dataclass
import copy
import math
from typing import Dict, Tuple, Any, Optional

from lib.calibrator import GForceModel, predict_g_at_downforce, build_df_g_profile
from lib.equilibrium import simulate_high_speed_trail_braking, solve_suspension_equilibrium
from lib.tire_wear import calculate_tire_wear_index


@dataclass
class SolverRequest:
    veh: Any
    trk: Any
    baseline_params: Dict[str, Any]
    telem: Dict[str, Any]
    sliders: Dict[str, Any]
    g_model: GForceModel
    objective: str = 'balanced'
    locked_params: Tuple[str, ...] = ()
    speed_kmh: float = 240.0


@dataclass
class SolverResult:
    parameters: Dict[str, Any]
    g_prediction: Dict[str, Any]
    df_g_profile: Dict[str, Any]
    trail_simulation: Dict[str, Any]
    equilibrium_proof: Dict[str, Any]
    tire_wear: Dict[str, Any]
    objective_score: float


def _optimize_downforce(req: SolverRequest, params: Dict[str, Any]) -> None:
    """Optimize aerodynamic downforce levels according to objective targets."""
    if 'downforce' in req.locked_params or not params.get('downforce'):
        return
    if not req.sliders.get('df_front') or not req.sliders.get('df_rear'):
        return
    min_f, max_f = req.sliders['df_front']
    min_r, max_r = req.sliders['df_rear']
    span = 0.90 if req.objective == 'max_grip' else (0.40 if req.objective == 'min_tire_wear' else 0.65)
    df_r = int(min_r + span * (max_r - min_r))
    f_share = max(0.32, min(0.46, 1.0 - req.veh.front_weight_ratio))
    df_f = int((f_share / max(0.01, 1.0 - f_share)) * df_r)
    params['downforce']['front'] = max(min_f, min(max_f, df_f))
    params['downforce']['rear'] = max(min_r, min(max_r, df_r))


def _optimize_frequencies(req: SolverRequest, params: Dict[str, Any]) -> None:
    """Adjust natural frequencies based on grip vs tire wear objective."""
    if 'natural_frequency_hz' in req.locked_params:
        return
    min_f, max_f = req.sliders.get('fn_front') or (1.5, 3.5)
    min_r, max_r = req.sliders.get('fn_rear') or (1.5, 3.5)
    delta = 0.15 if req.objective == 'max_grip' else (-0.15 if req.objective == 'min_tire_wear' else 0.0)
    fn_f = max(min_f, min(max_f, round(params['natural_frequency_hz']['front'] + delta, 2)))
    fr_ratio = req.telem.get('fr_ratio') or 1.04
    fn_r = max(min_r, min(max_r, round(fn_f * fr_ratio, 2)))
    params['natural_frequency_hz']['front'] = fn_f
    params['natural_frequency_hz']['rear'] = fn_r


def _optimize_camber(req: SolverRequest, params: Dict[str, Any]) -> None:
    """Tune negative camber to balance cornering bite against tire abrasion."""
    if 'camber_deg' in req.locked_params:
        return
    if req.objective == 'min_tire_wear':
        params['camber_deg']['front'] = -2.0
        params['camber_deg']['rear'] = -1.0
    elif req.objective == 'max_grip':
        params['camber_deg']['front'] = -2.8
        params['camber_deg']['rear'] = -1.5


def _resolve_height_bounds(req: SolverRequest) -> Tuple[int, int, int, int]:
    """Extract physical ride height boundaries from vehicle sliders."""
    s = req.sliders
    min_f = s['height_front'][0] if s.get('height_front') else (s['height_range'][0] if s.get('height_range') else 90)
    max_f = s['height_front'][1] if s.get('height_front') else (s['height_range'][1] if s.get('height_range') else 160)
    min_r = s['height_rear'][0] if s.get('height_rear') else (s['height_range'][0] if s.get('height_range') else 90)
    max_r = s['height_rear'][1] if s.get('height_rear') else (s['height_range'][1] if s.get('height_range') else 160)
    return min_f, max_f, min_r, max_r


def _simulate_trail(req: SolverRequest, params: Dict[str, Any], min_rh_f: int) -> Dict[str, Any]:
    """Execute stroke compression simulation for candidate setup."""
    df_f = params['downforce']['front'] if params.get('downforce') else 0
    df_r = params['downforce']['rear'] if params.get('downforce') else 0
    return simulate_high_speed_trail_braking(
        speed_kmh=req.speed_kmh, mass_kg=req.veh.mass_kg, corner_front_kg=req.telem['c_f'],
        corner_rear_kg=req.telem['c_r'], wf=req.veh.front_weight_ratio, hcg_m=req.veh.hcg_m,
        wheelbase_m=req.veh.wheelbase_m, track_width_m=req.veh.track_width_m, mu=req.telem['mu'],
        rh_front_mm=params['ride_height_mm']['front'], rh_rear_mm=params['ride_height_mm']['rear'],
        fn_front_hz=params['natural_frequency_hz']['front'], fn_rear_hz=params['natural_frequency_hz']['rear'],
        arb_front=params['anti_roll_bar']['front'], arb_rear=params['anti_roll_bar']['rear'],
        df_front=df_f, df_rear=df_r, is_widebody=req.veh.is_widebody, height_min_front_mm=min_rh_f
    )


def _step_ride_heights(params: Dict[str, Any], sim: Dict[str, Any], bounds: Tuple[int, int, int, int]) -> None:
    """Step ride heights upward to relieve bump stop collision and stroke deficit."""
    bump = math.ceil(max(12.0 - sim['dynamic_outside_front_clearance_mm'], 2.0))
    params['ride_height_mm']['front'] = min(bounds[1], params['ride_height_mm']['front'] + bump)
    params['ride_height_mm']['rear'] = min(bounds[3], max(params['ride_height_mm']['front'] + 8, params['ride_height_mm']['rear']))


def _optimize_ride_heights(req: SolverRequest, params: Dict[str, Any], bounds: Tuple[int, int, int, int]) -> Dict[str, Any]:
    """Solve ride heights iteratively until dynamic bottoming is eliminated."""
    sim = _simulate_trail(req, params, bounds[0])
    if 'ride_height_mm' in req.locked_params:
        return sim
    for _ in range(25):
        if not sim['bottoming_or_fender_hit'] and sim['dynamic_outside_front_clearance_mm'] >= 10.0:
            break
        _step_ride_heights(params, sim, bounds)
        sim = _simulate_trail(req, params, bounds[0])
    if params['ride_height_mm']['rear'] <= params['ride_height_mm']['front']:
        params['ride_height_mm']['rear'] = min(bounds[3], params['ride_height_mm']['front'] + 8)
    return sim


def _run_proofs_and_wear(req: SolverRequest, params: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Compute equilibrium verification proof and tire wear index."""
    df_f = params['downforce']['front'] if params.get('downforce') else 0
    df_r = params['downforce']['rear'] if params.get('downforce') else 0
    eq = solve_suspension_equilibrium(
        mass_kg=req.veh.mass_kg, front_ratio=req.veh.front_weight_ratio, power_hp=req.veh.power_hp,
        torque_nm=req.veh.torque_nm, drivetrain=req.veh.drivetrain, hcg_m=req.veh.hcg_m,
        wheelbase_m=req.veh.wheelbase_m, track_width_m=req.veh.track_width_m, mu=req.telem['mu'],
        fn_f=params['natural_frequency_hz']['front'], fn_r=params['natural_frequency_hz']['rear'],
        arb_f=params['anti_roll_bar']['front'], arb_r=params['anti_roll_bar']['rear'],
        df_f=df_f, df_r=df_r, height_range=req.sliders.get('height_range'),
        height_front_range=req.sliders.get('height_front'), height_rear_range=req.sliders.get('height_rear'),
        speed_kmh=req.speed_kmh, is_widebody=req.veh.is_widebody, group=req.veh.group,
        body_style=req.veh.body_style, bumpiness=req.trk.bumpiness, is_dirt=req.trk.is_dirt
    )
    tw = calculate_tire_wear_index(
        fn_hz_f=params['natural_frequency_hz']['front'], fn_hz_r=params['natural_frequency_hz']['rear'],
        camber_f=params['camber_deg']['front'], camber_r=params['camber_deg']['rear'],
        toe_f=params['toe_angle']['front'], toe_r=params['toe_angle']['rear'],
        ptw=req.veh.power_to_weight, is_endurance=req.trk.is_endurance
    )
    return eq, tw


def _calculate_score(objective: str, g_240: float, front_wear: float) -> float:
    """Evaluate scalar objective score for optimal setup comparison."""
    if objective == 'max_grip':
        return round(g_240, 3)
    if objective == 'min_tire_wear':
        return round(-front_wear, 3)
    return round(g_240 - 0.25 * front_wear, 3)


def solve_optimal_setup(request: SolverRequest) -> SolverResult:
    """Solve multi-variable suspension parameters satisfying aero and clearance constraints."""
    params = copy.deepcopy(request.baseline_params)
    _optimize_downforce(request, params)
    _optimize_frequencies(request, params)
    _optimize_camber(request, params)
    bounds = _resolve_height_bounds(request)
    sim = _optimize_ride_heights(request, params, bounds)
    eq, tw = _run_proofs_and_wear(request, params)
    active_df = (params['downforce']['front'], params['downforce']['rear']) if params.get('downforce') else (0, 0)
    g_pred = predict_g_at_downforce(request.g_model, active_df)
    df_ranges = (request.sliders.get('df_front') or (0, 0), request.sliders.get('df_rear') or (0, 0))
    df_profile = build_df_g_profile(request.g_model, df_ranges, active_df)
    score = _calculate_score(request.objective, g_pred['g_240'], tw['front_wear_factor'])
    return SolverResult(params, g_pred, df_profile, sim, eq, tw, score)
