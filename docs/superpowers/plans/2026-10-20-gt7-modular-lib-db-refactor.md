# GT7 Suspension Tuning Modular Architecture Refactor (lib / db / outside)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the codebase into a clean, modular library package architecture following the user's specification (`lib/` for calculation modules, `db/` for data loading and queries, and `outside` for models, setup orchestrator, and CLI), while maintaining 100% backward compatibility and green status for all existing tests.

**Architecture:**
- `lib/`: Pure calculation domain separated into single-responsibility modules:
  1. `formulas.py`: Fundamental physics formulas (wheel rate, load transfer, pitch, roll, heave).
  2. `springs.py`: Natural frequencies, flat ride synchronization, anti-roll bars (LLTD).
  3. `shocks.py`: Damping compression and rebound, critical damping ratios, anti-squat.
  4. `wheels.py`: Wheel alignment (camber, toe), tire friction coefficients, dynamic brake bias.
  5. `aero_body.py`: Ride height, center-of-pressure downforce balance, high-speed trail-braking bottoming simulation.
  6. `drivetrain.py`: Differential LSD lockup sensitivity, transmission top speed auto-gearing.
  7. `trims.py`: Closed-loop telemetry trims and quick-trims delta table generators.
- `db/`: Data loading and querying layer:
  1. `loader.py`: JSON database parser and caching.
  2. `interface.py`: Clean querying API (`get_car`, `get_track`, slider bounds registry).
- `outside` (root / package level):
  1. `models.py`: Immutable domain dataclasses (`VehicleSpec`, `TrackSpec`).
  2. `setup.py`: Core setup calculation coordinator (`build_setup`).
  3. `cli.py`: User-facing CLI entry point, argument parsing, setup sheet formatter.
  4. `constants.py`: Centralized physical constants and GT7 slider invariants.
- Facades: `scripts/gt7_dynamics.py` and `scripts/gt7_tuner.py` re-export from `lib/` and `outside/` to prevent breaking existing CLI calls and unit tests.

**Tech Stack:** Python 3.10+, standard library (`dataclasses`, `typing`, `math`, `unittest`, `argparse`).

**Spec:** User architecture prompt received 2026-10-20.

## Global Constraints
- Every module in `lib/` must have single responsibility and zero side-effects.
- Preserve 100% of mathematical formulas and numerical results across all existing 28 unit tests.
- Maintain identical CLI interface flags and setup sheet output text.
- Preserve backward compatibility for existing callers of `gt7_dynamics.py`, `gt7_db.py`, and `gt7_tuner.py`.

## Review Focus
1. `lib/springs.py` natural frequency formulas must match exact values produced by `gt7_dynamics.py`.
2. `lib/shocks.py` damping compression must enforce the GT7 legal 40% ceiling.
3. `lib/wheels.py` must correctly handle tire-saver camber cap (-2.4°) and low-scrub toe.
4. `lib/aero_body.py` trail-braking bottoming simulation must produce identical dynamic clearance and bump recommendations.
5. All 28 legacy tests in `tests/test_gt7_dynamics.py` must pass through the facade without modification.

---

### Task 1: Build the `db/` Subsystem (`loader.py` & `interface.py`)

**Files:**
- Create: `db/__init__.py`
- Create: `db/loader.py`
- Create: `db/interface.py`
- Test: `tests/test_db_interface.py`

**Interfaces:**
- `db.loader.load_database(filename: str) -> Dict[str, Any]`
- `db.interface.get_car(name_or_id: str) -> Optional[Dict[str, Any]]`
- `db.interface.get_track(name_or_id: str) -> Optional[Dict[str, Any]]`
- `db.interface.get_slider_ranges(car_id: str) -> Dict[str, Any]`

- [ ] **Step 1: Write failing test in `tests/test_db_interface.py`**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `db/loader.py` and `db/interface.py`**
- [ ] **Step 4: Wire `scripts/gt7_db.py` to forward to `db.interface`**
- [ ] **Step 5: Run unit tests to verify pass**

---

### Task 2: Build the `lib/` Calculation Modules

**Files:**
- Create: `lib/__init__.py`
- Create: `lib/formulas.py`
- Create: `lib/springs.py`
- Create: `lib/shocks.py`
- Create: `lib/wheels.py`
- Create: `lib/aero_body.py`
- Create: `lib/drivetrain.py`
- Create: `lib/trims.py`
- Test: `tests/test_lib_modules.py`

**Interfaces:**
- `lib.formulas`: `calculate_wheel_rate`, `calculate_sprung_mass`, `calculate_braking_pitch_dive`, `calculate_cornering_roll_deflection`, `calculate_aerodynamic_heave`
- `lib.springs`: `calculate_natural_frequencies`, `calculate_anti_roll_bars`
- `lib.shocks`: `calculate_dampers`
- `lib.wheels`: `calculate_wheel_alignment`, `calculate_brake_bias`, `get_tire_mu`
- `lib.aero_body`: `calculate_ride_height`, `calculate_aerodynamics`, `simulate_high_speed_trail_braking`
- `lib.drivetrain`: `calculate_differential_lsd`, `calculate_top_speed`
- `lib.trims`: `apply_closed_loop_trim`, `build_quick_trims`

- [ ] **Step 1: Write failing test in `tests/test_lib_modules.py`**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `lib/` modules migrating logic from `gt7_dynamics.py`**
- [ ] **Step 4: Expose all functions cleanly in `lib/__init__.py`**
- [ ] **Step 5: Run test to verify all `lib` tests pass**

---

### Task 3: Build the `outside/` Top-Level Layer (`models.py`, `setup.py`, `cli.py`, `constants.py`)

**Files:**
- Create: `constants.py` (canonical constants)
- Create: `models.py` (VehicleSpec, TrackSpec)
- Create: `setup.py` (Setup orchestrator / synthesizer calling `lib/`)
- Create: `cli.py` (CLI entry point & setup sheet formatter)

**Interfaces:**
- `setup.build_setup(car, track, ...) -> Dict[str, Any]`
- `cli.format_setup_sheet(setup_dict) -> str`
- `cli.main()`

- [ ] **Step 1: Write test for `setup.py` in `tests/test_setup_orchestrator.py`**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `constants.py`, `models.py`, `setup.py`, and `cli.py`**
- [ ] **Step 4: Run test to verify `setup.py` passes**

---

### Task 4: Connect Facades & Backward Compatibility

**Files:**
- Modify: `scripts/gt7_dynamics.py` (re-export all from `lib/`)
- Modify: `scripts/gt7_tuner.py` (re-export `build_setup`, `format_setup_sheet`, `main` from `setup.py` and `cli.py`)
- Modify: `scripts/gt7_db.py` (re-export from `db/`)

- [ ] **Step 1: Update `scripts/gt7_dynamics.py` as pure re-export facade**
- [ ] **Step 2: Update `scripts/gt7_tuner.py` as wrapper**
- [ ] **Step 3: Run full legacy test suite `python3 -m unittest discover -s tests -v`**
- [ ] **Step 4: Verify all tests pass with zero regression**

---

### Task 5: Final Review & Benchmark Proofs

**Files:**
- Review: `lib/`, `db/`, `models.py`, `setup.py`, `cli.py`, `constants.py`

- [ ] **Step 1: Run F355 Widebody 240 km/h benchmark**
- [ ] **Step 2: Run X2019 Maggiore 280 km/h benchmark**
- [ ] **Step 3: Run Civic Type R Time Attack benchmark**
- [ ] **Step 4: Run Subaru WRX Dirt benchmark**
- [ ] **Step 5: Full test suite verification**
