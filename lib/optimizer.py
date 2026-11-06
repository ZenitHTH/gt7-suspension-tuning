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
from lib.grip import calculate_grip_check


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
    grip_check: Optional[Dict] = None


def _resolve_df_ranges(sliders: Dict[str, Any], df: Dict[str, Any]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Extract downforce min/max boundaries from sliders or baseline parameters."""
    if sliders.get('df_front') and sliders.get('df_rear'):
        return sliders['df_front'], sliders['df_rear']
    if 'range_f' in df and 'range_r' in df:
        return tuple(int(x) for x in df['range_f'].split('-')), tuple(int(x) for x in df['range_r'].split('-'))
    f, r = df.get('front', 0), df.get('rear', 0)
    return (f, f), (r, r)


def _optimize_downforce(req: SolverRequest, params: Dict[str, Any], span: Optional[float] = None) -> None:
    """Optimize aerodynamic downforce levels according to objective targets."""
    if 'downforce' in req.locked_params or not params.get('downforce'):
        return
    (min_f, max_f), (min_r, max_r) = _resolve_df_ranges(req.sliders, params['downforce'])
    if (max_f - min_f) <= 0 and (max_r - min_r) <= 0:
        return
    if span is None:
        span = 0.90 if req.objective == 'max_grip' else (0.40 if req.objective == 'min_tire_wear' else 0.65)
    df_r = int(min_r + span * (max_r - min_r))
    f_share = max(0.35, min(0.48, 0.25 + 0.35 * req.veh.front_weight_ratio))
    df_f = int((f_share / max(0.01, 1.0 - f_share)) * df_r)
    params['downforce']['front'] = max(min_f, min(max_f, df_f))
    params['downforce']['rear'] = max(min_r, min(max_r, df_r))


def _optimize_frequencies(req: SolverRequest, params: Dict[str, Any], delta: Optional[float] = None) -> None:
    """Adjust natural frequencies based on grip vs tire wear objective."""
    if 'natural_frequency_hz' in req.locked_params:
        return
    min_f, max_f = req.sliders.get('fn_front') or (1.5, 3.5)
    min_r, max_r = req.sliders.get('fn_rear') or (1.5, 3.5)
    if delta is None:
        delta = 0.15 if req.objective == 'max_grip' else (-0.15 if req.objective == 'min_tire_wear' else 0.0)
    fn_f = max(min_f, min(max_f, round(params['natural_frequency_hz']['front'] + delta, 2)))
    fr_ratio = req.telem.get('fr_ratio') or 1.04
    fn_r = max(min_r, min(max_r, round(fn_f * fr_ratio, 2)))
    params['natural_frequency_hz']['front'] = fn_f
    params['natural_frequency_hz']['rear'] = fn_r


def _optimize_camber(req: SolverRequest, params: Dict[str, Any],
                     delta_f: Optional[float] = None, delta_r: Optional[float] = None) -> None:
    """Tune negative camber to balance cornering bite against tire abrasion."""
    if 'camber_deg' in req.locked_params or req.trk.is_dirt or req.trk.is_wet:
        return
    if delta_f is None:
        delta_f = 0.4 if req.objective == 'max_grip' else (-0.4 if req.objective == 'min_tire_wear' else 0.0)
    if delta_r is None:
        delta_r = 0.2 if req.objective == 'max_grip' else (-0.2 if req.objective == 'min_tire_wear' else 0.0)
    params['camber_deg']['front'] = round(min(-1.4, params['camber_deg']['front'] - delta_f), 1)
    params['camber_deg']['rear'] = round(min(-0.8, params['camber_deg']['rear'] - delta_r), 1)


def _resolve_height_bounds(req: SolverRequest) -> Tuple[int, int, int, int]:
    """Extract physical ride height boundaries from vehicle sliders or archetype."""
    s, v = req.sliders, req.veh
    grp = getattr(v, 'group', 'Road Car')
    if getattr(v, 'is_racecar', False) or grp in ['Gr.1', 'Gr.2', 'Gr.3', 'Gr.4', 'Gr.X']:
        b = 50 if grp in ['Gr.1', 'Gr.X'] else (55 if grp in ['Gr.2', 'Gr.3'] else 70)
        d_min, d_max = (b, b), (b + 40, b + 45)
    else:
        d_min, d_max = ((55, 55), (100, 105)) if getattr(v, 'is_ultralight', False) else ((90, 90), (160, 160))
    hf = s.get('height_front') or s.get('height_range') or (d_min[0], d_max[0])
    hr = s.get('height_rear') or s.get('height_range') or (d_min[1], d_max[1])
    return hf[0], hf[1], hr[0], hr[1]


def _simulate_trail(req: SolverRequest, params: Dict[str, Any], min_rh_f: int) -> Dict[str, Any]:
    """Execute stroke compression simulation for candidate setup."""
    df_f = params['downforce']['front'] if params.get('downforce') else 0
    df_r = params['downforce']['rear'] if params.get('downforce') else 0
    return simulate_high_speed_trail_braking(
        speed_kmh=req.speed_kmh, mass_kg=req.veh.mass_kg, corner_front_kg=req.telem['c_f'],
        corner_rear_kg=req.telem['c_r'], wf=req.veh.front_weight_ratio, hcg_m=req.veh.hcg_m,
        wheelbase_m=req.veh.wheelbase_m, track_width_m=req.veh.track_width_m, mu=req.telem.get('mu_braking', req.telem['mu']),
        rh_front_mm=params['ride_height_mm']['front'], rh_rear_mm=params['ride_height_mm']['rear'],
        fn_front_hz=params['natural_frequency_hz']['front'], fn_rear_hz=params['natural_frequency_hz']['rear'],
        arb_front=params['anti_roll_bar']['front'], arb_rear=params['anti_roll_bar']['rear'],
        df_front=df_f, df_rear=df_r, is_widebody=req.veh.is_widebody, height_min_front_mm=min_rh_f
    )


def _step_ride_heights(
    params: Dict[str, Any],
    sim: Dict[str, Any],
    limits_and_rake: Tuple[int, int, int]
) -> None:
    """Step ride heights upward to relieve bump stop collision while preserving target rake."""
    max_f, max_r, rake_delta = limits_and_rake
    bump = math.ceil(max(12.0 - sim['dynamic_outside_front_clearance_mm'], 2.0))
    params['ride_height_mm']['front'] = min(max_f, params['ride_height_mm']['front'] + bump)
    params['ride_height_mm']['rear'] = min(max_r, max(params['ride_height_mm']['front'] + rake_delta, params['ride_height_mm']['rear']))


def _optimize_ride_heights(req: SolverRequest, params: Dict[str, Any], bounds: Tuple[int, int, int, int]) -> Dict[str, Any]:
    """Solve ride heights iteratively until dynamic bottoming is eliminated."""
    sim = _simulate_trail(req, params, bounds[0])
    if 'ride_height_mm' in req.locked_params:
        return sim
    wf = req.veh.front_weight_ratio
    rake_delta = 22 if req.telem.get('is_no_aero') else max(6, min(12, round(7.0 + 15.0 * max(0.0, wf - 0.50))))
    for _ in range(25):
        if not sim['bottoming_or_fender_hit'] and sim['dynamic_outside_front_clearance_mm'] >= 10.0:
            break
        _step_ride_heights(params, sim, (bounds[1], bounds[3], rake_delta))
        sim = _simulate_trail(req, params, bounds[0])
    if params['ride_height_mm']['rear'] <= params['ride_height_mm']['front']:
        params['ride_height_mm']['rear'] = min(bounds[3], params['ride_height_mm']['front'] + rake_delta)
        sim = _simulate_trail(req, params, bounds[0])
    return sim


def _solve_eq(req: SolverRequest, params: Dict[str, Any]) -> Dict[str, Any]:
    """Compute suspension equilibrium proof for optimal parameters."""
    df_f = params['downforce']['front'] if params.get('downforce') else 0
    df_r = params['downforce']['rear'] if params.get('downforce') else 0
    s = req.sliders
    return solve_suspension_equilibrium(
        mass_kg=req.veh.mass_kg, front_ratio=req.veh.front_weight_ratio, power_hp=req.veh.power_hp,
        torque_nm=req.veh.torque_nm, drivetrain=req.veh.drivetrain, hcg_m=req.veh.hcg_m,
        wheelbase_m=req.veh.wheelbase_m, track_width_m=req.veh.track_width_m, mu=req.telem.get('mu_braking', req.telem['mu']),
        fn_f=params['natural_frequency_hz']['front'], fn_r=params['natural_frequency_hz']['rear'],
        arb_f=params['anti_roll_bar']['front'], arb_r=params['anti_roll_bar']['rear'],
        df_f=df_f, df_r=df_r, height_range=s.get('height_range'),
        height_front_range=s.get('height_front'), height_rear_range=s.get('height_rear'),
        speed_kmh=req.speed_kmh, is_widebody=req.veh.is_widebody, group=req.veh.group,
        body_style=req.veh.body_style, bumpiness=req.trk.bumpiness, is_dirt=req.trk.is_dirt
    )


def _eval_wear(req: SolverRequest, params: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate tire wear index for optimal setup."""
    return calculate_tire_wear_index(
        fn_hz_f=params['natural_frequency_hz']['front'], fn_hz_r=params['natural_frequency_hz']['rear'],
        camber_f=params['camber_deg']['front'], camber_r=params['camber_deg']['rear'],
        toe_f=params['toe_angle']['front'], toe_r=params['toe_angle']['rear'],
        ptw=req.veh.power_to_weight, is_endurance=req.trk.is_endurance
    )


def _calculate_score(objective: str, g_240: float, front_wear: float,
                     grip_min_margin: Optional[float] = None) -> float:
    """Evaluate scalar objective score for optimal setup comparison."""
    weights = {'max_grip': g_240, 'min_tire_wear': -front_wear}
    score = weights.get(objective, g_240 - 0.25 * front_wear)
    if grip_min_margin is not None and grip_min_margin < 1.0:
        score -= 0.20 * (1.0 - grip_min_margin)
    return round(score, 3)


def _evaluate(req: SolverRequest, params: Dict[str, Any], sim: Dict[str, Any],
              bounds: Tuple[int, int, int, int]) -> SolverResult:
    """Build the full SolverResult from one evaluated candidate setup."""
    eq, tw = _solve_eq(req, params), _eval_wear(req, params)
    active_df = (params['downforce']['front'], params['downforce']['rear']) if params.get('downforce') else (0, 0)
    g_pred = predict_g_at_downforce(req.g_model, active_df)
    # Friction anchor is the G-model's 60 km/h point (downforce ~0 there);
    # everything above it at 240 km/h is carried by the aero system, not the
    # tire friction budget.
    aero_g = max(0.0, g_pred['g_240'] - req.g_model.base_g[0])
    g_check = calculate_grip_check(req.veh, req.telem['mu'], g_pred['g_240'],
                                   req.telem.get('lltd_pct', 50.0) / 100.0,
                                   aero_g=aero_g, mu_is_measured=req.g_model.is_calibrated)
    df_ranges = _resolve_df_ranges(req.sliders, params.get('downforce') or {})
    df_profile = build_df_g_profile(req.g_model, df_ranges, active_df)
    score = _calculate_score(req.objective, g_pred['g_240'], tw['front_wear_factor'],
                             g_check['margins']['min'])
    return SolverResult(params, g_pred, df_profile, sim, eq, tw, score, g_check)


def _candidate_grid(req: SolverRequest) -> list:
    """Enumerate (downforce_span, fn_delta, camber_delta) candidates deterministically.

    Up to 36 candidates (6 spans x 3 fn deltas x 2 camber deltas); span 1.00 lets
    max_grip reach the full downforce slider. Locked axes collapse to a single
    [None] / [(0.0, 0.0)] entry.
    """
    locked = req.locked_params
    spans = ([0.30, 0.45, 0.60, 0.75, 0.90, 1.00]
             if 'downforce' not in locked else [None])
    fn_deltas = ([-0.15, 0.0, 0.15]
                 if 'natural_frequency_hz' not in locked else [None])
    camber_deltas = ([(0.0, 0.0), (0.4, 0.2)]
                     if 'camber_deg' not in locked and not req.trk.is_dirt and not req.trk.is_wet
                     else [(0.0, 0.0)])
    return [(s, f, c) for s in spans for f in fn_deltas for c in camber_deltas]


def _better(a: SolverResult, b: SolverResult, sim_a: Dict[str, Any], sim_b: Dict[str, Any]) -> bool:
    """Candidate a beats incumbent b: strictly higher score, or score within 0.001
    with larger dynamic front clearance (deterministic first-wins on exact ties)."""
    if abs(a.objective_score - b.objective_score) < 0.001:
        return sim_a['dynamic_outside_front_clearance_mm'] > sim_b['dynamic_outside_front_clearance_mm']
    return a.objective_score > b.objective_score


def _run_candidate(req: SolverRequest, span, fn_delta, camber_tuple,
                   bounds: Tuple[int, int, int, int]) -> Tuple[SolverResult, Dict[str, Any]]:
    """Apply one candidate's offsets to a fresh baseline copy and evaluate it."""
    params = copy.deepcopy(req.baseline_params)
    if span is not None:
        _optimize_downforce(req, params, span=span)
    if fn_delta is not None:
        _optimize_frequencies(req, params, delta=fn_delta)
    if camber_tuple != (0.0, 0.0):
        _optimize_camber(req, params, delta_f=camber_tuple[0], delta_r=camber_tuple[1])
    sim = _optimize_ride_heights(req, params, bounds)
    return _evaluate(req, params, sim, bounds), sim


def _refine(req: SolverRequest, best: SolverResult, best_sim: Dict[str, Any],
            best_meta: Tuple, bounds: Tuple[int, int, int, int]):
    """One local pass: +/-0.05 span and +/-0.05 fn around the grid winner.

    Returns (result, sim, meta) for the best neighbor that strictly beats the
    incumbent, or None.
    """
    span, fn_delta, camber_tuple = best_meta
    neighbors = []
    if span is not None and 'downforce' not in req.locked_params:
        for s in (round(span - 0.05, 2), round(span + 0.05, 2)):
            if 0.30 <= s <= 1.00 and abs(s - span) > 1e-9:
                neighbors.append((s, fn_delta))
    if 'natural_frequency_hz' not in req.locked_params:
        for d in ((fn_delta - 0.05) if fn_delta is not None else -0.05,
                  (fn_delta + 0.05) if fn_delta is not None else 0.05):
            neighbors.append((span, round(d, 3)))
    best_neighbor = None
    for n_span, n_fn in neighbors:
        result, sim = _run_candidate(req, n_span, n_fn, camber_tuple, bounds)
        if result.objective_score > best.objective_score + 1e-4:
            if best_neighbor is None or _better(result, best_neighbor[0], sim, best_neighbor[1]):
                best_neighbor = (result, sim, (n_span, n_fn, camber_tuple))
    return best_neighbor


def solve_optimal_setup(request: SolverRequest) -> SolverResult:
    """Solve multi-variable suspension parameters satisfying aero and clearance constraints."""
    bounds = _resolve_height_bounds(request)
    best, best_sim, best_meta = None, None, None
    for span, fn_delta, camber_tuple in _candidate_grid(request):
        result, sim = _run_candidate(request, span, fn_delta, camber_tuple, bounds)
        if best is None or _better(result, best, sim, best_sim):
            best, best_sim, best_meta = result, sim, (span, fn_delta, camber_tuple)
    refined = _refine(request, best, best_sim, best_meta, bounds)
    if refined is not None:
        best, best_sim, best_meta = refined
    return best
