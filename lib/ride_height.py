#!/usr/bin/env python3
"""
GT7 Ride Height & Ground Clearance Module
Calculates front and rear ground clearance (ride height) and positive rake angle (mm)
from vehicle geometry, aero requirements, and track characteristics.
"""

from typing import Tuple, Optional
from lib.formulas import normalize_group


def _calculate_ride_height_buffers(
    is_dirt: bool,
    elevation_diff_m: float,
    is_widebody: bool,
    is_controller: bool,
    is_racecar: bool
) -> int:
    """Calculate chassis clearance buffers for elevation, widebody, and controller inputs."""
    if is_dirt:
        return 0
    elev_buf = 4 if (elevation_diff_m or 0.0) >= 50.0 else 0
    wide_buf = 5 if is_widebody else 0
    ctrl_buf = 4 if (is_controller and not is_racecar) else 0
    return elev_buf + wide_buf + ctrl_buf


def _calculate_rake(wf: float, is_no_aero_rake: bool) -> int:
    """Calculate static rake delta (mm) between front and rear axle."""
    if is_no_aero_rake:
        return 22
    if wf <= 0.53:
        return 7
    return min(12, round(7.0 + 15.0 * (wf - 0.50)))


def _calculate_ranged_ride_height(
    h_min_f: int,
    h_max_f: int,
    h_min_r: int,
    h_max_r: int,
    bumpiness: str,
    is_racecar: bool,
    is_ultralight: bool,
    total_buf: int,
    rake: int,
    is_widebody: bool = False
) -> Tuple[int, int]:
    """Calculate ride height when in-game slider ranges are specified."""
    margin = 3 if is_racecar or is_ultralight else (12 if bumpiness == 'high' else 10)
    base_f = min(h_max_f, h_min_f + margin + total_buf)
    r_margin = margin + (5 if is_widebody else 0)
    base_r = min(h_max_r, max(h_min_r + r_margin, base_f + rake))
    return base_f, base_r


def _calculate_archetype_ride_height(
    grp: str,
    bumpiness: str,
    wf: float,
    total_buf: int
) -> Optional[Tuple[int, int]]:
    """Determine baseline ride height for homologated racing classes."""
    bump_offset = 5 if bumpiness == 'high' else 0
    if grp in ['Gr.X', 'Gr.1']:
        base = 50 + bump_offset + total_buf
        return base, base + 5
    if grp in ['Gr.2', 'Gr.3']:
        base = 65 + bump_offset + total_buf
        return base, base + 7
    if grp == 'Gr.4':
        base = 85 + bump_offset + total_buf
        rake = max(6, min(12, round(6.0 + 14.0 * max(0.0, wf - 0.45))))
        return base, base + rake
    if grp == 'Gr.B':
        base = 90 + bump_offset + total_buf
        return base, base + 8
    return None


def _calculate_road_ride_height(
    body_style: str,
    height_m: float,
    bumpiness: str,
    total_buf: int,
    wf: float,
    is_no_aero_rake: bool
) -> Tuple[int, int]:
    """Determine baseline ride height for road production cars."""
    bump_offset = 5 if bumpiness == 'high' else 0
    h_val = height_m or 1.30
    if body_style in ['SUV', 'Pickup', 'Minivan', 'Van'] or h_val >= 1.60:
        base_f = 135 + bump_offset + total_buf
    elif h_val >= 1.48:
        base_f = 105 + bump_offset + total_buf
    else:
        base_f = 100 + bump_offset + total_buf

    if is_no_aero_rake:
        return base_f, base_f + 22
    rake = max(5, min(14, round(6.0 + 16.0 * max(0.0, wf - 0.45))))
    return base_f, base_f + rake


def _calculate_unranged_ride_height(
    grp: str,
    body_style: str,
    height_m: float,
    bumpiness: str,
    total_buf: int,
    wf: float,
    ptw: float,
    is_racecar: bool,
    is_ultralight: bool,
    is_no_aero_rake: bool
) -> Tuple[int, int]:
    """Calculate ride height based on vehicle category and body geometry."""
    archetype_res = _calculate_archetype_ride_height(grp, bumpiness, wf, total_buf)
    if archetype_res:
        return archetype_res

    bump_offset = 5 if bumpiness == 'high' else 0
    if is_ultralight:
        base_f = 60 + bump_offset + total_buf
        return base_f, base_f + (12 if ptw >= 500 else 10)
    if is_racecar:
        base_f = 65 + bump_offset + total_buf
        return base_f, base_f + 7
    if body_style in ['SUV', 'Pickup'] or (height_m or 1.30) >= 1.65:
        base_f = 135 + bump_offset + total_buf
        return base_f, base_f + 10

    return _calculate_road_ride_height(body_style, height_m, bumpiness, total_buf, wf, is_no_aero_rake)


def _calculate_explicit_range_ride_height(
    height_front_range: Optional[Tuple[int, int]],
    height_rear_range: Optional[Tuple[int, int]],
    height_range: Optional[Tuple[int, int]],
    bumpiness: str,
    is_racecar: bool,
    is_ultralight: bool,
    total_buf: int,
    rake: int,
    is_widebody: bool = False
) -> Optional[Tuple[int, int]]:
    """Calculate ride height if slider ranges are provided."""
    if height_front_range and height_rear_range:
        return _calculate_ranged_ride_height(
            height_front_range[0], height_front_range[1],
            height_rear_range[0], height_rear_range[1],
            bumpiness, is_racecar, is_ultralight, total_buf, rake, is_widebody
        )
    if height_range:
        return _calculate_ranged_ride_height(
            height_range[0], height_range[1],
            height_range[0], height_range[1],
            bumpiness, is_racecar, is_ultralight, total_buf, rake, is_widebody
        )
    return None


def calculate_ride_height(
    is_dirt: bool = False,
    is_racecar: bool = False,
    is_ultralight: bool = False,
    body_style: str = 'Coupe',
    bumpiness: str = 'medium',
    ptw: float = 200.0,
    wf: float = 0.50,
    height_range: Optional[Tuple[int, int]] = None,
    height_front_range: Optional[Tuple[int, int]] = None,
    height_rear_range: Optional[Tuple[int, int]] = None,
    elevation_diff_m: float = 0.0,
    is_widebody: bool = False,
    height_m: float = 1.30,
    group: str = 'Road Car',
    is_controller: bool = False,
    is_no_aero_rake: bool = False
) -> Tuple[int, int]:
    """Calculate front ground clearance and positive rake angle (mm) from vehicle geometry."""
    if is_dirt:
        return 150, 155

    total_buf = _calculate_ride_height_buffers(is_dirt, elevation_diff_m, is_widebody, is_controller, is_racecar)
    rake = _calculate_rake(wf, is_no_aero_rake)

    ranged_res = _calculate_explicit_range_ride_height(
        height_front_range, height_rear_range, height_range, bumpiness, is_racecar, is_ultralight, total_buf, rake, is_widebody
    )
    if ranged_res:
        return ranged_res

    return _calculate_unranged_ride_height(
        normalize_group(group), body_style, height_m, bumpiness, total_buf, wf, ptw, is_racecar, is_ultralight, is_no_aero_rake
    )
