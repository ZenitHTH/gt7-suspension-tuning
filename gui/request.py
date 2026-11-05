"""Qt-free request/result dataclasses + choice literals for the GUI (Task 2).

`GuiRequest` is what `SetupForm.collect()` produces; `GuiResult` is what
`TuningService.compute()` returns. No Qt imports here by design.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Choice literals (verbatim from cli.py — do not reword).
TIRE_COMPOUNDS: Tuple[str, ...] = ('CH', 'CM', 'CS', 'SH', 'SM', 'SS', 'RH', 'RM', 'RS', 'Dirt', 'Wet')
DRIVETRAINS: Tuple[str, ...] = ('FF', 'FR', 'MR', 'RR', 'AWD', '4WD', '4x4')
MODES: Tuple[str, ...] = ('grip', 'time_attack', 'wet', 'dirt', 'drift', 'endurance')
SYMPTOMS: Tuple[str, ...] = ('entry_push', 'exit_snap', 'bottoming', 'curb_hop', 'front_tire_wear', 'rear_tire_wear')
SOLVE_OBJECTIVES: Tuple[str, ...] = ('balanced', 'max_grip', 'min_tire_wear')


@dataclass
class GuiRequest:
    """All user inputs for one setup computation.

    Range pairs are (min, max); `None` means "use saved/preseeded DB values"
    (the form applies the (0, 0) -> None rule before constructing this).
    """
    car_id: str
    tire: str = 'SS'
    df_front: Optional[Tuple[int, int]] = None      # (min, max)
    df_rear: Optional[Tuple[int, int]] = None
    height_front: Optional[Tuple[int, int]] = None
    height_rear: Optional[Tuple[int, int]] = None
    fn_front: Optional[Tuple[float, float]] = None
    fn_rear: Optional[Tuple[float, float]] = None
    custom_mass: Optional[int] = None
    custom_power: Optional[int] = None
    custom_torque: Optional[float] = None
    custom_drivetrain: Optional[str] = None
    custom_balance: Optional[Tuple[int, int]] = None
    track_id: Optional[str] = None
    mode: str = 'grip'
    g_forces: Optional[Tuple[float, float, float]] = None   # G@60/120/240
    g_ref_df: Optional[Tuple[int, int]] = None
    solve_objective: Optional[str] = None
    speed_kmh: Optional[float] = None
    stability: Optional[Tuple[float, float]] = None
    symptoms: Optional[List[str]] = None
    is_widebody: bool = False
    is_controller: bool = False


@dataclass
class GuiResult:
    """Outcome of a computation: sheet + raw setup, warnings, or an error."""
    setup: Optional[Dict[str, Any]] = None
    sheet: str = ''
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None
