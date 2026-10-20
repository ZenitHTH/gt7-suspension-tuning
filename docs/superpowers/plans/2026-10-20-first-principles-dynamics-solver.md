# First-Principles Suspension & Dynamics Equilibrium Solver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace heuristic rule-of-thumb ride height and spring adjustments with a deterministic physical equilibrium solver that calculates acceleration torque squat, braking dive, trail-braking stroke margin, and tire degradation trade-offs with mathematical proofs.

**Architecture:** Extend `lib/formulas.py` with first-principles mechanics functions (powertrain torque squat/lift, combined trail-braking load vectors, tire wear index, and closed-form suspension equilibrium solver). Integrate these formulas into `lib/aero_body.py`, `lib/springs.py`, and `setup.py`, and display mathematical proofs in `cli.py` dual-language setup sheets. Validate behavior with comprehensive unit tests in `tests/`.

**Tech Stack:** Python 3.10+, Standard Library (`math`, `typing`, `dataclasses`, `unittest`), Gran Turismo 7 physics specs.

**Spec:** User requirement for mathematically proven suspension balance: engine torque reaction forces, braking pitch transfer, trail-braking suspension compliance proof, and tire wear degradation rate modeling.

## Global Constraints

- Preserve backward compatibility with all existing `db/`, `models.py`, and CLI invocation signatures.
- Strictly adhere to GT7 in-game slider bounds and physics updates (Update 1.72+ / Spec IV).
- Zero external dependencies beyond Python standard library.
- Deterministic, pure mathematical functions without floating-point side effects or non-converging iterative loops.

## Review Focus

1. Extreme high torque engines (e.g. 1000+ Nm swaps) causing rear squat that exceeds suspension stroke or flips aerodynamic rake negative.
2. Low ride height / high aero cars (Gr.1, Gr.X, formula) bottoming out during combined high-G deceleration and lateral turn-in (trail braking).
3. Stiff spring rates ($f_n > 3.5\text{ Hz}$) in endurance races causing excessive tire wear multipliers.
4. Edge cases with zero or missing torque/power/height slider inputs falling back to safe physical defaults.
5. In-game slider limits clamping equilibrium solutions without crashing or producing inverted spring rates ($f_{n,f} > f_{n,r}$ violating flat ride).

---

### Task 1: Mathematical Primitives for Torque Squat, Trail Braking, and Tire Wear

**Files:**
- Modify: `lib/formulas.py`
- Test: `tests/test_lib_modules.py`

**Interfaces:**
- Consumes: Vehicle specs (mass, torque, power, drivetrain, $h_{cg}$, wheelbase, track width, wheel rates $K_w$, tire $\mu$).
- Produces:
  - `calculate_acceleration_squat_dive(torque_nm, power_hp, mass_kg, drivetrain, hcg_m, wheelbase_m, wheel_rate_f, wheel_rate_r) -> Dict[str, float]`
  - `calculate_combined_trail_braking_load(mass_kg, mu, hcg_m, wheelbase_m, track_width_m, lltd_f, arb_f, wheel_rate_f, speed_kmh, df_front) -> Dict[str, float]`
  - `calculate_tire_wear_index(fn_hz_f, fn_hz_r, camber_f, camber_r, toe_f, toe_r, ptw, is_endurance) -> Dict[str, float]`

- [ ] **Step 1: Write the failing unit tests for new physics primitives**

Add test methods in `tests/test_lib_modules.py`:
```python
def test_acceleration_squat_dive(self):
    res = calculate_acceleration_squat_dive(
        torque_nm=600.0, power_hp=500.0, mass_kg=1400.0, drivetrain='FR',
        hcg_m=0.45, wheelbase_m=2.6, wheel_rate_f=55000.0, wheel_rate_r=65000.0
    )
    self.assertIn('squat_rear_mm', res)
    self.assertIn('lift_front_mm', res)
    self.assertGreater(res['squat_rear_mm'], 0.0)
    self.assertGreater(res['lift_front_mm'], 0.0)

def test_combined_trail_braking(self):
    res = calculate_combined_trail_braking_load(
        mass_kg=1350.0, mu=1.35, hcg_m=0.45, wheelbase_m=2.5,
        track_width_m=1.6, lltd_f=0.55, arb_f=5, wheel_rate_f=60000.0,
        speed_kmh=180.0, df_front=150.0
    )
    self.assertIn('total_deflection_mm', res)
    self.assertIn('pitch_component_mm', res)
    self.assertIn('roll_component_mm', res)
    self.assertIn('aero_component_mm', res)
    self.assertGreater(res['total_deflection_mm'], 10.0)

def test_tire_wear_index(self):
    wear = calculate_tire_wear_index(
        fn_hz_f=2.8, fn_hz_r=3.0, camber_f=3.0, camber_r=2.0,
        toe_f=-0.10, toe_r=0.20, ptw=300.0, is_endurance=True
    )
    self.assertIn('front_wear_factor', wear)
    self.assertIn('rear_wear_factor', wear)
    self.assertGreater(wear['front_wear_factor'], 1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_lib_modules.py`
Expected: FAIL with `ImportError` or `NameError` for missing functions.

- [ ] **Step 3: Implement physics functions in `lib/formulas.py`**

Implement:
1. `calculate_acceleration_squat_dive`: Computes drive wheel tractive force limited by tire traction $\mu F_z$, pitch moment $M_p = m \cdot a_x \cdot h_{cg}$, dynamic rear load $\Delta F_{z,r} = M_p / L$, rear squat compression $\Delta z_r = \Delta F_{z,r} / (2 K_{w,r})$, and front lift $\Delta z_f = \Delta F_{z,r} / (2 K_{w,f})$.
2. `calculate_combined_trail_braking_load`: Combines braking pitch deceleration vector ($a_x = 0.55\mu g$), cornering lateral vector ($a_y = 0.80\mu g$) coupled with ARB roll stiffness, and aerodynamic heave force ($0.5 \rho C_L A v^2$).
3. `calculate_tire_wear_index`: Analytical model evaluating tire wear degradation multiplier based on frequency stiffness $(f_n / f_{n,\text{base}})^{1.4}$, alignment slip scrub $(1 + 0.08 |\theta_{\text{toe}}| + 0.04 |\theta_{\text{camber}}|)$, and endurance scaling.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests/test_lib_modules.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lib/formulas.py tests/test_lib_modules.py
git commit -m "feat(physics): implement torque squat, trail-braking load, and tire wear formulas"
```

---

### Task 2: Suspension Equilibrium Solver & Ride Height Optimization

**Files:**
- Modify: `lib/aero_body.py`
- Modify: `lib/springs.py`
- Test: `tests/test_lib_modules.py`

**Interfaces:**
- Consumes: Primitives from `lib/formulas.py`, slider limits, aerodynamic forces, and vehicle geometry.
- Produces:
  - `solve_suspension_equilibrium(...) -> Dict[str, Any]` in `lib/aero_body.py`
  - Mathematical proof metrics: static clearance, dynamic clearance under trail braking, acceleration dynamic rake, bump stop clearance margin, trail-braking pass/fail indicator.

- [ ] **Step 1: Write failing unit test for equilibrium solver**

Add test in `tests/test_lib_modules.py`:
```python
def test_suspension_equilibrium_solver(self):
    res = solve_suspension_equilibrium(
        mass_kg=1400.0, front_ratio=0.54, power_hp=500.0, torque_nm=650.0,
        drivetrain='FR', hcg_m=0.45, wheelbase_m=2.6, track_width_m=1.6,
        mu=1.35, fn_f=2.6, fn_r=2.8, arb_f=4, arb_r=6,
        df_f=120, df_r=200, height_front_range=(90, 140), height_rear_range=(95, 145),
        speed_kmh=220.0
    )
    self.assertIn('optimal_rh_front', res)
    self.assertIn('optimal_rh_rear', res)
    self.assertIn('trail_braking_feasible', res)
    self.assertIn('min_dynamic_clearance_mm', res)
    self.assertGreaterEqual(res['optimal_rh_front'], 90)
    self.assertGreaterEqual(res['min_dynamic_clearance_mm'], 0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_lib_modules.py`
Expected: FAIL with `ImportError: cannot import name 'solve_suspension_equilibrium'`

- [ ] **Step 3: Implement `solve_suspension_equilibrium` in `lib/aero_body.py`**

Replace heuristic additive constants in `calculate_ride_height` with calls to `solve_suspension_equilibrium`:
- Solve for minimum front ground clearance $h_f$:
  $$h_f = h_{\min,f} + \Delta z_{\text{trail-brake}} + \text{Margin}_{\text{bump}} - \text{StrokeFloor}$$
  clamped within $[h_{\min,f}, h_{\max,f}]$.
- If $h_f$ exceeds slider maximum or dynamic clearance $< 12\text{ mm}$, calculate the required spring stiffness increase $\Delta f_{n,f}$ needed to prevent bottoming and enable trail-braking.
- Calculate rear ground clearance $h_r$ to ensure positive aerodynamic rake under maximum velocity and maintain pitch stability under engine torque squat:
  $$h_r \ge h_f + \Delta z_{\text{squat},r} + \text{Rake}_{\text{aero}}$$
- Compute trail-braking feasibility: True if remaining dynamic travel $\ge 12\text{ mm}$, else False with warning and recommended adjustments.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests/test_lib_modules.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lib/aero_body.py lib/springs.py tests/test_lib_modules.py
git commit -m "feat(suspension): replace heuristic heights with physical equilibrium solver"
```

---

### Task 3: Pipeline Integration into Setup Coordinator

**Files:**
- Modify: `setup.py`
- Test: `tests/test_setup_orchestrator.py`

**Interfaces:**
- Consumes: `solve_suspension_equilibrium`, `calculate_tire_wear_index`, `calculate_acceleration_squat_dive`.
- Produces: Enriched `setup_dict` containing:
  - `telemetry.equilibrium_proof`: Acceleration squat, braking dive, dynamic trail-braking clearance, trail-braking feasibility flag.
  - `telemetry.tire_wear_analysis`: Front/rear tire wear index, degradation risk notes.

- [ ] **Step 1: Write failing test in `tests/test_setup_orchestrator.py`**

```python
def test_setup_equilibrium_telemetry(self):
    car = {'name': 'Corvette ZR1', 'mass_kg': 1500, 'drivetrain': 'FR', 'power_hp': 755, 'torque_nm': 969}
    track = {'name': 'Spa-Francorchamps', 'bumpiness': 'medium', 'elevation_diff_m': 100.0}
    res = build_setup(car, track=track, tire='RM')
    self.assertIn('equilibrium_proof', res['telemetry'])
    self.assertIn('tire_wear_analysis', res['telemetry'])
    self.assertIn('trail_braking_feasible', res['telemetry']['equilibrium_proof'])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_setup_orchestrator.py`
Expected: FAIL on missing `equilibrium_proof` in telemetry dict.

- [ ] **Step 3: Update `setup.py` to calculate and inject equilibrium telemetry**

- Pass engine torque (`veh.torque_nm`), power (`veh.power_hp`), and circuit conditions to `solve_suspension_equilibrium`.
- Compute tire degradation factors via `calculate_tire_wear_index`.
- Append clear engineering advisory notes to `endurance_notes` if trail-braking is compromised or if high spring rate will cause premature tire wear.

- [ ] **Step 4: Run all test suites**

Run: `python3 -m unittest discover tests`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add setup.py tests/test_setup_orchestrator.py
git commit -m "feat(orchestrator): integrate physical equilibrium telemetry and tire wear analysis"
```

---

### Task 4: Dual-Language Setup Sheet Rendering in CLI

**Files:**
- Modify: `cli.py`
- Test: `tests/test_cli_output.py` (Create)

**Interfaces:**
- Consumes: Enriched `setup_dict` from `setup.build_setup()`.
- Produces: Formatted English/Thai tuning sheet with new "Equilibrium Proof & Trail-Braking Feasibility" and "Tire Wear Analysis" sections.

- [ ] **Step 1: Write test for setup sheet formatting**

Create `tests/test_cli_output.py`:
```python
import unittest
from cli import format_setup_sheet
from setup import build_setup

class TestCLIOutput(unittest.TestCase):
    def test_format_setup_sheet_contains_proofs(self):
        car = {'name': 'Porsche 911 GT3 RS', 'mass_kg': 1430, 'drivetrain': 'RR', 'power_hp': 520, 'torque_nm': 470}
        setup_dict = build_setup(car, tire='RS')
        sheet = format_setup_sheet(setup_dict)
        self.assertIn('Trail-Braking', sheet)
        self.assertIn('Squat', sheet)
        self.assertIn('Tire Wear', sheet)

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_cli_output.py`
Expected: FAIL

- [ ] **Step 3: Implement new telemetry rendering in `cli.py`**

Add formatted display rows in `format_setup_sheet`:
- Engine Acceleration Squat & Dynamic Rake under torque load.
- Braking Pitch Dive & Trail-Braking Compliance Status (✅ Pass with remaining travel / ⚠️ Fail with bump-stop bottoming warning).
- Front/Rear Tire Wear Degradation Index (% expected wear rate increase relative to baseline).

- [ ] **Step 4: Run all unit tests**

Run: `python3 -m unittest discover tests`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add cli.py tests/test_cli_output.py
git commit -m "feat(cli): render equilibrium proofs, trail-braking compliance, and tire wear metrics"
```
