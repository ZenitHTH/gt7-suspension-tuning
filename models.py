#!/usr/bin/env python3
"""
GT7 Race-Engineering Domain Data Models (Canonical Root Reference)
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Any
import constants


def _resolve_drivetrain(ov: Dict[str, Any], car_data: Dict[str, Any]) -> str:
    """Normalize vehicle drivetrain string."""
    raw_dt = str(ov.get('drivetrain') or car_data.get('drivetrain') or 'FR').upper()
    return 'AWD' if raw_dt in ['4WD', '4X4', 'AWD'] else raw_dt


def _resolve_group(car_data: Dict[str, Any]) -> str:
    """Normalize car group representation."""
    raw_grp = str(car_data.get('group', 'Road Car')).strip()
    mapping = {'X': 'Gr.X', 'B': 'Gr.B', 'N': 'Road Car'}
    return mapping.get(raw_grp, raw_grp)


def _resolve_weight_fraction(ov: Dict[str, Any], car_data: Dict[str, Any]) -> float:
    """Calculate front weight distribution ratio."""
    custom_bal = ov.get('balance')
    if custom_bal and isinstance(custom_bal, (list, tuple)) and len(custom_bal) >= 1:
        return float(custom_bal[0]) / 100.0
    return float(car_data.get('balance', {}).get('front_pct') or 50) / 100.0


def _resolve_engine_specs(ov: Dict[str, Any], car_data: Dict[str, Any]) -> Tuple[float, float, str]:
    """Resolve horsepower, torque, and engine aspiration."""
    engine = car_data.get('engine', {})
    power = float(ov.get('power') or engine.get('power_hp') or 300)
    torque = float(ov.get('torque') or engine.get('torque_nm') or (power * 1.12))
    aspiration = str(engine.get('aspiration') or 'Naturally-Aspirated')
    return power, torque, aspiration


def _resolve_vehicle_class(name: str, mass: float, group: str, body_style: str) -> Tuple[bool, bool]:
    """Determine whether vehicle is classified as racecar or ultralight track special."""
    is_race = any(g in group for g in ['Gr.1', 'Gr.2', 'Gr.3', 'Gr.4', 'Gr.X']) or ('Racecar' in body_style)
    is_ultra = (not is_race) and (mass <= 750 or any(k in name for k in ['Caterham', 'Seven', 'Mono', 'Radical', '2X', 'Kart']))
    return is_race, is_ultra


def _resolve_dimensions_and_cg(
    car_data: Dict[str, Any],
    group: str,
    body_style: str
) -> Tuple[float, float, float, float, float, float]:
    """Calculate chassis physical dimensions, wheelbase, track width, and center of gravity height."""
    dim = car_data.get('dimensions_mm', {})
    length_m = float(dim.get('length', 4500)) / 1000.0
    width_m = float(dim.get('width', 1800)) / 1000.0
    height_m = float(dim.get('height', 1300)) / 1000.0

    wheelbase_m = length_m * constants.CHASSIS_RATIOS['wheelbase_from_length']
    track_width_m = width_m * constants.CHASSIS_RATIOS['track_width_from_width']

    if any(g in group for g in ['Gr.1', 'Gr.2', 'Gr.3', 'Gr.X']):
        cg_ratio = constants.CG_HEIGHT_RATIOS['prototype_racecar']
    elif body_style in ['SUV', 'Pickup']:
        cg_ratio = constants.CG_HEIGHT_RATIOS['suv_pickup']
    else:
        cg_ratio = constants.CG_HEIGHT_RATIOS['standard_road']
    hcg_m = height_m * cg_ratio
    return length_m, width_m, height_m, wheelbase_m, track_width_m, hcg_m


@dataclass(frozen=True)
class VehicleSpec:
    """Immutable representation of physical vehicle parameters."""
    name: str
    mass_kg: float
    front_weight_ratio: float
    drivetrain: str
    group: str
    body_style: str
    power_hp: float
    torque_nm: float
    length_m: float
    width_m: float
    height_m: float
    wheelbase_m: float
    track_width_m: float
    hcg_m: float
    is_widebody: bool = False
    is_racecar: bool = False
    is_ultralight: bool = False
    aspiration: str = 'Naturally-Aspirated'

    @property
    def rear_weight_ratio(self) -> float:
        return 1.0 - self.front_weight_ratio

    @property
    def power_to_weight(self) -> float:
        return self.power_hp / (self.mass_kg / 1000.0) if self.mass_kg > 0 else 200.0

    @classmethod
    def from_dict(
        cls,
        car_data: Dict[str, Any],
        custom_overrides: Optional[Dict[str, Any]] = None,
        is_widebody: bool = False
    ) -> 'VehicleSpec':
        ov = custom_overrides or {}
        name = car_data.get('name', 'Unknown Vehicle')
        mass = float(ov.get('mass') or car_data.get('mass_kg') or 1350)
        drivetrain = _resolve_drivetrain(ov, car_data)
        group, body_style = _resolve_group(car_data), str(car_data.get('body_style') or 'Coupe')
        power, torque, aspiration = _resolve_engine_specs(ov, car_data)
        wf = _resolve_weight_fraction(ov, car_data)
        l_m, w_m, h_m, wb_m, tw_m, hcg_m = _resolve_dimensions_and_cg(car_data, group, body_style)
        is_race, is_ultra = _resolve_vehicle_class(name, mass, group, body_style)

        return cls(
            name=name, mass_kg=mass, front_weight_ratio=wf, drivetrain=drivetrain,
            group=group, body_style=body_style, power_hp=power, torque_nm=torque,
            length_m=l_m, width_m=w_m, height_m=h_m, wheelbase_m=wb_m, track_width_m=tw_m,
            hcg_m=hcg_m, is_widebody=is_widebody, is_racecar=is_race,
            is_ultralight=is_ultra, aspiration=aspiration
        )


def _is_track_oval(t_name_lower: str) -> bool:
    """Detect whether circuit has oval topology."""
    has_oval_name = any(k in t_name_lower for k in ['blue moon', 'daytona', 'route x', 'speedway'])
    has_road_infield = any(k in t_name_lower for k in ['infield', 'road course'])
    return has_oval_name and not has_road_infield


def _is_track_endurance(mode: str, tire: str, t_name_lower: str) -> bool:
    """Determine whether setup should target endurance tire conservation."""
    if mode == 'endurance':
        return True
    if mode == 'grip':
        has_compound = tire in ['RH', 'RM']
        has_circuit = any(k in t_name_lower for k in ['spa', 'sarthe', 'nurburgring', 'interlagos', 'suzuka', 'panorama', '24h', '1h'])
        return has_compound or has_circuit
    return False


@dataclass(frozen=True)
class TrackSpec:
    """Immutable representation of circuit characteristics and session mode."""
    name: str = 'General Balanced Circuit'
    category: str = 'circuit'
    bumpiness: str = 'medium'
    elevation_diff_m: float = 0.0
    downforce_demand: str = 'medium'
    longest_straight_m: float = 0.0
    is_oval: bool = False
    is_dirt: bool = False
    is_wet: bool = False
    is_endurance: bool = False

    @classmethod
    def from_dict(
        cls,
        track_data: Optional[Dict[str, Any]] = None,
        mode: str = 'grip',
        tire: str = 'SS'
    ) -> 'TrackSpec':
        t = track_data or {}
        name = str(t.get('name') or 'General Balanced Circuit')
        t_name_lower = name.lower()

        return cls(
            name=name,
            category=str(t.get('category') or 'circuit'),
            bumpiness=str(t.get('bumpiness') or 'medium'),
            elevation_diff_m=float(t.get('elevation_diff_m') or 0.0),
            downforce_demand=str(t.get('downforce_demand') or 'medium'),
            longest_straight_m=float(t.get('longest_straight_m') or 0.0),
            is_oval=_is_track_oval(t_name_lower),
            is_dirt=(mode == 'dirt') or ('dirt' in str(t.get('category') or '').lower()),
            is_wet=(mode == 'wet'),
            is_endurance=_is_track_endurance(mode, tire, t_name_lower)
        )
