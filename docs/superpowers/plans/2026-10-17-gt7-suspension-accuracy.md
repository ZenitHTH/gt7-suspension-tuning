# GT7 Suspension Setup Accuracy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase suspension setup accuracy in `gt7_dynamics.py`, `gt7_tuner.py`, and `gt7_db.py` by wiring track elevation/downforce/straight telemetry into the physics solver, coupling aerodynamic downforce into spring frequencies, persisting per-car slider ranges, and adding closed-loop telemetry/symptom trim adjustments.

**Architecture:** Extend pure mathematical solvers in `scripts/gt7_dynamics.py` to accept track elevation, downforce demand, aerodynamic vertical load, and closed-loop handling trims while keeping zero external dependencies. Update `scripts/gt7_db.py` to persist per-car slider ranges into `data/cars_master.json`, and wire the new parameters and CLI flags (`--save-sliders`, `--stability`, `--symptom`) in `scripts/gt7_tuner.py`.

**Tech Stack:** Python 3 standard library (`math`, `json`, `argparse`, `unittest`, `typing`).

**Spec:** `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/SKILL.md` (Sections 0.A, 2.A, 2.E, 3.A–3.F, 4, 8, 9).

## Global Constraints

- Zero third-party Python dependencies (standard library only).
- All existing calls to `gt7_dynamics` functions must remain backward-compatible via default parameter values.
- All outputs must respect GT7 in-game slider bounds: ARB `1..10`, Damping `20..80%`, LSD Initial `4..30`, LSD Accel/Brake `5..65`, Brake Bias `-5..+5` (`0..+5` on `FF`).
- `Gr.4` AWD cars must keep `awd_torque_split = 'Fixed (Homologation / ปรับไม่ได้ใน Gr.4)'` under all trim modes.

## Review Focus

- `track` dictionary with `None` or missing `elevation_diff_m`, `downforce_demand`, or `longest_straight_m`: must fall back to `0.0`, `'medium'`, and `0.0` without raising `TypeError`. (Tested in Task 1 `test_track_telemetry_missing_keys_fallback`)
- High aerodynamic downforce when custom `fn_front_range` / `fn_rear_range` is provided: aerodynamic frequency boost must never exceed `f_max_f` or `f_max_r`. (Tested in Task 2 `test_downforce_frequency_coupling_clamped_to_slider_max`)
- Partial `--save-sliders` invocation (e.g., saving only `df_front` and `df_rear` on a car that already has saved `height_range`): must merge into existing `slider_ranges` dict without erasing prior keys. (Tested in Task 3 `test_save_and_autoload_slider_ranges_partial_merge`)
- Extreme or stacked `--stability` and `--symptom` inputs: must clamp ARB within `1..10`, LSD within `5..65`, and prevent negative brake bias on `FF` cars. (Tested in Task 4 `test_closed_loop_trim_clamps_to_gt7_legal_bounds`)
- `Gr.4` AWD car with `--symptom entry_push`: must adjust ARB, LSD, and rake without unlocking `awd_torque_split`. (Tested in Task 4 `test_gr4_awd_preserves_fixed_split_under_symptom_trim`)

---

### Task 1: Track Telemetry Wiring (Elevation, Downforce Demand, Straight Gearing)

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:34-80`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:186-217`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:313-365`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:56-85`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: `track` dict from `data/tracks_master.json` (`elevation_diff_m`, `downforce_demand`, `longest_straight_m`, `bumpiness`, `is_oval`)
- Produces:
  - `gt7_dynamics.calculate_ride_height(..., elevation_diff_m: float = 0.0) -> Tuple[int, int]`
  - `gt7_dynamics.calculate_dampers(..., elevation_diff_m: float = 0.0) -> Tuple[int, int, int, int]`
  - `gt7_dynamics.calculate_aerodynamics(..., downforce_demand: str = 'medium') -> Dict[str, Any]`
  - `gt7_dynamics.calculate_top_speed(power: float, ptw: float, longest_straight_m: float = 0.0, is_oval: bool = False) -> int`

- [ ] **Step 1: Write the failing tests in `tests/test_gt7_dynamics.py`**

```python
    def test_elevation_crest_ride_height_and_dampers(self):
        # Steep elevation track (>= 50m like SUGO 69.8m or Bathurst 174m) adds ride height buffer and rear rebound
        rh_flat = gt7_dynamics.calculate_ride_height(bumpiness='medium', wf=0.50, elevation_diff_m=10.0)
        rh_steep = gt7_dynamics.calculate_ride_height(bumpiness='medium', wf=0.50, elevation_diff_m=69.8)
        self.assertEqual(rh_steep[0], rh_flat[0] + 4)

        _, _, _, exp_r_flat = gt7_dynamics.calculate_dampers(bumpiness='medium', ptw=300.0, elevation_diff_m=10.0)
        comp_f, comp_r, _, exp_r_steep = gt7_dynamics.calculate_dampers(bumpiness='medium', ptw=300.0, elevation_diff_m=69.8)
        self.assertGreater(exp_r_steep, exp_r_flat)
        self.assertGreaterEqual(exp_r_steep / comp_r, 1.48)

    def test_aerodynamics_downforce_demand_scaling(self):
        df_low = gt7_dynamics.calculate_aerodynamics((100, 200), (200, 400), wf=0.50, downforce_demand='low')
        df_med = gt7_dynamics.calculate_aerodynamics((100, 200), (200, 400), wf=0.50, downforce_demand='medium')
        df_high = gt7_dynamics.calculate_aerodynamics((100, 200), (200, 400), wf=0.50, downforce_demand='high')
        self.assertEqual((df_low['front'], df_low['rear']), (140, 280))
        self.assertEqual((df_med['front'], df_med['rear']), (160, 320))
        self.assertEqual((df_high['front'], df_high['rear']), (180, 350))

    def test_calculate_top_speed_by_straight_length(self):
        v_short = gt7_dynamics.calculate_top_speed(power=400, ptw=300, longest_straight_m=450)
        v_long = gt7_dynamics.calculate_top_speed(power=400, ptw=300, longest_straight_m=1500)
        self.assertGreater(v_long, v_short)

    def test_track_telemetry_missing_keys_fallback(self):
        import gt7_tuner
        car = {'id': '9999', 'name': 'Test Car', 'drivetrain': 'FR', 'mass_kg': 1350, 'balance': {'front_pct': 50}}
        sparse_track = {'name': 'Sparse Circuit', 'bumpiness': None, 'elevation_diff_m': None, 'downforce_demand': None, 'longest_straight_m': None}
        setup = gt7_tuner.build_setup(car=car, track=sparse_track)
        self.assertIn('ride_height_mm', setup['parameters'])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `TypeError: calculate_ride_height() got an unexpected keyword argument 'elevation_diff_m'`

- [ ] **Step 3: Implement track telemetry parameters in `scripts/gt7_dynamics.py` and wire in `scripts/gt7_tuner.py`**

In `scripts/gt7_dynamics.py`:
- Add `elevation_diff_m: float = 0.0` to `calculate_ride_height`: compute `elev_buf = 4 if (not is_dirt and (elevation_diff_m or 0.0) >= 50.0) else 0` and add `elev_buf` to `base_f` before applying `rake` and slider max clamping.
- Add `elevation_diff_m: float = 0.0` to `calculate_dampers`: set `exp_r_mult = 1.50 if (elevation_diff_m or 0.0) >= 50.0 else 1.38` and `exp_r = round(comp_r * exp_r_mult)`.
- Add `downforce_demand: str = 'medium'` to `calculate_aerodynamics`: for balanced cars (`wf < 0.55`, non-oval, non-fixed-front), select `(ratio_f, ratio_r)` from `{'low': (0.40, 0.40), 'medium': (0.60, 0.60), 'high': (0.80, 0.75)}.get(downforce_demand or 'medium', (0.60, 0.60))`. When `wf >= 0.55`, scale rear ratio by `-0.05` on `'low'` and `+0.10` on `'high'`.
- Add `calculate_top_speed(power: float, ptw: float, longest_straight_m: float = 0.0, is_oval: bool = False) -> int`: base speed `230` (`power < 300`), `260` (`< 450`), `285` (`< 650`), `315` (`>= 650`), plus `+15` if `(longest_straight_m or 0.0) >= 1100 or is_oval`, `-10` if `0 < (longest_straight_m or 0.0) <= 550`, rounded to nearest 10 km/h.
- In `scripts/gt7_tuner.py:build_setup`, extract `elevation_diff_m = float((track or {}).get('elevation_diff_m') or 0.0)`, `downforce_demand = (track or {}).get('downforce_demand') or 'medium'`, `longest_straight_m = float((track or {}).get('longest_straight_m') or 0.0)`, and `bumpiness = (track or {}).get('bumpiness') or 'medium'`, and pass them to the four functions.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (10 tests)

---

### Task 2: Aerodynamic Downforce-to-Natural-Frequency ($f_n$) Coupling

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:81-155`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:68-78`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: `df['front']` and `df['rear']` from `gt7_dynamics.calculate_aerodynamics`
- Produces: `gt7_dynamics.calculate_natural_frequencies(..., df_front: int = 0, df_rear: int = 0) -> Tuple[float, float, float]`

- [ ] **Step 1: Write the failing tests in `tests/test_gt7_dynamics.py`**

```python
    def test_downforce_frequency_coupling(self):
        fn_low_df = gt7_dynamics.calculate_natural_frequencies(mu=1.45, wf=0.50, df_front=75, df_rear=110)
        fn_high_df = gt7_dynamics.calculate_natural_frequencies(mu=1.45, wf=0.50, df_front=400, df_rear=600)
        self.assertGreater(fn_high_df[0], fn_low_df[0])
        self.assertGreater(fn_high_df[1], fn_low_df[1])

    def test_downforce_frequency_coupling_clamped_to_slider_max(self):
        fn_f, fn_r, _ = gt7_dynamics.calculate_natural_frequencies(
            mu=1.65, wf=0.50, mass=2100.0,
            fn_front_range=(2.00, 3.10), fn_rear_range=(2.00, 3.20),
            df_front=900, df_rear=1400
        )
        self.assertLessEqual(fn_f, 3.10)
        self.assertLessEqual(fn_r, 3.20)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `TypeError: calculate_natural_frequencies() got an unexpected keyword argument 'df_front'`

- [ ] **Step 3: Implement downforce load scaling in `calculate_natural_frequencies` and reorder call in `gt7_tuner.py`**

In `scripts/gt7_dynamics.py:calculate_natural_frequencies`:
- Add `df_front: int = 0, df_rear: int = 0` parameters.
- Compute `aero_boost_f = min(0.35, max(0.0, (df_front - 100) * 0.00035))` and `aero_boost_r = min(0.40, max(0.0, (df_rear - 150) * 0.00030))` (0.0 when `is_dirt` is True).
- When `fn_front_range` and `fn_rear_range` are provided, add `aero_boost_f` / `aero_boost_r` to `target_f` / `target_r` and clamp with `min(f_max_f, max(f_min_f, ...))` and `min(f_max_r, max(f_min_r, ...))`.
- In the road/Gr.4 branch, add `aero_boost_f` to `f_front` and `aero_boost_r` to `f_rear` before rounding.
- In `scripts/gt7_tuner.py:build_setup`, call `calculate_aerodynamics` before `calculate_natural_frequencies` and pass `df_front=df['front'], df_rear=df['rear']`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (12 tests)

---

### Task 3: Persistent Per-Car Slider Ranges (`--save-sliders`)

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_db.py:98-115`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:26-46`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:240-290`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: user CLI slider arguments (`--df-front`, `--df-rear`, `--height-range`, `--height-front`, `--height-rear`, `--fn-front`, `--fn-rear`)
- Produces:
  - `gt7_db.save_car_sliders(car_id: str, sliders: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]`
  - Automatic loading of `car.get('slider_ranges', {})` in `gt7_tuner.build_setup`

- [ ] **Step 1: Write the failing test in `tests/test_gt7_dynamics.py`**

```python
    def test_save_and_autoload_slider_ranges_partial_merge(self):
        import tempfile, json, gt7_db, gt7_tuner
        sample_cars = [{
            'id': '3614', 'name': "Ferrari F355 Berlinetta '94",
            'drivetrain': 'MR', 'mass_kg': 1350, 'balance': {'front_pct': 42}
        }]
        with tempfile.NamedTemporaryFile('w+', suffix='.json', delete=False) as tf:
            json.dump(sample_cars, tf)
            temp_path = tf.name
        try:
            gt7_db.save_car_sliders('3614', {'height_range': [85, 135]}, db_path=temp_path)
            merged = gt7_db.save_car_sliders('3614', {'df_front': [100, 200], 'df_rear': [200, 350]}, db_path=temp_path)
            self.assertEqual(merged['height_range'], [85, 135])
            self.assertEqual(merged['df_front'], [100, 200])

            with open(temp_path, 'r', encoding='utf-8') as f:
                saved_car = json.load(f)[0]
            setup = gt7_tuner.build_setup(car=saved_car)
            self.assertEqual(setup['parameters']['downforce']['range_f'], '100-200')
            self.assertEqual(setup['parameters']['ride_height_mm']['range'], '85-135')
        finally:
            os.remove(temp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `AttributeError: module 'gt7_db' has no attribute 'save_car_sliders'`

- [ ] **Step 3: Implement `save_car_sliders` in `scripts/gt7_db.py` and auto-loading + `--save-sliders` in `scripts/gt7_tuner.py`**

- In `scripts/gt7_db.py`: implement `save_car_sliders(car_id: str, sliders: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]` which loads the target JSON file (default `os.path.join(DATA_DIR, 'cars_master.json')`), finds the car with `str(c.get('id')) == str(car_id)`, merges non-`None` entries from `sliders` into `c.setdefault('slider_ranges', {})`, updates `CARS_DB` in memory if using default `db_path`, writes the JSON back with `indent=2, ensure_ascii=False`, and returns the merged `slider_ranges` dict.
- In `scripts/gt7_tuner.py:build_setup`: read `saved = car.get('slider_ranges') or {}` and for each of `df_front_range`, `df_rear_range`, `height_range`, `height_front_range`, `height_rear_range`, `fn_front_range`, `fn_rear_range`, fall back to `tuple(saved[key])` if the argument is `None` and `key` exists in `saved`.
- In `scripts/gt7_tuner.py:main`: add `--save-sliders` boolean flag (`action='store_true'`). When set, call `gt7_db.save_car_sliders(car['id'], ...)` with any provided range flags.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (13 tests)

---

### Task 4: Closed-Loop Telemetry (`--stability`) & Handling Symptom Trim (`--symptom`)

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:345-365`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:19-35`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:125-146`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:235-295`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: baseline `parameters` dict in `gt7_tuner.build_setup`, optional `stability: Optional[Tuple[float, float]] = None`, optional `symptoms: Optional[List[str]] = None`
- Produces: `gt7_dynamics.apply_closed_loop_trim(parameters: Dict[str, Any], stability: Optional[Tuple[float, float]] = None, symptoms: Optional[List[str]] = None, drivetrain: str = 'FR', group: str = 'Road Car') -> Dict[str, Any]`

- [x] **Step 1: Write the failing tests in `tests/test_gt7_dynamics.py`**

```python
    def test_closed_loop_trim_clamps_to_gt7_legal_bounds(self):
        import gt7_tuner
        car = {'id': '1', 'name': 'FF Hatch', 'drivetrain': 'FF', 'group': 'Road Car', 'mass_kg': 1100, 'balance': {'front_pct': 63}}
        setup = gt7_tuner.build_setup(
            car=car,
            stability=(-0.95, 0.85),
            symptoms=['entry_push', 'exit_snap', 'bottoming', 'curb_hop']
        )
        p = setup['parameters']
        self.assertGreaterEqual(p['anti_roll_bar']['front'], 1)
        self.assertLessEqual(p['anti_roll_bar']['rear'], 10)
        self.assertGreaterEqual(p['lsd_rear']['brake'], 5)
        self.assertLessEqual(p['lsd_rear']['brake'], 65)
        self.assertGreaterEqual(p['brake_bias'], 0)  # FF must never get negative rear brake bias

    def test_gr4_awd_preserves_fixed_split_under_symptom_trim(self):
        import gt7_tuner
        car = {'id': '2', 'name': 'WRX Gr.4', 'drivetrain': 'AWD', 'group': 'Gr.4', 'mass_kg': 1300, 'balance': {'front_pct': 56}}
        setup = gt7_tuner.build_setup(car=car, symptoms=['entry_push'])
        self.assertEqual(setup['parameters']['awd_torque_split'], 'Fixed (Homologation / ปรับไม่ได้ใน Gr.4)')
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `TypeError: build_setup() got an unexpected keyword argument 'stability'`

- [x] **Step 3: Implement `apply_closed_loop_trim` in `scripts/gt7_dynamics.py` and wire CLI flags in `scripts/gt7_tuner.py`**

In `scripts/gt7_dynamics.py`:
- Implement `apply_closed_loop_trim(parameters: Dict[str, Any], stability: Optional[Tuple[float, float]] = None, symptoms: Optional[List[str]] = None, drivetrain: str = 'FR', group: str = 'Road Car') -> Dict[str, Any]`:
  - If `stability` `(low_s, high_s)` is provided:
    - If `low_s <= -0.25`: `arb.front -= 1`, `arb.rear += 1`, `lsd_rear.brake -= 4`, and if `drivetrain != 'FF'`: `brake_bias -= 1`.
    - If `high_s >= 0.20`: `damping_expansion_pct.rear += 4`, `lsd_rear.brake += 6`.
  - For each `sym` in `symptoms or []`:
    - `'entry_push'`: `arb.front -= 1`, `arb.rear += 1`, `lsd_rear.brake -= 4`, `ride_height_mm.rear += 3`, and if `drivetrain != 'FF'`: `brake_bias -= 1`.
    - `'exit_snap'`: `lsd_rear.accel -= 4`, `damping_compression_pct.rear += 2`, `arb.rear -= 1`.
    - `'bottoming'`: `ride_height_mm.front += 5`, `ride_height_mm.rear += 5`, `damping_compression_pct.front += 2`, `damping_compression_pct.rear += 2`.
    - `'curb_hop'`: `arb.front -= 1`, `arb.rear -= 1`, `damping_compression_pct.front -= 2`, `damping_compression_pct.rear -= 2`, `ride_height_mm.front += 3`, `ride_height_mm.rear += 3`.
  - Clamp: `arb` `1..10`, `damping_compression_pct` and `damping_expansion_pct` `20..80`, `lsd_rear.init` `4..30`, `lsd_rear.accel` and `lsd_rear.brake` `5..65`, `brake_bias` `0..5` if `drivetrain == 'FF'` else `-5..5`.
- In `scripts/gt7_tuner.py`:
  - Add `stability: Optional[Tuple[float, float]] = None` and `symptoms: Optional[List[str]] = None` to `build_setup`, call `gt7_dynamics.apply_closed_loop_trim`, and add CLI flags `--stability` (`nargs=2, type=float, metavar=('LOW', 'HIGH')`) and `--symptom` (`nargs='+', choices=['entry_push', 'exit_snap', 'bottoming', 'curb_hop']`).

- [x] **Step 4: Run full test suite and CLI smoke test**

Run: `python3 -m unittest discover -s tests -v && python3 scripts/gt7_tuner.py "Ferrari F355 Berlinetta '94" -t "SUGO" --stability -0.35 0.25 --symptom entry_push`
Expected: PASS (15 tests) and formatted setup sheet printed with closed-loop trims applied.
