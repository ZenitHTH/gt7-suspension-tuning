#!/usr/bin/env python3
"""
GT7 Setup Simulation Runner
Executes high-speed trail-braking simulation, equilibrium solver, and tire wear analysis.
"""

from typing import Dict, Tuple, Optional, Any
from models import VehicleSpec, TrackSpec
import lib


def _resolve_min_front_height(veh: VehicleSpec, sliders: Dict[str, Any]) -> int:
    """Resolve physical front slider lower bound."""
    if sliders['height_front']:
        return sliders['height_front'][0]
    if sliders['height_range']:
        return sliders['height_range'][0]
    return 45 if veh.is_racecar else 90


def _simulate_trail_braking(
    veh: VehicleSpec,
    params: Dict[str, Any],
    telem: Dict[str, Any],
    h_min_f: int,
    sim_spd: float,
    is_widebody: bool
) -> Dict[str, Any]:
    """Execute dynamic stroke compression simulation."""
    return lib.simulate_high_speed_trail_braking(
        speed_kmh=sim_spd, mass_kg=veh.mass_kg, corner_front_kg=telem['c_f'], corner_rear_kg=telem['c_r'],
        wf=veh.front_weight_ratio, hcg_m=veh.hcg_m, wheelbase_m=veh.wheelbase_m, track_width_m=veh.track_width_m,
        mu=telem.get('mu_braking', telem['mu']), rh_front_mm=params['ride_height_mm']['front'], rh_rear_mm=params['ride_height_mm']['rear'],
        fn_front_hz=params['natural_frequency_hz']['front'], fn_rear_hz=params['natural_frequency_hz']['rear'],
        arb_front=params['anti_roll_bar']['front'], arb_rear=params['anti_roll_bar']['rear'],
        df_front=params['downforce']['front'] if params.get('downforce') else 0,
        df_rear=params['downforce']['rear'] if params.get('downforce') else 0,
        is_widebody=is_widebody, height_min_front_mm=h_min_f
    )


def _solve_equilibrium(
    veh: VehicleSpec,
    trk: TrackSpec,
    params: Dict[str, Any],
    telem: Dict[str, Any],
    sliders: Dict[str, Any],
    sim_spd: float,
    is_widebody: bool
) -> Dict[str, Any]:
    """Execute physical equilibrium solver."""
    return lib.solve_suspension_equilibrium(
        mass_kg=veh.mass_kg, front_ratio=veh.front_weight_ratio, power_hp=veh.power_hp, torque_nm=veh.torque_nm,
        drivetrain=veh.drivetrain, hcg_m=veh.hcg_m, wheelbase_m=veh.wheelbase_m, track_width_m=veh.track_width_m,
        mu=telem['mu'], fn_f=params['natural_frequency_hz']['front'], fn_r=params['natural_frequency_hz']['rear'],
        arb_f=params['anti_roll_bar']['front'], arb_r=params['anti_roll_bar']['rear'],
        df_f=params['downforce']['front'] if params.get('downforce') else 0,
        df_r=params['downforce']['rear'] if params.get('downforce') else 0,
        height_range=sliders['height_range'], height_front_range=sliders['height_front'], height_rear_range=sliders['height_rear'],
        speed_kmh=sim_spd, is_widebody=is_widebody, group=veh.group, body_style=veh.body_style,
        bumpiness=trk.bumpiness, is_dirt=trk.is_dirt
    )


def run_trail_simulations(
    veh: VehicleSpec,
    trk: TrackSpec,
    params: Dict[str, Any],
    telem: Dict[str, Any],
    sliders: Dict[str, Any],
    speed_kmh: Optional[float],
    is_widebody: bool
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], float]:
    """Execute high-speed trail-braking simulation, equilibrium solver, and tire wear analysis."""
    sim_spd = float(speed_kmh) if speed_kmh is not None else (240.0 if veh.is_racecar else 200.0)
    h_min_f = _resolve_min_front_height(veh, sliders)

    sim = _simulate_trail_braking(veh, params, telem, h_min_f, sim_spd, is_widebody)
    eq_proof = _solve_equilibrium(veh, trk, params, telem, sliders, sim_spd, is_widebody)
    tire_wear = lib.calculate_tire_wear_index(
        fn_hz_f=params['natural_frequency_hz']['front'], fn_hz_r=params['natural_frequency_hz']['rear'],
        camber_f=params['camber_deg']['front'], camber_r=params['camber_deg']['rear'],
        toe_f=params['toe_angle']['front'], toe_r=params['toe_angle']['rear'],
        ptw=veh.power_to_weight, is_endurance=trk.is_endurance
    )
    return sim, eq_proof, tire_wear, sim_spd
