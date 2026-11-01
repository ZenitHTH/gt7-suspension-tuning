# Dynamic G-Force Calibrator & Multi-Variable Reverse Solver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dynamic G-force telemetry calibrator that models cornering G as a function of downforce (`G @ Downforce Front/Rear`) and an Excel-Solver style constrained reverse optimizer that automatically solves for optimal ride height, spring frequency, downforce, and roll stiffness without bottoming out.

**Architecture:** Add two focused library modules under `lib/`: `lib/calibrator.py` (fits 3-point in-game rotational G-force telemetry at a reference downforce and predicts `60/120/240 km/h` G-forces across any downforce pair) and `lib/optimizer.py` (constrained multi-variable solver supporting locked parameters and objective targets `balanced`, `max_grip`, and `min_tire_wear`). Wire both into `setup.py`, `cli.py`, and `sheet_formatter.py` so every setup sheet explicitly reports the dynamic G-force at the exact recommended downforce alongside min/max aero scaling.

**Tech Stack:** Python 3.10+, Standard Library (`math`, `dataclasses`, `typing`, `unittest`), GT7 Update 1.72+ (Spec IV) vehicle dynamics engine.

**Spec:** User requirement for a reverse solver + dynamic G-force calibrator where G-force dynamically follows downforce and always tells the user the exact G-force at each specific downforce setting.

## Global Constraints

- Follow Clean Code rules: max 20 lines per function, max 200 lines per file, max 3 function arguments (group into `@dataclass` parameter objects), zero boolean flag arguments in new functions.
- Zero external runtime dependencies beyond Python standard library.
- Every G-force output MUST explicitly state the `(Front / Rear)` downforce pair at which that G-force occurs (`e.g. 1.46G / 1.60G / 1.78G @ DF 118/190`).
- Preserve 100% backward compatibility with existing `cli.py`, `setup.py`, and all 48 existing unit tests.

## Review Focus

1. User provides measured G-forces (`1.46G 1.59G 1.75G`) at a low reference downforce (`110/100`), and the solver raises downforce to `135/185`: predicted G at `240 km/h` must increase monotonically while `60 km/h` G changes minimally ($\propto (v/240)^2$).
2. User provides measured G-forces without specifying `--g-ref-df`: calibrator must cleanly fall back to the vehicle's baseline/midpoint downforce without division-by-zero when total downforce is `0` (stock wingless road car).
3. Aerodynamic Center-of-Pressure (CP) imbalance penalty: maxing front downforce (`200`) while starving rear downforce (`100`) on a front-heavy FR car must reduce effective high-speed cornering G due to rear axle saturation, preventing the solver from naively maxing front aero.
4. High-speed trail-braking bottoming auto-correction: when baseline ride height (`115 mm`) bottoms out at `240 km/h` (`-6.6 mm` clearance), the reverse solver must automatically raise `rh_front` and/or `fn_front` until dynamic clearance $\ge 12.0\text{ mm}$ while keeping positive rake.
5. Locked parameter support for future PyQt UI integration: locking any subset of parameters (e.g. `locked={'downforce', 'ride_height_mm'}`) must hold those exact values fixed while optimizing the remaining unlocked parameters.

---

### Task 1: Dynamic G-Force Calibrator & Downforce-to-G Predictor (`lib/calibrator.py`)

**Files:**
- Create: `lib/calibrator.py`
- Modify: `lib/__init__.py`
- Test: `tests/test_calibrator.py`

**Interfaces:**
- Consumes: `lib.formulas.get_tire_mu`
- Produces:
  - `@dataclass class GForceCalibrationInput`:
    `measured_g: Optional[Tuple[float, float, float]] = None` (`60, 120, 240 km/h`),
    `ref_downforce: Optional[Tuple[int, int]] = None`,
    `base_mu: float = 1.55`,
    `front_weight_ratio: float = 0.50`,
    `mass_kg: float = 1200.0`
  - `@dataclass class GForceModel`:
    `mu_zero: float`, `k_aero: float`, `front_weight_ratio: float`, `ref_downforce: Tuple[int, int]`
  - `calibrate_g_model(config: GForceCalibrationInput) -> GForceModel`
  - `predict_g_at_downforce(model: GForceModel, downforce: Tuple[int, int]) -> Dict[str, Any]`
  - `build_df_g_profile(model: GForceModel, df_ranges: Tuple[Tuple[int, int], Tuple[int, int]], active_df: Tuple[int, int]) -> Dict[str, Any]`

- [ ] **Step 1: Write the failing unit tests in `tests/test_calibrator.py`**

```python
import unittest
from lib.calibrator import (
    GForceCalibrationInput,
    calibrate_g_model,
    predict_g_at_downforce,
    build_df_g_profile
)


class TestGForceCalibrator(unittest.TestCase):
    def test_calibrate_from_measured_sierra_telemetry(self):
        cfg = GForceCalibrationInput(
            measured_g=(1.46, 1.59, 1.75),
            ref_downforce=(110, 100),
            base_mu=1.55,
            front_weight_ratio=0.56,
            mass_kg=989.0
        )
        model = calibrate_g_model(cfg)
        at_ref = predict_g_at_downforce(model, (110, 100))
        self.assertAlmostEqual(at_ref['g_60'], 1.46, places=2)
        self.assertAlmostEqual(at_ref['g_240'], 1.75, places=2)
        self.assertEqual(at_ref['downforce'], {'front': 110, 'rear': 100})
        self.assertIn('@ DF 110/100', at_ref['summary'])

        # Increasing downforce to 135/185 increases 240 km/h G more than 60 km/h G
        at_high = predict_g_at_downforce(model, (135, 185))
        self.assertGreater(at_high['g_240'], at_ref['g_240'] + 0.05)
        self.assertGreater(
            at_high['g_240'] - at_ref['g_240'],
            at_high['g_60'] - at_ref['g_60']
        )

    def test_zero_aero_and_unprovided_fallback(self):
        cfg = GForceCalibrationInput(base_mu=1.35, front_weight_ratio=0.52, mass_kg=1200.0)
        model = calibrate_g_model(cfg)
        pred = predict_g_at_downforce(model, (0, 0))
        self.assertAlmostEqual(pred['g_60'], pred['g_240'], places=2)
        self.assertIn('@ DF 0/0', pred['summary'])

    def test_cp_imbalance_penalty_reduces_effective_g(self):
        cfg = GForceCalibrationInput(
            measured_g=(1.45, 1.58, 1.75),
            ref_downforce=(120, 180),
            front_weight_ratio=0.56,
            mass_kg=989.0
        )
        model = calibrate_g_model(cfg)
        # Same total downforce (300), but balanced (120/180) vs inverted front-heavy (200/100)
        g_balanced = predict_g_at_downforce(model, (120, 180))
        g_inverted = predict_g_at_downforce(model, (200, 100))
        self.assertGreater(g_balanced['g_240'], g_inverted['g_240'])

    def test_build_df_g_profile_returns_min_active_max(self):
        cfg = GForceCalibrationInput(
            measured_g=(1.46, 1.59, 1.75),
            ref_downforce=(110, 100),
            front_weight_ratio=0.56,
            mass_kg=989.0
        )
        model = calibrate_g_model(cfg)
        profile = build_df_g_profile(model, ((50, 200), (100, 250)), (118, 190))
        self.assertEqual(profile['active']['downforce'], {'front': 118, 'rear': 190})
        self.assertLess(profile['min_aero']['g_240'], profile['active']['g_240'])
        self.assertLess(profile['active']['g_240'], profile['max_aero']['g_240'])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning python3 -m unittest tests/test_calibrator.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'lib.calibrator'`

- [ ] **Step 3: Implement `lib/calibrator.py` and export in `lib/__init__.py`**

Implement `lib/calibrator.py` keeping every function $\le 20$ lines and $\le 3$ arguments:
- `_cp_balance_efficiency(df_front: int, df_rear: int, wf: float) -> float`:
  Returns `1.0` when `df_front + df_rear == 0`. Otherwise computes target front share `target_share = max(0.32, min(0.46, 1.0 - wf))` and returns `max(0.84, 1.0 - 0.55 * abs(front_share - target_share))`.
- `calibrate_g_model(config: GForceCalibrationInput) -> GForceModel`:
  When `config.measured_g` is provided (`g60, g120, g240`), solves linear aero scaling across $s_{60} = (60/240)^2 = 0.0625$ and $s_{240} = 1.0$:
  $$\Delta G_{\text{aero}, 240} = \max(0.0, \frac{g_{240} - g_{60}}{1.0 - 0.0625}), \quad \mu_0 = g_{60} - 0.0625 \cdot \Delta G_{\text{aero}, 240}$$
  Divides $\Delta G_{\text{aero}, 240}$ by $\max(1.0, (DF_{\text{ref},f} + DF_{\text{ref},r}) \cdot \eta_{cp})$ to obtain `k_aero`.
- `predict_g_at_downforce(model: GForceModel, downforce: Tuple[int, int]) -> Dict[str, Any]`:
  Computes `g_60`, `g_120`, `g_240` for `(df_f, df_r)` and formats `'summary': f"{g60:.2f}G / {g120:.2f}G / {g240:.2f}G @ DF {df_f}/{df_r}"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning python3 -m unittest tests/test_calibrator.py`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit Task 1**

```bash
git -C /Users/zenithth/.gemini/config/skills/gt7-suspension-tuning add lib/calibrator.py lib/__init__.py tests/test_calibrator.py
git -C /Users/zenithth/.gemini/config/skills/gt7-suspension-tuning commit -m "feat(calibrator): add dynamic G-force at downforce calibrator and predictor"
```

---

### Task 2: Constrained Multi-Variable Reverse Solver (`lib/optimizer.py`)

**Files:**
- Create: `lib/optimizer.py`
- Modify: `lib/__init__.py`
- Test: `tests/test_optimizer.py`

**Interfaces:**
- Consumes: `lib.calibrator.GForceModel`, `lib.calibrator.predict_g_at_downforce`, `lib.equilibrium.simulate_high_speed_trail_braking`, `lib.equilibrium.solve_suspension_equilibrium`, `lib.tire_wear.calculate_tire_wear_index`
- Produces:
  - `@dataclass class SolverRequest`:
    `veh: Any` (`VehicleSpec`),
    `trk: Any` (`TrackSpec`),
    `baseline_params: Dict[str, Any]`,
    `telem: Dict[str, Any]`,
    `sliders: Dict[str, Any]`,
    `g_model: GForceModel`,
    `objective: str = 'balanced'` (`'balanced' | 'max_grip' | 'min_tire_wear'`),
    `locked_params: Tuple[str, ...] = ()`,
    `speed_kmh: float = 240.0`
  - `@dataclass class SolverResult`:
    `parameters: Dict[str, Any]`,
    `g_prediction: Dict[str, Any]`,
    `df_g_profile: Dict[str, Any]`,
    `trail_simulation: Dict[str, Any]`,
    `equilibrium_proof: Dict[str, Any]`,
    `tire_wear: Dict[str, Any]`,
    `objective_score: float`
  - `solve_optimal_setup(request: SolverRequest) -> SolverResult`

- [ ] **Step 1: Write the failing unit tests in `tests/test_optimizer.py`**

```python
import unittest
from models import VehicleSpec, TrackSpec
from setup_engine import resolve_slider_ranges, compute_baseline_suspension
from lib.calibrator import GForceCalibrationInput, calibrate_g_model
from lib.optimizer import SolverRequest, solve_optimal_setup


class TestReverseOptimizer(unittest.TestCase):
    def setUp(self):
        car = {
            'id': '3466', 'name': "Ford Sierra RS 500 Cosworth '87",
            'drivetrain': 'FR', 'mass_kg': 989, 'power_hp': 359, 'torque_nm': 368.9,
            'balance': {'front_pct': 56, 'rear_pct': 44}
        }
        explicit = {
            'df_front': (50, 200), 'df_rear': (100, 250),
            'height_front': (100, 200), 'height_rear': (120, 220),
            'fn_front': (1.50, 3.50), 'fn_rear': (1.50, 3.50),
            'height_range': None
        }
        self.sliders = resolve_slider_ranges(car, explicit)
        self.veh = VehicleSpec.from_dict(car, custom_overrides={}, is_widebody=True)
        self.trk = TrackSpec.from_dict(None, mode='endurance', tire='RM')
        self.params, self.telem = compute_baseline_suspension(
            self.veh, self.trk, 'RM', self.sliders, True, False
        )
        self.g_model = calibrate_g_model(GForceCalibrationInput(
            measured_g=(1.46, 1.59, 1.75), ref_downforce=(110, 100),
            base_mu=1.55, front_weight_ratio=0.56, mass_kg=989.0
        ))

    def test_solver_eliminates_bottoming_and_preserves_rake(self):
        # Force an unsafe low front height in baseline to verify solver fixes it
        self.params['ride_height_mm']['front'] = 105
        req = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='balanced', speed_kmh=240.0
        )
        res = solve_optimal_setup(req)
        self.assertFalse(res.trail_simulation['bottoming_or_fender_hit'])
        self.assertGreaterEqual(res.trail_simulation['dynamic_outside_front_clearance_mm'], 10.0)
        rh = res.parameters['ride_height_mm']
        self.assertGreater(rh['rear'], rh['front'])

    def test_max_grip_vs_min_tire_wear_objectives(self):
        req_grip = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='max_grip', speed_kmh=240.0
        )
        req_wear = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='min_tire_wear', speed_kmh=240.0
        )
        res_grip = solve_optimal_setup(req_grip)
        res_wear = solve_optimal_setup(req_wear)
        self.assertGreater(res_grip.g_prediction['g_240'], res_wear.g_prediction['g_240'])
        self.assertLess(
            res_wear.tire_wear['front_wear_factor'],
            res_grip.tire_wear['front_wear_factor']
        )

    def test_locked_parameters_remain_untouched(self):
        self.params['downforce']['front'] = 110
        self.params['downforce']['rear'] = 155
        req = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='max_grip', locked_params=('downforce',), speed_kmh=240.0
        )
        res = solve_optimal_setup(req)
        self.assertEqual(res.parameters['downforce']['front'], 110)
        self.assertEqual(res.parameters['downforce']['rear'], 155)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning python3 -m unittest tests/test_optimizer.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'lib.optimizer'`

- [ ] **Step 3: Implement `lib/optimizer.py` and export in `lib/__init__.py`**

Implement `lib/optimizer.py` (< 180 lines, functions $\le 20$ lines, $\le 3$ args):
- `_optimize_downforce(req: SolverRequest) -> Tuple[int, int]`:
  If `'downforce'` in `req.locked_params`, returns current `(front, rear)`. Otherwise searches candidate `(df_f, df_r)` pairs across slider spans obeying `df_f <= df_r` on non-oval RWD cars, maximizing `g_240 - wear_penalty * aero_load` according to `req.objective` (`'max_grip'` weights `g_240` at `1.0`, `'min_tire_wear'` caps aero at `0.40–0.55` span, `'balanced'` balances CP at `0.50–0.65` span).
- `_optimize_frequencies_and_camber(req: SolverRequest, g_pred: Dict[str, Any]) -> None`:
  Updates `natural_frequency_hz` and `camber_deg` (unless in `locked_params`) scaled by calibrated `g_pred['g_240']` and objective (`min_tire_wear` softens $f_n$ by $-0.15\text{ Hz}$ and flattens camber to $-2.0^\circ / -1.0^\circ$; `max_grip` stiffens $f_n$ by $+0.15\text{ Hz}$ and sets camber $-2.8^\circ / -1.5^\circ$ while preserving flat-ride ratio `1.04`).
- `_resolve_clearance_heights(req: SolverRequest) -> None`:
  If `'ride_height_mm'` not in `req.locked_params`, runs `simulate_high_speed_trail_braking` at `req.speed_kmh` and iteratively steps `rh_front` and `rh_rear` within slider bounds until `dynamic_outside_front_clearance_mm >= 12.0` and rear squat buffer $\ge 12.0\text{ mm}$ while maintaining positive rake $\ge 6\text{ mm}$.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning python3 -m unittest tests/test_optimizer.py`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit Task 2**

```bash
git -C /Users/zenithth/.gemini/config/skills/gt7-suspension-tuning add lib/optimizer.py lib/__init__.py tests/test_optimizer.py
git -C /Users/zenithth/.gemini/config/skills/gt7-suspension-tuning commit -m "feat(optimizer): add constrained multi-variable reverse suspension solver"
```

---

### Task 3: Wire Dynamic G-Force @ Downforce & Solver into `setup.py`, `cli.py`, and `sheet_formatter.py`

**Files:**
- Modify: `cli.py`
- Modify: `setup.py`
- Modify: `sheet_formatter.py`
- Test: `tests/test_cli_output.py`

**Interfaces:**
- Consumes: `lib.calibrator`, `lib.optimizer`
- Produces:
  - New CLI flags in `cli.py`:
    `--g-forces G60 G120 G240` (`nargs=3, type=float`),
    `--g-ref-df FRONT REAR` (`nargs=2, type=int`),
    `--solve {balanced,max_grip,min_tire_wear}` (`type=str, default=None`)
  - New telemetry keys in `setup.build_setup` output dict:
    `telemetry['dynamic_g_force']` (active G-forces with explicit `@ DF front/rear`),
    `telemetry['downforce_g_profile']` (`min_aero`, `active`, `max_aero` G-force scaling table)
  - Formatted dynamic G-force lines in `sheet_formatter.py`

- [ ] **Step 1: Write the failing test in `tests/test_cli_output.py`**

Add test method in `tests/test_cli_output.py`:
```python
def test_dynamic_g_force_at_downforce_and_solver_in_sheet(self):
    car = {
        'id': '3466', 'name': "Ford Sierra RS 500 Cosworth '87",
        'drivetrain': 'FR', 'mass_kg': 989, 'power_hp': 359, 'torque_nm': 368.9,
        'balance': {'front_pct': 56, 'rear_pct': 44}
    }
    res = build_setup(
        car=car, tire='RM', mode='endurance',
        df_front_range=(50, 200), df_rear_range=(100, 250),
        height_front_range=(100, 200), height_rear_range=(120, 220),
        fn_front_range=(1.50, 3.50), fn_rear_range=(1.50, 3.50),
        g_forces=(1.46, 1.59, 1.75), g_ref_df=(110, 100),
        solve_objective='balanced', is_widebody=True, speed_kmh=240.0
    )
    sheet = format_setup_sheet(res)
    df_f = res['parameters']['downforce']['front']
    df_r = res['parameters']['downforce']['rear']
    self.assertIn(f"@ DF {df_f}/{df_r}", sheet)
    self.assertIn("Min DF", sheet)
    self.assertIn("Max DF", sheet)
    self.assertFalse(res['telemetry']['high_speed_simulation']['bottoming_or_fender_hit'])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning python3 -m unittest tests/test_cli_output.py`
Expected: FAIL with `TypeError: build_setup() got an unexpected keyword argument 'g_forces'`

- [ ] **Step 3: Implement wiring in `setup.py`, `cli.py`, and `sheet_formatter.py`**

1. In `setup.py`:
   - Add optional arguments `g_forces: Optional[Tuple[float, float, float]] = None`, `g_ref_df: Optional[Tuple[int, int]] = None`, `solve_objective: Optional[str] = None` to `build_setup`.
   - Build `GForceModel` via `lib.calibrate_g_model`. When `solve_objective` is provided (or when `g_forces` is provided), run `lib.solve_optimal_setup` so ride height, spring rate, and downforce are solved without bottoming.
   - Populate `telemetry['dynamic_g_force']` and `telemetry['downforce_g_profile']`.
2. In `sheet_formatter.py`:
   - In `_format_telemetry`, display the calibrated dynamic G-force line with explicit `@ DF front/rear`:
     `• แรงเหวี่ยง G ตามแรงกดแอร์โร (Dynamic G @ DF {df_f}/{df_r}): 60 km/h = {g60:.2f}G | 120 km/h = {g120:.2f}G | 240 km/h = {g240:.2f}G`
     `  ↳ เทียบสเกลแรงกด (240 km/h G vs Aero): Min DF ({min_f}/{min_r}) = {min_g240:.2f}G | Setup DF ({df_f}/{df_r}) = {g240:.2f}G | Max DF ({max_f}/{max_r}) = {max_g240:.2f}G`
3. In `cli.py`:
   - Add `--g-forces`, `--g-ref-df`, and `--solve` to `_add_options_arguments` and pass through `_extract_setup_kwargs`.

- [ ] **Step 4: Run full test suite to verify all tests pass**

Run: `PYTHONPATH=/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning python3 -m unittest discover -s /Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests`
Expected: PASS (56+ tests, 0 failures)

- [ ] **Step 5: Commit Task 3**

```bash
git -C /Users/zenithth/.gemini/config/skills/gt7-suspension-tuning add cli.py setup.py sheet_formatter.py tests/test_cli_output.py
git -C /Users/zenithth/.gemini/config/skills/gt7-suspension-tuning commit -m "feat(cli): wire dynamic G-force @ downforce telemetry and reverse solver into setup sheet"
```
