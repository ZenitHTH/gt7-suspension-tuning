# Brake Balance & Patch 1.71+ Physics Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align GT7 Brake Balance Controller sign conventions, drivetrain physics calculations, and controller compensation to match ground-truth in-game behavior and Patch 1.71+ / 1.72+ Spec IV empirical data.

**Architecture:** Correct the in-game HUD polarity mapping (`-5` Front to `+5` Rear) across calculations, trims, and sheet formatters; implement drivetrain-aware brake proportioning (FF front bias, FR wheel rear bias vs controller clamp, MR/RR yaw damping, AWD center-diff harmony); update tests and documentation.

**Tech Stack:** Python 3.10+, pytest, GT7 First-Principles Dynamics Engine (`lib/`, `sheet_formatter.py`, `cli.py`).

**Spec:** `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/SKILL.md`

## Global Constraints

- **GT7 In-Game Polarity:** Negative values (`-5` to `-1`) indicate FRONT bias (หน้า); `0` is CENTER (กลาง); positive values (`+1` to `+5`) indicate REAR bias (หลัง).
- **Clean Code Standard:** Max 20 lines per function, max 200 lines per file, SRP, clear public contracts, no magic numbers.
- **Python Compatibility:** Python 3.10+ standard library only for core engine; pytest for test execution via `PYTHONPATH=. pytest tests`.
- **Display Labeling:** Explicit direction strings required in formatted output: e.g. `+2 (หลัง / Rear)` or `-1 (หน้า / Front)` or `0 (กลาง / Center)`.

## Review Focus

1. **DualSense Controller on Racing Tires (FR / Gr.3):** Ensure `is_controller=True` clamps rear brake bias to `≤ +1` on racing compounds to prevent ABS micro-lock and snap oversteer.
2. **AWD Platform (e.g., Genesis G70 Gr.4):** Ensure brake bias defaults to `-1` or `0` to prevent center differential binding under trail-braking, validating empirical 1:36.778 telemetry.
3. **Mid-Engine / Rear-Engine (MR / RR):** Ensure brake bias remains `0` to `-2` (neutral to slight front) to prevent trailing-throttle snap-spin in 1.71+ Ackermann kinematics.
4. **Front-Wheel Drive (FF):** Ensure brake bias remains strictly negative (`-1` to `-2`, front bias); never allow positive rear bias on FF.
5. **Zero / Edge Case Weight Distributions:** Ensure extreme weight ratios (e.g., 40:60 to 65:35) stay strictly within legal GT7 slider bounds `[-5, +5]`.

---

### Task 1: Constants & Formatter Ground-Truth Polarity Correction

**Files:**
- Modify: `constants.py:20-25`
- Modify: `sheet_formatter.py:140-165`
- Test: `tests/test_cli_output.py`

**Interfaces:**
- Consumes: `params['brake_bias']` (int)
- Produces: `format_brake_bias_label(bias: int) -> str`

- [ ] **Step 1: Write the failing test**

```python
# In tests/test_cli_output.py
def test_format_brake_bias_ground_truth_label():
    from sheet_formatter import format_brake_bias_label
    assert format_brake_bias_label(-1) == "-1 (หน้า / Front)"
    assert format_brake_bias_label(2) == "+2 (หลัง / Rear)"
    assert format_brake_bias_label(0) == "0 (กลาง / Center)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. /Users/zenithth/.gemini/config/plugins/anibon-stream-synthesis/.venv/bin/pytest tests/test_cli_output.py::test_format_brake_bias_ground_truth_label -v`
Expected: FAIL with `ImportError: cannot import name 'format_brake_bias_label' from 'sheet_formatter'`

- [ ] **Step 3: Implement `format_brake_bias_label` and update `sheet_formatter.py`**

Create `format_brake_bias_label(bias: int) -> str` in `sheet_formatter.py` adhering to SRP (<15 lines):
- If `bias == 0`: return `"0 (กลาง / Center)"`
- If `bias > 0`: return `f"+{bias} (หลัง / Rear)"`
- If `bias < 0`: return `f"{bias} (หน้า / Front)"`
Update line 143 in `sheet_formatter.py` from `(หน้า + / หลัง -)` to use `format_brake_bias_label(bias)` and range `[หน้า -5 ถึง +5 หลัง]`.
Update `constants.py` slider bounds comment if needed.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. /Users/zenithth/.gemini/config/plugins/anibon-stream-synthesis/.venv/bin/pytest tests/test_cli_output.py::test_format_brake_bias_ground_truth_label -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add constants.py sheet_formatter.py tests/test_cli_output.py
git commit -m "fix(formatter): correct GT7 brake balance in-game polarity to negative front and positive rear"
```

---

### Task 2: Drivetrain Brake Bias Solver Calibration (Patch 1.71+ / 1.72+)

**Files:**
- Modify: `lib/wheels.py:84-101`
- Modify: `setup_engine.py:120-128`
- Test: `tests/test_gt7_dynamics.py`
- Test: `tests/test_lib_modules.py`

**Interfaces:**
- Consumes: `calculate_brake_bias(wf, hcg_m, wheelbase_m, drivetrain, is_endurance, is_controller)`
- Produces: `Tuple[int, float]` where int is signed bias in GT7 scale `[-5, +5]` and float is pitch transfer %

- [ ] **Step 1: Write the failing test**

```python
# In tests/test_lib_modules.py
def test_calculate_brake_bias_ground_truth():
    from lib.wheels import calculate_brake_bias
    # FF must have front bias (negative)
    bias_ff, _ = calculate_brake_bias(wf=0.62, drivetrain='FF')
    assert bias_ff in [-1, -2]
    # FR front-heavy on wheel should have rearward bias (positive) for trail-brake rotation
    bias_fr_wheel, _ = calculate_brake_bias(wf=0.54, drivetrain='FR', is_controller=False)
    assert bias_fr_wheel in [1, 2, 3]
    # FR on controller must be clamped to <= 1 to avoid ABS snap
    bias_fr_pad, _ = calculate_brake_bias(wf=0.54, drivetrain='FR', is_controller=True)
    assert bias_fr_pad <= 1
    # AWD (Genesis G70 Gr.4) must have slight front or center bias to avoid center diff binding
    bias_awd, _ = calculate_brake_bias(wf=0.53, drivetrain='AWD')
    assert bias_awd in [-1, 0]
    # MR should have neutral or slight front bias (0 to -2) as yaw damper
    bias_mr, _ = calculate_brake_bias(wf=0.44, drivetrain='MR')
    assert bias_mr in [-2, -1, 0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. /Users/zenithth/.gemini/config/plugins/anibon-stream-synthesis/.venv/bin/pytest tests/test_lib_modules.py::test_calculate_brake_bias_ground_truth -v`
Expected: FAIL due to inverted values and missing `is_controller` parameter.

- [ ] **Step 3: Implement `calculate_brake_bias` in `lib/wheels.py` and pass `is_controller` from `setup_engine.py`**

Refactor `calculate_brake_bias` in `lib/wheels.py`:
- Helper `_calculate_drivetrain_bias(drivetrain: str, wf: float, is_controller: bool) -> int`:
  - `if drivetrain == 'FF'`: return `-1` if wf < 0.64 else `-2`
  - `if drivetrain in ['MR', 'RR']`: return `0` if wf >= 0.46 else `-1`
  - `if drivetrain in ['AWD', '4WD']`: return `-1` if wf >= 0.52 else `0`
  - `if drivetrain == 'FR'`:
    - Base rearward bias: `round(10.0 * (wf - 0.48))`
    - Clamp wheel: `max(1, min(3, base))` if wf >= 0.52 else `0`
    - Clamp controller: `min(1, base)`
- In `setup_engine.py`: Pass `is_controller=is_controller` to `lib.calculate_brake_bias(...)`.
Ensure function length ≤ 20 lines per clean code rule.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. /Users/zenithth/.gemini/config/plugins/anibon-stream-synthesis/.venv/bin/pytest tests/test_lib_modules.py::test_calculate_brake_bias_ground_truth -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lib/wheels.py setup_engine.py tests/test_lib_modules.py tests/test_gt7_dynamics.py
git commit -m "feat(physics): recalibrate brake bias for 1.71+ kinematics and controller yaw damping"
```

---

### Task 3: Align Closed-Loop Trims & Quick-Trims Delta Module

**Files:**
- Modify: `lib/trims.py:20-85`
- Test: `tests/test_optimizer.py`
- Test: `tests/test_lib_modules.py`

**Interfaces:**
- Consumes: `p['brake_bias']`
- Produces: Correctly shifted `p['brake_bias']` in GT7 polarity (`+` for rear rotation, `-` for front stability)

- [ ] **Step 1: Write the failing test**

```python
# In tests/test_optimizer.py
def test_trims_brake_bias_direction():
    from lib.trims import _apply_corner_symptom, _apply_stability_trims
    # Understeer entry push should shift bias rearward (+1 in GT7)
    params = {'anti_roll_bar': {'front': 5, 'rear': 5}, 'ride_height_mm': {'rear': 100}, 'brake_bias': 0}
    _apply_corner_symptom(params, 'entry_push', drivetrain='FR')
    assert params['brake_bias'] == 1  # Shifted rearward to promote trail-brake rotation
    
    # Twitchy high-speed stability should shift bias forward (-1 in GT7)
    params2 = {'anti_roll_bar': {'front': 5, 'rear': 5}, 'damping_expansion_pct': {'rear': 45}, 'brake_bias': 2}
    _apply_stability_trims(params2, stability=(0.0, 0.25), drivetrain='FR')
    assert params2['brake_bias'] <= 1  # Shifted towards front or clamped for stability
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. /Users/zenithth/.gemini/config/plugins/anibon-stream-synthesis/.venv/bin/pytest tests/test_optimizer.py::test_trims_brake_bias_direction -v`
Expected: FAIL due to reversed polarity in `_apply_corner_symptom` and `_apply_stability_trims`.

- [ ] **Step 3: Implement polarity alignment in `lib/trims.py`**

In `lib/trims.py`:
- `_apply_corner_symptom` for `entry_push`:
  - `p['brake_bias'] = min(5, p['brake_bias'] + 1)` (shifts rearward in GT7 scale to promote rotation).
- `_apply_stability_trims` for low-speed loose / high-speed twitchy:
  - If high-speed instability: `p['brake_bias'] = max(-5, p['brake_bias'] - 1)` (shifts forward to stabilize tail).
- In `_apply_tire_wear_symptom`:
  - Preserve 1.71+ Section 2.G invariant: do NOT dump brake bias to full rear to solve front tire wear; keep brake bias adjustment subtle (`max(-2, p['brake_bias'] - 1)` or maintain neutral) while ARB and camber do the heavy lifting.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. /Users/zenithth/.gemini/config/plugins/anibon-stream-synthesis/.venv/bin/pytest tests/test_optimizer.py::test_trims_brake_bias_direction -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lib/trims.py tests/test_optimizer.py
git commit -m "fix(trims): align closed-loop trim deltas with GT7 positive rearward polarity"
```

---

### Task 4: Documentation Synchronization & Full Test Suite Pass

**Files:**
- Modify: `SKILL.md` (Sections 1, 2.A, 2.E, 2.G, 2.H, 3.F)
- Modify: `tests/test_gt7_dynamics.py`
- Modify: `tests/test_cli_output.py`

**Interfaces:**
- Consumes: Updated engine output
- Produces: Consistent documentation, zero test failures

- [ ] **Step 1: Write verification test for full CLI output sheet**

```python
# In tests/test_cli_output.py
def test_cli_sheet_contains_correct_brake_bias_format():
    from cli import format_setup_sheet
    # Verify formatted sheet displays explicit direction
    mock_setup = {
        'car': {'name': 'Test FR', 'drivetrain': 'FR', 'mass_kg': 1300, 'balance': {'ratio_str': '54:46'}},
        'track': {'name': 'Nurburgring', 'mode': 'grip'},
        'telemetry': {'ay_est': 1.5, 'mu': 1.5, 'tot_s': 1100, 'c_f': 280, 'c_r': 270, 'fr_ratio': 1.05, 'lltd_pct': 48.0, 'pitch_transfer_pct': 18.0, 'is_no_aero': False},
        'params': {
            'ride_height_mm': {'front': 95, 'rear': 105},
            'natural_frequency_hz': {'front': 2.6, 'rear': 2.8},
            'anti_roll_bar': {'front': 4, 'rear': 6},
            'damping_compression_pct': {'front': 30, 'rear': 32},
            'damping_expansion_pct': {'front': 48, 'rear': 50},
            'camber_deg': {'front': -2.2, 'rear': -1.2},
            'toe_angle': {'front': '0.00', 'rear': 'In 0.10'},
            'downforce': {'front': 100, 'rear': 200},
            'lsd_rear': {'init': 6, 'accel': 24, 'brake': 14},
            'brake_bias': 2,
            'transmission_top_speed_kmh': 280
        }
    }
    sheet = format_setup_sheet(mock_setup)
    assert "+2 (หลัง / Rear)" in sheet
    assert "(หน้า + / หลัง -)" not in sheet
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `PYTHONPATH=. /Users/zenithth/.gemini/config/plugins/anibon-stream-synthesis/.venv/bin/pytest tests/test_cli_output.py::test_cli_sheet_contains_correct_brake_bias_format -v`

- [ ] **Step 3: Update `SKILL.md` and old test expectations in `test_gt7_dynamics.py`**

In `SKILL.md`:
- Replace all legacy inverted mentions `(หน้า + / หลัง -)` with `(หน้า - / หลัง +)`.
- Update Section 1 dictionary:
  `Brake Proportioning Bias -> Brake Balance Controller -> ตัวควบคุมสมดุลเบรก (-5 หน้า ถึง +5 หลัง)`
- Update Section 2.A, 2.E Table 2.E.1, 2.G, 2.H:
  - FF: `-1 to -2 (Front Bias)`
  - FR: `+1 to +3 (Rear Bias on Wheel)` / `+1 (Controller)`
  - MR: `0 to -2 (Neutral / Slight Front Bias)`
  - AWD: `-1 to 0 (Slight Front / Neutral)`
In `tests/test_gt7_dynamics.py`:
- Update outdated assertions that expected FF to be `>= 0` (now expects `< 0` in GT7 scale).

- [ ] **Step 4: Run full test suite to verify 100% pass**

Run: `PYTHONPATH=. /Users/zenithth/.gemini/config/plugins/anibon-stream-synthesis/.venv/bin/pytest tests`
Expected: 100% PASS across all test modules.

- [ ] **Step 5: Commit**

```bash
git add SKILL.md tests/test_gt7_dynamics.py tests/test_cli_output.py
git commit -m "docs: align SKILL.md brake balance polarity with in-game GT7 HUD and Spec IV physics"
```

---

### Task 5: End-to-End Benchmark Validation (Genesis G70 Gr.4, AMG GT3, Alpine A110)

**Files:**
- Test: `tests/test_benchmark_validation.py`

**Interfaces:**
- Consumes: `setup.py` / `setup_engine.py` / `cli.py`
- Produces: Regression assertions verifying exact benchmark specs match empirical video ground-truth

- [ ] **Step 1: Write end-to-end benchmark tests**

```python
# In tests/test_benchmark_validation.py
import pytest
from setup import generate_full_setup

def test_genesis_g70_gr4_awd_benchmark():
    # Genesis G70 AWD at Red Bull Ring should yield bias in [-1, 0]
    setup = generate_full_setup(car_query="Genesis G70", track_query="Red Bull Ring", tire="RM", mode="grip")
    assert setup['params']['brake_bias'] in [-1, 0]

def test_amg_gt3_fr_wheel_vs_controller_benchmark():
    # AMG GT3 FR at Nurburgring
    wheel_setup = generate_full_setup(car_query="AMG GT3", track_query="Nurburgring", tire="RM", is_controller=False)
    assert wheel_setup['params']['brake_bias'] >= 1  # Rearward bias unlocks trail-brake rotation
    pad_setup = generate_full_setup(car_query="AMG GT3", track_query="Nurburgring", tire="RM", is_controller=True)
    assert pad_setup['params']['brake_bias'] <= 1    # Controller clamp prevents ABS snap
    assert pad_setup['params']['lsd_rear']['brake'] >= 80

def test_alpine_a110_mr_benchmark():
    # MR car should not get high rear bias
    setup = generate_full_setup(car_query="Alpine A110", track_query="Alsace", tire="SM")
    assert setup['params']['brake_bias'] <= 0
```

- [ ] **Step 2: Run test to verify it passes**

Run: `PYTHONPATH=. /Users/zenithth/.gemini/config/plugins/anibon-stream-synthesis/.venv/bin/pytest tests/test_benchmark_validation.py -v`
Expected: PASS

- [ ] **Step 3: Run full CLI smoke test**

Run: `PYTHONPATH=. python3 cli.py "Genesis G70" -t "Red Bull Ring" --tire RM`
Run: `PYTHONPATH=. python3 cli.py "AMG GT3" -t "Nurburgring" --tire RM --controller`
Expected: Clean table output with correct sign labels and physics validation.

- [ ] **Step 4: Commit**

```bash
git add tests/test_benchmark_validation.py
git commit -m "test: add end-to-end benchmark validation suite for GT7 1.71+ brake balance"
```

---

## Self-Review Checklist

1. **Spec Coverage:** Covers in-game polarity fix, drivetrain-specific calibration (FF, FR, MR, AWD), DualSense controller clamping, Section 2.G tire wear rebalancing, and documentation synchronization.
2. **Step Scan:** Every step specifies an exact failing test, command to run, implementation directive, and commit.
3. **Type Consistency:** Consistent use of `brake_bias: int` (in `[-5, +5]`) across `wheels.py`, `trims.py`, `setup_engine.py`, and `sheet_formatter.py`.
4. **Review Focus:** DualSense controller clamping (Task 2 & 5), Genesis G70 AWD (Task 2 & 5), MR/RR yaw damping (Task 2 & 5), FF front bias (Task 2), extreme bounds clamp (Task 2 & 3).
5. **Clean Code Integrity:** All functions kept under 20 lines with single responsibility.
