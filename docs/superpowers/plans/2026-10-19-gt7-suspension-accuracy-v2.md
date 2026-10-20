# GT7 Suspension Setup Accuracy v2 (Spec IV / 1.72+) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate physics accuracy gaps between `SKILL.md` (Update 1.72+ Spec IV) and the Python synthesizer (`gt7_dynamics.py`, `gt7_tuner.py`, `patch_db.py`) across Group X/B normalization, pre-seeded in-game slider ranges, widebody fender clearance, Center-of-Pressure (CP) endurance downforce, MR/RR tire-saver alignment, the Section 2.F Quick-Trims delta table, and a high-speed (`v km/h`) aero + trail-braking outside-front suspension compression & bottoming simulator.

**Architecture:** Normalize upstream database group codes (`'X' -> 'Gr.X'`, `'B' -> 'Gr.B'`, `'N' -> 'Road Car'`) and pre-seed verified in-game slider bounds in `data/cars_master.json` via `scripts/patch_db.py`. Refine the pure first-principles functions in `scripts/gt7_dynamics.py` to account for `--widebody` front fender travel buffers, rear-biased MR/RR aerodynamic CP in endurance mode, MR/RR rear toe-in stability floors, GT7's 20–40% compression damping ceiling, and combined aero + braking pitch + cornering roll outside-front compression at velocity `v km/h` (`--speed`), auto-raising ride height if the car would bottom out or hit the fender under high-speed trail-braking.

**Tech Stack:** Python 3 standard library (`math`, `json`, `argparse`, `unittest`, `typing`).

**Spec:** `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/SKILL.md` (Sections 0, 0.A, 2.E, 2.F, 3.A–3.F, 6, 8.D).

## Global Constraints

- Zero third-party Python dependencies (standard library only).
- All existing function signatures in `gt7_dynamics.py` and `gt7_tuner.py` must remain backward-compatible via default parameter values; all 15 existing unit tests in `tests/test_gt7_dynamics.py` must continue to pass.
- All outputs must respect GT7 in-game slider bounds: ARB `1..10`, Damping Compression `20..40%`, Damping Expansion `30..80%`, LSD Initial `4..30`, LSD Accel/Brake `5..65`, Brake Bias `-5..+5` (`0..+5` on `FF`).
- `Gr.4` AWD cars must keep `awd_torque_split = 'Fixed (Homologation / ปรับไม่ได้ใน Gr.4)'` under all trim modes.

## Review Focus

- Upstream cars with shorthand group strings (`'X'`, `'B'`, `'N'`) such as `Gran Turismo Red Bull X2019 Competition` (`group: 'X'`, `650 kg`): must be classified as `'Gr.X'` racecars rather than `is_ultralight` road cars so ride height, natural frequency, and downforce never fall outside in-game slider bounds. (Tested in Task 1 `test_group_x_normalization_and_x2019_preseeded_sliders`)
- Widebody road cars with `--widebody` on bumpy or steep tracks: must add `+5 mm` front ride height buffer and preserve positive rake without exceeding `height_range` / `height_front_range` slider maximums. (Tested in Task 2 `test_widebody_fender_clearance_clamped_to_slider_max`)
- Fixed-front-aero cars (`span_f == 0`, e.g., `Toyota Supra GT Road Car` `200-200 / 400-500`) in `endurance` mode: must retain the anti-push rear floor clamp (`200 / 400`) rather than applying the MR/RR endurance ratio. (Tested in Task 2 `test_endurance_aerodynamics_cp_and_fixed_front_clamp`)
- High-power MR/RR cars (`wr >= 0.54`, `power >= 500 HP`) in `endurance` (tire-saver) mode: must keep rear toe-in between `In 0.12°` and `In 0.22°` and front camber at `-2.2°` on Racing Medium tires, never dropping rear toe to unstable `In 0.07°`. (Tested in Task 3 `test_mr_endurance_alignment_and_maggiore_brake_bias`)
- High-speed trail-braking (`--speed 240` or higher) with soft springs / low ride height / widebody: outside-front combined compression ($\Delta z_{\text{aero}} + \Delta z_{\text{pitch}} + \Delta z_{\text{roll}}$) must detect bump-stop/fender contact (`bottoming_or_fender_hit == True`) and auto-guard ride height within slider bounds. (Tested in Task 5 `test_high_speed_trail_brake_compression_and_bottoming_guard`)

---

### Task 1: Group Code Normalization & Pre-Seeded Verified Slider Ranges

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:20-33, 106-138, 368-380`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:60-96`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/patch_db.py:27-105`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: `car['group']` and `car['slider_ranges']` from `data/cars_master.json`
- Produces:
  - `gt7_dynamics.normalize_group(group: Optional[str]) -> str`
  - Pre-seeded `slider_ranges` in `scripts/patch_db.py` (`CARS_PATCHES`) and `data/cars_master.json` for IDs `3342`, `3374`, `3517`, `3440`, `3385`, `3387`, `3596`, `3614`

- [ ] **Step 1: Write the failing test in `tests/test_gt7_dynamics.py`**

```python
    def test_group_x_normalization_and_x2019_preseeded_sliders(self):
        import gt7_db, gt7_tuner
        self.assertEqual(gt7_dynamics.normalize_group('X'), 'Gr.X')
        self.assertEqual(gt7_dynamics.normalize_group('B'), 'Gr.B')
        self.assertEqual(gt7_dynamics.normalize_group('N'), 'Road Car')

        x2019 = gt7_db.get_car('3374')
        setup = gt7_tuner.build_setup(car=x2019, tire='RM', mode='endurance')
        p = setup['parameters']
        self.assertTrue(45 <= p['ride_height_mm']['front'] <= 55)
        self.assertTrue(50 <= p['ride_height_mm']['rear'] <= 65)
        self.assertTrue(5.00 <= p['natural_frequency_hz']['front'] <= 5.30)
        self.assertTrue(5.30 <= p['natural_frequency_hz']['rear'] <= 5.55)
        self.assertTrue(800 <= p['downforce']['front'] <= 1200)
        self.assertTrue(1200 <= p['downforce']['rear'] <= 1600)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_gt7_dynamics.TestGT7Dynamics.test_group_x_normalization_and_x2019_preseeded_sliders -v`
Expected: FAIL with `AttributeError: module 'gt7_dynamics' has no attribute 'normalize_group'`

- [ ] **Step 3: Implement `normalize_group`, `Gr.X` endurance frequency scaling, and `patch_db.py` slider patches**

- In `scripts/gt7_dynamics.py`:
  - Add `normalize_group(group: Optional[str]) -> str` mapping `'X' -> 'Gr.X'`, `'B' -> 'Gr.B'`, `'N' -> 'Road Car'`, defaulting empty/`None` to `'Road Car'`. Call `group = normalize_group(group)` at the top of `calculate_sprung_mass`, `calculate_natural_frequencies`, `calculate_aerodynamics`, and `apply_closed_loop_trim`.
  - In `calculate_natural_frequencies`, when `fn_front_range` and `fn_rear_range` are present and `any(g in group for g in ['Gr.1', 'Gr.2', 'Gr.3', 'Gr.X'])`: use `pct_f, pct_r = (0.40, 0.50)` when `is_endurance` is `True` else `(0.75, 0.78)` so that after adding `aero_boost_f` (`0.35`) and `aero_boost_r` (`0.40`) on `[4.00, 6.00]`, endurance lands at `5.15 Hz / 5.40 Hz`.
  - In `calculate_aerodynamics`, add fallback before `if group == 'Gr.1':`: `if group == 'Gr.X': return {'front': 980 if is_endurance else 1040, 'rear': 1420 if is_endurance else 1440, 'range_f': '800-1200', 'range_r': '1200-1600', 'preset': 'High Downforce Prototype'}`.
- In `scripts/gt7_tuner.py:build_setup`:
  - Set `group = gt7_dynamics.normalize_group(car.get('group', 'Road Car'))`.
  - Set `is_ultralight = (not is_racecar) and (mass <= 750 or any(k in car_name for k in ['Caterham', 'Seven', 'Mono', 'Radical', 'Kart']))` so `Gr.X` prototypes (`is_racecar=True`) never fall into the road ultralight branch.
- In `scripts/patch_db.py`:
  - Add `slider_ranges` entries to `CARS_PATCHES` for:
    - `"3342"` (F1500T-A): `{"height_front": [45, 60], "height_rear": [45, 60], "fn_front": [4.0, 6.0], "fn_rear": [4.0, 6.0], "df_front": [700, 900], "df_rear": [1300, 1700]}`
    - `"3374"` & `"3517"` (Red Bull X2019 Competition & 25th Anniversary): `{"height_front": [45, 55], "height_rear": [50, 65], "fn_front": [4.0, 6.0], "fn_rear": [4.0, 6.0], "df_front": [800, 1200], "df_rear": [1200, 1600]}`
    - `"3440"` (911 Turbo S Leichtbau '93): `{"df_front": [50, 200], "df_rear": [140, 290]}`
    - `"3385"` (911 Turbo 930 '81): `{"df_front": [50, 200], "df_rear": [100, 250]}`
    - `"3387"` (Camaro ZL1 1LE '18): `{"df_front": [200, 250], "df_rear": [300, 350]}`
    - `"3596"` (Supra GT Road Car JZA80): `{"height_front": [65, 105], "height_rear": [65, 105], "fn_front": [1.5, 3.5], "fn_rear": [1.5, 3.5], "df_front": [200, 200], "df_rear": [400, 500]}`
    - `"3614"` (Ferrari F355 Berlinetta '94): `{"df_front": [50, 200], "df_rear": [100, 250]}`
  - Run `python3 scripts/patch_db.py` to apply to `data/cars_master.json`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 scripts/patch_db.py && python3 -m unittest tests.test_gt7_dynamics.TestGT7Dynamics.test_group_x_normalization_and_x2019_preseeded_sliders -v`
Expected: PASS

---

### Task 2: Widebody Fender-Clearance (`--widebody`) & Center-of-Pressure (CP) Endurance Downforce

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:34-83, 326-367`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:19-40, 97-115, 293-380`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: `is_widebody: bool = False`, `is_endurance: bool = False`, `wf: float`
- Produces:
  - `gt7_dynamics.calculate_ride_height(..., elevation_diff_m: float = 0.0, is_widebody: bool = False) -> Tuple[int, int]`
  - `gt7_dynamics.calculate_aerodynamics(..., is_oval: bool = False, downforce_demand: str = 'medium', is_endurance: bool = False) -> Dict[str, Any]`
  - `gt7_tuner.build_setup(..., is_widebody: bool = False) -> Dict[str, Any]` and CLI flag `--widebody`

- [ ] **Step 1: Write the failing tests in `tests/test_gt7_dynamics.py`**

```python
    def test_widebody_fender_clearance_clamped_to_slider_max(self):
        rh_std = gt7_dynamics.calculate_ride_height(wf=0.42, is_widebody=False)
        rh_wb = gt7_dynamics.calculate_ride_height(wf=0.42, is_widebody=True)
        self.assertEqual(rh_wb[0], rh_std[0] + 5)
        self.assertEqual(rh_wb[1] - rh_wb[0], rh_std[1] - rh_std[0])

        rh_clamped = gt7_dynamics.calculate_ride_height(
            wf=0.50, height_front_range=(90, 100), height_rear_range=(90, 105),
            elevation_diff_m=70.0, is_widebody=True
        )
        self.assertLessEqual(rh_clamped[0], 100)
        self.assertLessEqual(rh_clamped[1], 105)

    def test_endurance_aerodynamics_cp_and_fixed_front_clamp(self):
        # F355 (wf=0.42) with 50-200 / 100-250 in endurance mode -> 40% front (110) / 70% rear (205)
        df_f355 = gt7_dynamics.calculate_aerodynamics(
            df_front_range=(50, 200), df_rear_range=(100, 250),
            wf=0.42, group='Road Car', is_endurance=True
        )
        self.assertEqual((df_f355['front'], df_f355['rear']), (110, 205))

        # X2019 (wf=0.46) with 800-1200 / 1200-1600 in endurance mode -> 45% front (980) / 55% rear (1420)
        df_x2019 = gt7_dynamics.calculate_aerodynamics(
            df_front_range=(800, 1200), df_rear_range=(1200, 1600),
            wf=0.46, group='Gr.X', is_endurance=True
        )
        self.assertEqual((df_x2019['front'], df_x2019['rear']), (980, 1420))

        # Fixed front aero (200-200 / 400-500) must still clamp rear to floor (400) in endurance mode
        df_supra = gt7_dynamics.calculate_aerodynamics(
            df_front_range=(200, 200), df_rear_range=(400, 500),
            wf=0.53, group='Road Car', is_endurance=True
        )
        self.assertEqual((df_supra['front'], df_supra['rear']), (200, 400))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_gt7_dynamics.TestGT7Dynamics.test_widebody_fender_clearance_clamped_to_slider_max tests.test_gt7_dynamics.TestGT7Dynamics.test_endurance_aerodynamics_cp_and_fixed_front_clamp -v`
Expected: FAIL with `TypeError: calculate_ride_height() got an unexpected keyword argument 'is_widebody'`

- [ ] **Step 3: Implement `is_widebody` in `calculate_ride_height` and `is_endurance` CP balancing in `calculate_aerodynamics`**

- In `scripts/gt7_dynamics.py:calculate_ride_height`:
  - Add `is_widebody: bool = False`. Compute `wide_buf = 5 if (is_widebody and not is_dirt) else 0` and include `+ wide_buf` alongside `elev_buf` in `base_f` across all non-dirt branches before applying `rake` and slider max clamping.
- In `scripts/gt7_dynamics.py:calculate_aerodynamics`:
  - Add `is_endurance: bool = False`.
  - Keep `is_oval` and `span_f == 0` branches first.
  - In the `else` (`wf < 0.55`) branch, when `is_endurance` is `True`:
    - If `group == 'Gr.X'`: `ratio_f, ratio_r = 0.45, 0.55`
    - Else if `wf <= 0.46` (MR/RR): `ratio_f, ratio_r = 0.40, 0.70`
    - Else: `ratio_f, ratio_r = 0.45, 0.60`
- In `scripts/gt7_tuner.py`:
  - Add `is_widebody: bool = False` to `build_setup` and `--widebody` (`action='store_true'`) to `main()`. Pass `is_widebody=is_widebody` to `calculate_ride_height` and `is_endurance=is_endurance` to `calculate_aerodynamics`. Append an endurance/engineering note when `is_widebody` is `True`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (18 tests)

---

### Task 3: Tire-Saver Endurance Alignment, MR/RR Rear Toe-In & Endurance Brake Bias

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:231-265, 310-325`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:108-114`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: `ay_est: float`, `wf: float`, `wr: float`, `drivetrain: str`, `power: float`, `is_endurance: bool`
- Produces:
  - `gt7_dynamics.calculate_wheel_alignment(...) -> Tuple[float, float, str, str]`
  - `gt7_dynamics.calculate_brake_bias(..., is_endurance: bool = False) -> Tuple[int, float]`

- [ ] **Step 1: Write the failing test in `tests/test_gt7_dynamics.py`**

```python
    def test_mr_endurance_alignment_and_maggiore_brake_bias(self):
        # F355 Full Tune (MR, wf=0.42, wr=0.58, 520 HP, RM ay_est=1.55) in endurance mode
        cam_f, cam_r, toe_f, toe_r = gt7_dynamics.calculate_wheel_alignment(
            ay_est=1.55, wf=0.42, wr=0.58, drivetrain='MR', power=520.0, is_endurance=True
        )
        self.assertEqual(cam_f, -2.2)
        self.assertEqual(cam_r, -1.2)
        self.assertEqual(toe_f, '0.00')
        self.assertEqual(toe_r, 'In 0.20')

        # X2019 (MR, wf=0.46, wr=0.54, 816 HP, RM ay_est=1.55) in endurance mode
        cam_f_x, cam_r_x, toe_f_x, toe_r_x = gt7_dynamics.calculate_wheel_alignment(
            ay_est=1.55, wf=0.46, wr=0.54, drivetrain='MR', power=816.0, is_endurance=True
        )
        self.assertEqual(cam_f_x, -2.2)
        self.assertEqual(cam_r_x, -1.2)
        self.assertEqual(toe_r_x, 'In 0.12')

        # Brake bias shifts -1 rearward on balanced/front-loaded endurance runs (wf >= 0.45) to save front tires
        bias_x, _ = gt7_dynamics.calculate_brake_bias(wf=0.46, hcg_m=0.32, wheelbase_m=2.95, drivetrain='MR', is_endurance=True)
        self.assertEqual(bias_x, -1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_gt7_dynamics.TestGT7Dynamics.test_mr_endurance_alignment_and_maggiore_brake_bias -v`
Expected: FAIL (`-2.0 != -2.2`)

- [ ] **Step 3: Update `calculate_wheel_alignment` and `calculate_brake_bias` in `scripts/gt7_dynamics.py` and wire in `scripts/gt7_tuner.py`**

- In `scripts/gt7_dynamics.py:calculate_wheel_alignment` (`if is_endurance:` branch):
  - Set `cam_f = -round(min(2.4, max(1.8, 0.92 + 0.90 * ay_est * math.sqrt(max(0.46, wf) / 0.50))), 1)`.
  - Set `eta_longitudinal = 0.70 if drivetrain in ['FR', 'MR', 'RR'] else 0.50` and `cam_r = -round(0.4 + 0.65 * ay_est * math.sqrt(wr / 0.50) * eta_longitudinal, 1)`.
  - For rear toe-in: if `drivetrain in ['MR', 'RR']`, compute `toe_r_val = round(min(0.22, max(0.12, 0.12 + 2.0 * max(0.0, wr - 0.54))), 2)` (giving `0.12` at `wr=0.54` and `0.20` at `wr=0.58`); otherwise keep `round(max(0.06, min(0.14, 0.06 + 0.15 * max(0.0, wr - 0.45))), 2)`.
- In `scripts/gt7_dynamics.py:calculate_brake_bias`:
  - Add `is_endurance: bool = False`. When `is_endurance` is `True` and `drivetrain != 'FF'` and `wf >= 0.45`: set `bias = max(-3, bias - 1)`.
- In `scripts/gt7_tuner.py:build_setup`: pass `is_endurance=is_endurance` to `calculate_brake_bias`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (19 tests)

---

### Task 4: Damping Compression 40% Ceiling & Section 2.F Quick-Trims Delta Table

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:465-495`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:165-292`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: `parameters: Dict[str, Any]`, `drivetrain: str`, `is_endurance: bool`
- Produces:
  - `gt7_dynamics.build_quick_trims(parameters: Dict[str, Any], drivetrain: str = 'FR', is_endurance: bool = False) -> Dict[str, Dict[str, Any]]`
  - Quick-Trims delta section rendered in `gt7_tuner.format_setup_sheet(setup: Dict[str, Any]) -> str`

- [ ] **Step 1: Write the failing test in `tests/test_gt7_dynamics.py`**

```python
    def test_damping_compression_clamped_to_40_pct_and_quick_trims_rendered(self):
        import gt7_tuner
        car = {'id': '3614', 'name': "Ferrari F355 Berlinetta '94", 'drivetrain': 'MR', 'group': 'Road Car', 'mass_kg': 1200, 'balance': {'front_pct': 42}}
        setup = gt7_tuner.build_setup(
            car=car, custom_power=520,
            symptoms=['bottoming', 'bottoming', 'bottoming', 'exit_snap', 'exit_snap']
        )
        p = setup['parameters']
        self.assertLessEqual(p['damping_compression_pct']['front'], 40)
        self.assertLessEqual(p['damping_compression_pct']['rear'], 40)
        self.assertIn('quick_trims', p)
        self.assertIn('tire_saver', p['quick_trims'])
        self.assertIn('max_stability', p['quick_trims'])

        sheet = gt7_tuner.format_setup_sheet(setup)
        self.assertIn('Tire-Saver Spec', sheet)
        self.assertIn('Max Stability Spec', sheet)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_gt7_dynamics.TestGT7Dynamics.test_damping_compression_clamped_to_40_pct_and_quick_trims_rendered -v`
Expected: FAIL (`42 not less than or equal to 40`)

- [ ] **Step 3: Clamp compression damping to `20..40%`, implement `build_quick_trims`, and render in `format_setup_sheet`**

- In `scripts/gt7_dynamics.py`:
  - In `apply_closed_loop_trim`: change `damping_compression_pct` upper bound from `80` to `40` (`max(20, min(40, ...))`) and `damping_expansion_pct` lower bound to `30` (`max(30, min(80, ...))`).
  - Add `build_quick_trims(parameters: Dict[str, Any], drivetrain: str = 'FR', is_endurance: bool = False) -> Dict[str, Dict[str, Any]]`:
    - `tire_saver`: `fn_front = round(max(1.40, fn_f - (0.0 if is_endurance else 0.20)), 2)`, `fn_rear = round(max(1.40, fn_r - (0.0 if is_endurance else 0.20)), 2)`, `camber = '-2.2° / -1.2°'`, `toe = '0.00° / In 0.12°'` (or `'0.00° / In 0.08°'` if non-MR/RR), `lsd_accel = max(14, min(20, lsd_r['accel'] - (0 if is_endurance else 4)))`.
    - `max_stability`: `arb = f"{min(7, arb_f + 1)} / {max(4, arb_r - 1)}"`, `damping_exp_rear = f"{min(80, exp_r + 4)}%"`, `toe_rear = 'In 0.20°'` (or `'In 0.18°'` if non-MR/RR), `lsd_brake = min(65, lsd_r['brake'] + 8)`, `brake_bias = min(2, bias + 1)`.
- In `scripts/gt7_tuner.py`:
  - In `build_setup`: after `apply_closed_loop_trim`, set `params['quick_trims'] = gt7_dynamics.build_quick_trims(params, drivetrain=drivetrain, is_endurance=is_endurance)`.
  - In `format_setup_sheet`: render a compact `⚡ QUICK-TRIMS DELTA TABLE (โหมดปรับด่วน: ถนอมยาง & เน้นความนิ่ง - Section 2.F)` block showing `Tire-Saver Spec` and `Max Stability Spec` rows before the closing `=` line.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (20 tests)

---

### Task 5: High-Speed (`v km/h`) Aero + Trail-Braking Outside-Front Compression & Bottoming Simulator

**Files:**
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_dynamics.py:465-495`
- Modify: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/scripts/gt7_tuner.py:19-40, 145-295`
- Test: `/Users/zenithth/.gemini/config/skills/gt7-suspension-tuning/tests/test_gt7_dynamics.py`

**Interfaces:**
- Consumes: `speed_kmh: float`, `mass_kg: float`, `corner_front_kg: float`, `corner_rear_kg: float`, `wf: float`, `hcg_m: float`, `wheelbase_m: float`, `track_width_m: float`, `mu: float`, `rh_front_mm: int`, `rh_rear_mm: int`, `fn_front_hz: float`, `fn_rear_hz: float`, `arb_front: int`, `arb_rear: int`, `df_front: int`, `df_rear: int`, `is_widebody: bool`, `height_min_front_mm: int`
- Produces:
  - `gt7_dynamics.simulate_high_speed_trail_braking(...) -> Dict[str, Any]` returning:
    - `speed_kmh: float`
    - `aero_compression_mm: {'front': float, 'rear': float}`
    - `pitch_compression_front_mm: float`
    - `roll_compression_front_mm: float`
    - `total_outside_front_compression_mm: float`
    - `dynamic_outside_front_clearance_mm: float`
    - `dynamic_rake_mm: float`
    - `bottoming_or_fender_hit: bool`
    - `recommended_front_rh_bump_mm: int`
  - CLI flag `--speed <KMH>` in `scripts/gt7_tuner.py` (default `200.0` for road cars, `240.0` for racecars) and telemetry output block in `format_setup_sheet`

- [ ] **Step 1: Write the failing test in `tests/test_gt7_dynamics.py`**

```python
    def test_high_speed_trail_brake_compression_and_bottoming_guard(self):
        import gt7_tuner
        # Soft-sprung slammed widebody road car under 240 km/h trail-braking must trigger bottoming_or_fender_hit
        sim_slammed = gt7_dynamics.simulate_high_speed_trail_braking(
            speed_kmh=240.0, mass_kg=1350.0, corner_front_kg=250.0, corner_rear_kg=344.0,
            wf=0.42, hcg_m=0.42, wheelbase_m=2.45, track_width_m=1.62, mu=1.55,
            rh_front_mm=92, rh_rear_mm=100, fn_front_hz=2.00, fn_rear_hz=2.20,
            arb_front=3, arb_rear=6, df_front=180, df_rear=240,
            is_widebody=True, height_min_front_mm=90
        )
        self.assertTrue(sim_slammed['bottoming_or_fender_hit'])
        self.assertGreater(sim_slammed['total_outside_front_compression_mm'], 25.0)
        self.assertGreater(sim_slammed['recommended_front_rh_bump_mm'], 0)

        # Properly tuned F355 (105/113 mm, 2.50/2.70 Hz, ARB 5/5) at 200 km/h must clear fender & road safely
        car = {'id': '3614', 'name': "Ferrari F355 Berlinetta '94", 'drivetrain': 'MR', 'group': 'Road Car', 'mass_kg': 1200, 'balance': {'front_pct': 42}, 'dimensions_mm': {'length': 4250, 'width': 1900, 'height': 1170}}
        setup = gt7_tuner.build_setup(car=car, tire='RM', mode='endurance', is_widebody=True, speed_kmh=200.0)
        self.assertIn('high_speed_simulation', setup['telemetry'])
        self.assertFalse(setup['telemetry']['high_speed_simulation']['bottoming_or_fender_hit'])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_gt7_dynamics.TestGT7Dynamics.test_high_speed_trail_brake_compression_and_bottoming_guard -v`
Expected: FAIL with `AttributeError: module 'gt7_dynamics' has no attribute 'simulate_high_speed_trail_brake_compression_and_bottoming_guard'`

- [ ] **Step 3: Implement `simulate_high_speed_trail_braking` in `scripts/gt7_dynamics.py` and wire `--speed` in `scripts/gt7_tuner.py`**

- In `scripts/gt7_dynamics.py`:
  - Implement `simulate_high_speed_trail_braking(...) -> Dict[str, Any]`:
    - Wheel rates ($N/m$): $K_{w,f} = (2\pi f_{n,f})^2 \cdot m_{c,f}$, $K_{w,r} = (2\pi f_{n,r})^2 \cdot m_{c,r}$.
    - Aerodynamic vertical load ($N$) at speed $v$: $F_{\text{df},f} = \text{df}_f \cdot 9.81 \cdot (v / 240.0)^2$, $F_{\text{df},r} = \text{df}_r \cdot 9.81 \cdot (v / 240.0)^2$.
    - Aero heave compression ($mm$): $\Delta z_{\text{aero},f} = \frac{F_{\text{df},f} / 2.0}{K_{w,f}} \cdot 1000.0$, $\Delta z_{\text{aero},r} = \frac{F_{\text{df},r} / 2.0}{K_{w,r}} \cdot 1000.0$.
    - Trail-braking combined friction circle at corner entry ($a_x = 0.55 \mu g$, $a_y = 0.80 \mu g$):
      - Forward pitch force per front wheel ($N$): $\Delta F_{\text{pitch},f} = \frac{m \cdot a_x \cdot h_{\text{cg}}}{2.0 \cdot L} \implies \Delta z_{\text{pitch},f} = \frac{\Delta F_{\text{pitch},f}}{K_{w,f}} \cdot 1000.0$.
      - Lateral roll force on outside front wheel ($N$) reduced by ARB roll stiffness factor $(1.0 + 0.12 \cdot \text{arb}_f)$: $\Delta F_{\text{roll},f} = \frac{\text{arb}_f}{\text{arb}_f + \text{arb}_r} \cdot \frac{m \cdot a_y \cdot h_{\text{cg}}}{T} \implies \Delta z_{\text{roll},f} = \frac{\Delta F_{\text{roll},f}}{K_{w,f} \cdot (1.0 + 0.12 \cdot \text{arb}_f)} \cdot 1000.0$.
    - Total outside-front compression: $\Delta z_{\text{tot},f} = \Delta z_{\text{aero},f} + \Delta z_{\text{pitch},f} + \Delta z_{\text{roll},f}$.
    - Effective stroke limit before bump-stop / fender contact: $z_{\text{avail},f} = (\text{rh}_f - \text{height\_min\_front\_mm}) + (22.0 \text{ if not is\_widebody else } 16.0)$.
    - `bottoming_or_fender_hit = (dz_tot_f >= z_avail_f)` and `recommended_front_rh_bump_mm = max(0, math.ceil(dz_tot_f - z_avail_f + 2.0))`.
- In `scripts/gt7_tuner.py`:
  - Add `speed_kmh: Optional[float] = None` to `build_setup` and `--speed` (`type=float`) to `main()`.
  - Run `simulate_high_speed_trail_braking`; if `bottoming_or_fender_hit` is `True`, auto-increment `ride_height_mm['front']` and `ride_height_mm['rear']` by `recommended_front_rh_bump_mm` (clamped to slider max), re-run simulation, and append a warning note in `endurance_notes` and `format_setup_sheet`.

- [ ] **Step 4: Run full test suite and CLI verification**

Run: `python3 -m unittest discover -s tests -v && python3 scripts/gt7_tuner.py "Ferrari F355 Berlinetta '94" --widebody --power 520 --mass 1200 --tire RM --mode endurance --speed 220 && python3 scripts/gt7_tuner.py 3374 -t "Maggiore" --mode endurance --tire RM --speed 260`
Expected: PASS (21 tests) and both F355 and X2019 sheets display 2D/3D High-Speed Trail-Braking Compression & Bottoming Clearance telemetry plus Quick-Trims.
