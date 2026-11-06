"""Tuning service facade + off-thread worker (Tasks 2-3).

`TuningService` wraps the DB lookup layer, `scripts.gt7_db.get_swaps`, and
`setup.build_setup` / `sheet_formatter.format_setup_sheet` behind plain
Python methods so the Qt layer never touches the core directly.
`compute()` never raises: failures come back as `GuiResult(error=...)`.

`Worker` (Task 3) is the QObject wrapper that runs `compute()` off the UI
thread so the solver never blocks the event loop.
"""
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

import setup
from db.interface import (
    TRACKS_DB,
    get_car as _get_car,
    get_slider_ranges as _get_slider_ranges,
    get_track as _get_track,
    norm_str,
    save_car_sliders as _save_car_sliders,
    search_cars as _search_cars,
)
from scripts.gt7_db import get_swaps as _get_swaps
from sheet_formatter import format_setup_sheet

from gui.request import GuiRequest, GuiResult

# The six in-game slider range fields; these are the only ones with
# saved/preseeded DB fallback values, so the "No {name} range" warning
# applies to them alone.
_SLIDER_RANGE_FIELDS: Tuple[Tuple[str, str], ...] = (
    ('df_front', 'DF front'),
    ('df_rear', 'DF rear'),
    ('height_front', 'height front'),
    ('height_rear', 'height rear'),
    ('fn_front', 'natural frequency front'),
    ('fn_rear', 'natural frequency rear'),
)
# All two-value range fields checked for min/max ordering and negatives.
# NOTE: `stability` is deliberately NOT here — it is a signed
# (low_speed, high_speed) index on −1.00 (understeer) … +1.00 (oversteer),
# not a (min, max) range, so neither the ordering check nor the
# below-0 check applies (negative readings are valid input).
_RANGE_FIELDS: Tuple[Tuple[str, str], ...] = _SLIDER_RANGE_FIELDS + (
    ('g_ref_df', 'G-force reference downforce'),
)


class TuningService:
    """Plain-Python service facade over the tuning core + DB."""

    # ---- car / track / swap lookups -------------------------------------

    def search_cars(self, query: str = '') -> List[Dict[str, Any]]:
        """Fuzzy-search the car DB (db.interface.search_cars)."""
        return _search_cars(query=query)

    def get_car(self, car_id: str) -> Optional[Dict[str, Any]]:
        """Resolve a car by exact ID or best name match; None when missing."""
        return _get_car(car_id)

    def search_tracks(self, query: str = '') -> List[Dict[str, Any]]:
        """Filter TRACKS_DB with the same norm_str token logic as car search."""
        q_tokens = set(norm_str(query).split()) if query else None
        results: List[Dict[str, Any]] = []
        for track in TRACKS_DB:
            if not q_tokens:
                results.append(track)
                continue
            t_text = (f"{track.get('id', '')} {track.get('name', '')} "
                      f"{track.get('short_name', '')} {track.get('country', '')}")
            if all(tok in norm_str(t_text) for tok in q_tokens):
                results.append(track)
        return results

    def get_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Resolve a track by ID or name; None when missing."""
        return _get_track(track_id)

    def get_swaps(self, car_id: str) -> List[Dict[str, Any]]:
        """Engine swaps a car can receive; [] when the car is missing."""
        info = _get_swaps(car_id)
        return list(info.get('swaps_available', [])) if info.get('found') else []

    def get_slider_ranges(self, car_id: str) -> Dict[str, Any]:
        """Saved + preseeded slider ranges for a car (saved wins per key)."""
        merged: Dict[str, Any] = dict(_get_slider_ranges(car_id))
        car = self.get_car(car_id)
        if car:
            saved = car.get('slider_ranges') or {}
            for key, value in saved.items():
                merged[key] = list(value) if isinstance(value, (list, tuple)) else value
        return merged

    def save_sliders(self, car_id: str, ranges: Dict[str, Tuple],
                     db_path: Optional[str] = None) -> bool:
        """Persist slider ranges (db.interface.save_car_sliders).

        `db_path` overrides the real cars_master.json location (test use).
        Returns False when the car cannot be found.
        """
        saved = _save_car_sliders(car_id, ranges, db_path=db_path)
        return bool(saved)

    # ---- validation / computation ----------------------------------------

    def validate(self, req: GuiRequest) -> Tuple[List[str], List[str]]:
        """Validate a request. Returns (errors, warnings): errors are hard
        blockers, warnings are soft notes attached to the result."""
        errors: List[str] = []
        warnings: List[str] = []

        if self.get_car(req.car_id) is None:
            errors.append(f'Car not found: {req.car_id}')

        for field, name in _SLIDER_RANGE_FIELDS:
            if getattr(req, field) is None:
                warnings.append(f'No {name} range — using saved/preseeded DB values')

        for field, name in _RANGE_FIELDS:
            value = getattr(req, field)
            if value is None:
                continue
            try:
                lo, hi = value
            except (TypeError, ValueError):
                errors.append(f'{name} range must be a (min, max) pair')
                continue
            if lo > hi:
                errors.append(f'{name} range: min ({lo}) > max ({hi})')
            if lo < 0 or hi < 0:
                errors.append(f'{name} range: value below 0 ({min(lo, hi)})')

        if req.solve_objective is not None and req.g_forces is None:
            warnings.append('Solver needs G-force calibration; solve will be skipped')

        if req.custom_balance is not None and abs(sum(req.custom_balance) - 100) > 1:
            warnings.append(f'Balance front+rear = {sum(req.custom_balance)} (expected 100)')

        if req.g_forces is not None and req.g_ref_df is None:
            warnings.append('G-forces without reference downforce; profile anchored at current DF')

        return errors, warnings

    def compute(self, req: GuiRequest) -> GuiResult:
        """Build a setup + sheet for `req`. NEVER raises: failures come back
        as GuiResult(error=repr(e))."""
        _, warnings = self.validate(req)

        car = self.get_car(req.car_id)
        if car is None:
            return GuiResult(error=f'Car not found: {req.car_id}', warnings=warnings)

        track = self.get_track(req.track_id) if req.track_id else None

        kwargs = {
            'track': track,
            'tire': req.tire,
            'mode': req.mode,
            'custom_mass': req.custom_mass,
            'custom_power': req.custom_power,
            'custom_torque': req.custom_torque,
            'custom_drivetrain': req.custom_drivetrain,
            'custom_balance': req.custom_balance,
            'df_front_range': req.df_front,
            'df_rear_range': req.df_rear,
            'height_front_range': req.height_front,
            'height_rear_range': req.height_rear,
            'fn_front_range': req.fn_front,
            'fn_rear_range': req.fn_rear,
            'stability': req.stability,
            'symptoms': req.symptoms,
            'is_widebody': req.is_widebody,
            'speed_kmh': req.speed_kmh,
            'is_controller': req.is_controller,
            'g_forces': req.g_forces,
            'g_ref_df': req.g_ref_df,
            'solve_objective': req.solve_objective,
        }

        try:
            setup_dict = setup.build_setup(car, **kwargs)
            sheet = format_setup_sheet(setup_dict)
        except Exception as e:
            return GuiResult(error=repr(e), warnings=warnings)

        switched = setup_dict.get('telemetry', {}).get('tire_switched_from')
        if switched:
            warnings.append(
                f"Tire auto-switched {switched} → {setup_dict['tire_compound']} "
                f"({req.mode} circuit requires the surface tire)"
            )
        return GuiResult(setup=setup_dict, sheet=sheet, warnings=warnings)


class Worker(QObject):
    """Off-thread compute wrapper (Task 3).

    App-layer usage: connect `finished`/`failed` to the UI, `moveToThread()`
    the worker, then connect the thread's `started` to `run()`. `finished`
    carries the `GuiResult`; `failed` is belt-and-braces only, since
    `TuningService.compute()` never raises (errors arrive as
    `GuiResult(error=...)`).
    """

    finished = pyqtSignal(object)   # GuiResult
    failed = pyqtSignal(str)

    def __init__(self, service: TuningService, req: GuiRequest,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._req = req

    def run(self) -> None:
        """Run `compute()` and emit `finished` (or `failed` if it ever raises)."""
        try:
            self.finished.emit(self._service.compute(self._req))
        except Exception as e:  # belt-and-braces: compute() never raises
            self.failed.emit(str(e))
