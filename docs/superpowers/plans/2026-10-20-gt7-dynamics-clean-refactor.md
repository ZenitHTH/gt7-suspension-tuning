# GT7 Dynamics & Tuner Clean Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up and modularize `gt7_dynamics.py` and `gt7_tuner.py` by extracting typed data models, centralizing physics/calibration constants, and separating calculation from presentation, while strictly preserving 100% calculation accuracy and backward compatibility with all 22 unit tests.

**Architecture:** Introduce typed domain models in `gt7_models.py` (`VehicleSpec`, `TrackSpec`, `SetupSheet`) and centralized calibration constants in `gt7_constants.py`. Refactor `gt7_dynamics.py` to use these constants and typed contracts under the hood while retaining its identical public API. Refactor `gt7_tuner.py` into distinct stages: Input Parsing -> Model Construction -> Physics Synthesis -> Presentation Formatting.

**Tech Stack:** Python 3.10+, standard library (`dataclasses`, `typing`, `math`, `unittest`, `argparse`).

**Spec:** Codebase audit and architecture requirements defined during user discussion on 2026-10-20.

## Global Constraints
- Preserve exact public function signatures and return types in `gt7_dynamics.py`.
- Preserve exact CLI arguments, behavior, and output format in `gt7_tuner.py`.
- All existing unit tests in `tests/test_gt7_dynamics.py` must pass at every task boundary.
- Zero regression in numerical calculations (ride heights, frequencies, ARB, dampers, alignment, aero, LSD, brake bias, trail-braking compression).
- No new external runtime dependencies (keep standard library only).

## Review Focus
1. Unsprung mass and corner mass calculations in `VehicleSpec` must match `calculate_sprung_mass` values to 0.1 kg precision.
2. Aerodynamic heave, braking pitch, and roll deflection formulas in `simulate_high_speed_trail_braking` must produce identical millimeter values.
3. Closed-loop trims and quick-trims delta table must preserve exact GT7 legal boundary clamps (compression <= 40%).
4. Widebody ride height buffer and center-of-pressure aero scaling must remain intact.
5. In-game setup sheet formatting (Thai + English menu items) must match character-for-character.

---

### Task 1: Centralize Constants in `scripts/gt7_constants.py`

**Files:**
- Create: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_constants.py`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:12-25`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_constants.py`

**Interfaces:**
- Produces:
  - `TIRE_MU_MAP: Dict[str, float]`
  - `SLIDER_BOUNDS: Dict[str, Tuple[int, int]]` (Damping compression [20, 40], expansion [30, 80], ARB [1, 10], LSD [4, 30]/[5, 65])
  - `CHASSIS_RATIOS: Dict[str, float]` (Wheelbase default ratio 0.58, track width ratio 0.85, road unsprung ratio 0.12, race unsprung ratio 0.09)
  - `CG_HEIGHT_RATIOS: Dict[str, float]` (Racecar 0.32, SUV/Pickup 0.46, Standard Road 0.36)
  - `AERO_REFERENCE_SPEED_KMH: float = 240.0`
  - `STROKE_CLEARANCE_FLOOR_MM: Dict[str, float]` (Widebody 16.0, Standard 22.0)

- [ ] **Step 1: Write the failing test for constants**
Create `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_constants.py`:
```python
import unittest
import gt7_constants

class TestGT7Constants(unittest.TestCase):
    def test_tire_mu_map_entries(self):
        self.assertEqual(gt7_constants.TIRE_MU_MAP['SS'], 1.35)
        self.assertEqual(gt7_constants.TIRE_MU_MAP['RM'], 1.55)
    def test_slider_bounds(self):
        self.assertEqual(gt7_constants.SLIDER_BOUNDS['damping_compression'], (20, 40))
        self.assertEqual(gt7_constants.SLIDER_BOUNDS['damping_expansion'], (30, 80))
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests/test_gt7_constants.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'gt7_constants')

- [ ] **Step 3: Implement `gt7_constants.py` and import into `gt7_dynamics.py`**
Implement `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_constants.py` with all constants cleanly documented and typed. Update `gt7_dynamics.py` to import and reference `gt7_constants.TIRE_MU_MAP` and slider limits.

- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests/test_gt7_constants.py -v && python3 -m unittest discover -s tests -v`
Expected: PASS (all 23 tests pass)

---

### Task 2: Typed Vehicle & Track Models in `scripts/gt7_models.py`

**Files:**
- Create: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_models.py`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_models.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class VehicleSpec`:
    - fields: `mass_kg: float`, `front_weight_pct: float`, `drivetrain: str`, `group: str`, `body_style: str`, `power_hp: float`, `torque_nm: float`, `length_m: float`, `width_m: float`, `height_m: float`, `wheelbase_m: float`, `track_width_m: float`, `hcg_m: float`, `is_widebody: bool`
    - method: `classmethod from_dict(car_data: Dict[str, Any], custom_overrides: Optional[Dict[str, Any]] = None, is_widebody: bool = False) -> 'VehicleSpec'`
  - `@dataclass(frozen=True) class TrackSpec`:
    - fields: `name: str`, `category: str`, `bumpiness: str`, `elevation_diff_m: float`, `downforce_demand: str`, `longest_straight_m: float`, `is_oval: bool`, `is_dirt: bool`
    - method: `classmethod from_dict(track_data: Optional[Dict[str, Any]], mode: str = 'grip') -> 'TrackSpec'`

- [ ] **Step 1: Write the failing test for vehicle and track models**
Create `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_models.py`:
```python
import unittest
from gt7_models import VehicleSpec, TrackSpec

class TestGT7Models(unittest.TestCase):
    def test_vehicle_spec_from_dict_heuristic_fallback(self):
        raw = {
            'name': "Ferrari F355 Berlinetta '94",
            'mass_kg': 1350,
            'drivetrain': 'MR',
            'group': 'Road Car',
            'balance': {'front_pct': 42},
            'dimensions_mm': {'length': 4250, 'width': 1900, 'height': 1170}
        }
        spec = VehicleSpec.from_dict(raw, is_widebody=True)
        self.assertEqual(spec.mass_kg, 1350)
        self.assertAlmostEqual(spec.wheelbase_m, 4.250 * 0.58, places=3)
        self.assertTrue(spec.is_widebody)
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests/test_gt7_models.py -v`
Expected: FAIL (ModuleNotFoundError or empty module)

- [ ] **Step 3: Implement `gt7_models.py`**
Implement `VehicleSpec` and `TrackSpec` dataclasses with clean factory constructors encapsulating fallback dimension heuristics with explicit docstrings.

- [ ] **Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests/test_gt7_models.py -v && python3 -m unittest discover -s tests -v`
Expected: PASS (all 24 tests pass)

---

### Task 3: Refactor `gt7_dynamics.py` with Clean Math Helpers

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: `gt7_constants`
- Preserves: Exact existing function signatures:
  - `calculate_sprung_mass`, `calculate_ride_height`, `calculate_natural_frequencies`
  - `calculate_anti_roll_bars`, `calculate_dampers`, `calculate_wheel_alignment`
  - `calculate_differential_lsd`, `calculate_brake_bias`, `calculate_aerodynamics`
  - `calculate_top_speed`, `apply_closed_loop_trim`, `build_quick_trims`
  - `simulate_high_speed_trail_braking`

- [ ] **Step 1: Verify current tests pass as baseline**
Run: `python3 -m unittest discover -s tests -v`
Expected: 24/24 PASS

- [ ] **Step 2: Refactor math helpers and remove hardcoded constants in `gt7_dynamics.py`**
  - Replace magic slider clamps (20, 40, 30, 80) with `gt7_constants.SLIDER_BOUNDS`.
  - Replace inline `240.0` aero velocity with `gt7_constants.AERO_REFERENCE_SPEED_KMH`.
  - Replace stroke floor constants (16.0, 22.0) with `gt7_constants.STROKE_CLEARANCE_FLOOR_MM`.
  - Decompose `simulate_high_speed_trail_braking` into distinct helper equations:
    - `calculate_aerodynamic_heave(df_kg, speed_kmh, wheel_rate_N_per_m) -> float`
    - `calculate_braking_pitch_dive(mass_kg, mu, hcg_m, wheelbase_m, wheel_rate_f) -> float`
    - `calculate_cornering_roll_deflection(mass_kg, mu, hcg_m, track_width_m, lltd_f, arb_f, wheel_rate_f) -> float`

- [ ] **Step 3: Run full unit test suite to verify zero regression**
Run: `python3 -m unittest discover -s tests -v`
Expected: 24/24 PASS with identical numerical outputs

---

### Task 4: Refactor `gt7_tuner.py` Pipeline & Decouple Formatting

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: `gt7_models.VehicleSpec`, `gt7_models.TrackSpec`, `gt7_dynamics`
- Preserves: `build_setup(...)` parameter list and dictionary return schema, `format_setup_sheet(...)` string output, CLI flags.

- [ ] **Step 1: Refactor `build_setup` in `gt7_tuner.py` to use `VehicleSpec` and `TrackSpec`**
Replace 60 lines of inline dictionary unpacks and heuristic math in `gt7_tuner.py` with:
```python
vehicle = VehicleSpec.from_dict(
    car_data=car,
    custom_overrides={...},
    is_widebody=is_widebody
)
track_spec = TrackSpec.from_dict(track_data=track, mode=mode)
```
Pass the structured properties to `gt7_dynamics` and return the setup dictionary.

- [ ] **Step 2: Test CLI runs against benchmark cars**
Run:
```bash
python3 scripts/gt7_tuner.py "Ferrari F355" --mode endurance --widebody --speed 240
python3 scripts/gt7_tuner.py "Red Bull X2019" -t "Autodromo Lago Maggiore" --mode endurance --tire RM --speed 280
```
Expected: Identical setup sheets and telemetry outputs matching baseline.

- [ ] **Step 3: Run complete unit test suite**
Run: `python3 -m unittest discover -s tests -v`
Expected: All 24 tests PASS.

---

### Task 5: Final Review & Quality Gate

**Files:**
- Review: all files in `scripts/` and `tests/`

- [ ] **Step 1: Check code formatting, docstrings, and type annotations**
Ensure zero syntax warnings, no unused imports, and clear first-principles explanations.

- [ ] **Step 2: Run test suite with verbose coverage**
Run: `python3 -m unittest discover -s tests -v`
Expected: 24/24 PASS.
