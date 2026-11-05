# GT7 Suspension Tuner — PyQt6 GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A PyQt6 desktop GUI that replaces manual CLI flag entry: user picks a car, fills in-game slider ranges + optional calibration data, clicks Compute, gets the full suspension sheet with copy-to-clipboard.

**Architecture:** Thin Qt layer over the existing physics core. A plain-Python `TuningService` facade (search, swaps, slider-range persistence, validation, `build_setup` dispatch) is called from a `QObject` worker on a `QThread` so the solver never blocks the UI. The form is one `SetupForm` widget with grouped panels that `collect()`s into a `GuiRequest` dataclass; results render `sheet_formatter.format_setup_sheet()` output in a `QTextBrowser`.

**Tech Stack:** Python 3.15 (macOS), PyQt6 ≥6.7, stdlib `unittest`, project venv (PEP 668).

**Spec:** Input contract established in the design conversation (4 input tiers: required car+slider ranges / auto-from-DB / optional build overrides / optional session params) and the CLI reference at `cli.py` + tutorial `/Users/zenithth/gt7-suspension-cli-tutorial.md`.

## Global Constraints

- Repo root: `/Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning`. All paths relative to it.
- PEP 668 blocks system pip: create `.venv/` once; run everything with `.venv/bin/python`. Add `.venv/` to `.gitignore`.
- Only new dependency: `PyQt6>=6.7,<7`. Fallback if the wheel won't install on 3.15: `PySide6` 6.12 — same API for this plan, only the import prefix changes (`PyQt6` → `PySide6`); decide at Task 1's verify step and use one consistently.
- No other third-party deps. Tests use stdlib `unittest` with the existing pattern: `BASE_DIR = os.path.dirname(...)` + `sys.path.insert(0, BASE_DIR)`.
- GUI is a read-only consumer: never modify `lib/`, `setup.py`, `setup_engine.py`, `sheet_formatter.py`, `cli.py`, `db/`.
- No shelling out to `cli.py`. Import directly: `setup.build_setup`, `sheet_formatter.format_setup_sheet`, `db.interface.{search_cars, get_car, get_track, get_slider_ranges, save_car_sliders}`, `scripts.gt7_db.get_swaps` (it inserts BASE_DIR onto sys.path itself, so `from scripts.gt7_db import get_swaps` works).
- Every GUI test file starts with `os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')` BEFORE any Qt import.
- Range-pair rule: a form range pair is sent as `None` iff `min == 0 and max == 0` (means "use DB saved/preseeded values").
- Choice literals (verbatim from `cli.py`): TIRE `('CH','CM','CS','SH','SM','SS','RH','RM','RS','Dirt','Wet')`; DRIVETRAIN `('FF','FR','MR','RR','AWD','4WD','4x4')`; MODE `('grip','time_attack','wet','dirt','drift','endurance')`; SYMPTOM `('entry_push','exit_snap','bottoming','curb_hop','front_tire_wear','rear_tire_wear')`; SOLVE `('balanced','max_grip','min_tire_wear')`.
- Commit after each task.

## File Structure

| File | Responsibility |
|---|---|
| `gui/__init__.py` | Package marker (empty) |
| `gui/__main__.py` | Entry point: `python3 -m gui` → calls `gui.app.main()` |
| `gui/request.py` | `GuiRequest` / `GuiResult` dataclasses + the 5 choice tuples above |
| `gui/service.py` | `TuningService` (plain Python, no Qt) + `Worker(QObject)` |
| `gui/components.py` | Reusable widgets: `RangePair` (min/max pair, owns the (0,0)→None rule) |
| `gui/form.py` | `SetupForm(QWidget)` — all input panels (built from `gui.components`), `collect()`, `validate()` |
| `gui/results.py` | `ResultsView(QWidget)` — warnings label, sheet browser, copy button |
| `gui/theme.py` | **Global theme**: `QSS: str` + `apply(app)` — written in Task 1 from the Design Spec section |
| `gui/app.py` | `MainWindow(QMainWindow)` + `main()`; applies `gui.theme` |
| `run_gui.sh` | Launcher: creates `.venv` if missing, runs `python -m gui` |
| `docs/GUI.md` | User guide (short) |
| `tests/test_gui_components.py`, `tests/test_gui_request.py`, `tests/test_gui_service.py`, `tests/test_gui_form.py`, `tests/test_gui_app.py` | Per-task tests |

`build_setup` signature (verified, `setup.py:146`): `build_setup(car, track=None, tire='SS', custom_mass=None, custom_power=None, custom_torque=None, custom_drivetrain=None, custom_balance=None, mode='grip', df_front_range=None, df_rear_range=None, height_range=None, height_front_range=None, height_rear_range=None, fn_front_range=None, fn_rear_range=None, stability=None, symptoms=None, is_widebody=False, speed_kmh=None, is_controller=False, g_forces=None, g_ref_df=None, solve_objective=None) -> Dict`. The GUI exposes per-side heights only (no combined `height_range`).

## Design Spec (theme) — `gui/theme.py`, written in Task 1, applied from the first launch

**Principle:** dark cockpit chrome, light document panel. The setup sheet is the product — it must look like a paper spec sheet (white) inside a dark racing-game console (GT7 is dark UI). Hierarchy comes from contrast, not decoration: no images, no gradients, single accent color, ≤ 70 lines of QSS. The sheet pane dominates the window (splitter: form ~400px fixed-ish, sheet gets the rest).

**Tokens (exact values — the QSS must use these):**
| Token | Value | Use |
|---|---|---|
| `bg-window` | `#1b1d23` | `QMainWindow`, splitter, status bar |
| `bg-panel` | `#23262e` | `QGroupBox` / form sections, default buttons |
| `bg-field` | `#14161a` | spinbox/combo/line-edit inputs |
| `border` | `#3a3f4d` | 1px field + group-box borders, scrollbars |
| `text-primary` | `#e6e8ee` | labels, field values, group titles |
| `text-secondary` | `#9aa0ae` | hints, `db_info_label`, placeholders |
| `accent` | `#e5484d` | Compute button bg, focus rings, selected combo row |
| `accent-hover` / `accent-pressed` | `#f2555a` / `#c73a3f` | Compute button states |
| `warn` | `#ffb454` | warnings label + status (bold) |
| `error` | `#ff6369` | status errors (bold) |
| `error-on-sheet` | `#c62828` | error text inside the white sheet browser |
| `ok` | `#4ade80` | success status text |
| `sheet-bg` / `sheet-text` | `#ffffff` / `#16181d` | `ResultsView.browser` only |

**Typography:** UI 13px system font; `QGroupBox` titles bold 13px; sheet `QTextBrowser` monospace 12.5px with 16px padding; status 12px.

**Per-component rules:**
- `QGroupBox`: `bg-panel`, 1px `border`, 8px radius, content margin 12px, title bold `text-primary`.
- Inputs (`QSpinBox`/`QDoubleSpinBox`/`QComboBox`/`QLineEdit`): `bg-field`, `text-primary`, 1px border, 4px radius, padding 4px 8px, min height 28px; **focus → 2px accent border** (the user must always see where they are); disabled → 50% opacity, `text-secondary`.
- Buttons: default = `bg-panel` + border + hover lightens border; **Compute = accent bg, white bold text, full height 40px**.
- `db_info_label` + hint labels: `text-secondary` 12px.
- `warnings_label`: `warn` bold; error status: `error` bold; success: `ok`.
- Sheet `QTextBrowser`: `sheet-bg`/`sheet-text` monospace 12.5px; error messages rendered inside it use `error-on-sheet` (dark red on white).
- Scrollbars: 10px, handle `border`, transparent track.

**Verification (theme is testable, not vibes):** `tests/test_gui_smoke.py` asserts `gui.theme.QSS` contains the key token literals (`#1b1d23`, `#e5484d`, `monospace`) so the theme can't be silently dropped; Task 7 does the visual polish pass.

## Task 1: Venv, PyQt6, gui package skeleton

Deliverable: `.venv` with PyQt6 importable; `python3 -m gui` launches an empty window offscreen and exits 0.

- [ ] `python3 -m venv .venv && .venv/bin/pip install --upgrade pip 'PyQt6>=6.7,<7'`; append `.venv/` to `.gitignore` (create if missing).
- [ ] Verify: `.venv/bin/python -c "from PyQt6.QtWidgets import QApplication; print('ok')"`. If it fails to install/import on this Python, install `PySide6` instead and note it — all later code uses one binding; record the choice in `docs/GUI.md`.
- [ ] Create `gui/__init__.py` (empty) and `gui/theme.py` — `QSS: str` + `apply(app)` written from the **Design Spec** section above (exact tokens).
- [ ] `gui/__main__.py` with:
  ```python
  from gui.app import main
  if __name__ == '__main__':
      raise SystemExit(main())
  ```
- [ ] `gui/app.py` minimal: `def main() -> int:` creates `QApplication([])`, calls `gui.theme.apply(app)`, a 600x400 `QMainWindow` titled "GT7 Suspension Tuner", `win.show()`, `return app.exec()`.
- [ ] Test `tests/test_gui_smoke.py`: set offscreen env; create QApplication + import `gui.app`; assert `gui.app.main.__module__ == 'gui.app'` AND that `gui.theme.QSS` contains the token literals `#1b1d23`, `#e5484d`, `monospace` (theme guard — the design can't be silently dropped); then run `subprocess` of `.venv/bin/python -m gui` with `QT_QPA_PLATFORM=offscreen` and `timeout 15`, after `show()` the window auto-closes — implement by having `main()` accept an optional `auto_quit: int = 0` ms parameter that schedules `QTimer.singleShot(auto_quit, app.quit)` when > 0; `__main__` passes 0. Test asserts returncode 0.
- [ ] Run: `.venv/bin/python -m unittest tests.test_gui_smoke -v` → passes.
- [ ] Commit `gui: venv scaffold + themed skeleton window (Design Spec tokens)`.
## Task 2: `GuiRequest` / `GuiResult` + `TuningService` (pure Python, no Qt)

Deliverable: a Qt-free service the whole GUI is built on, with exact `build_setup` kwargs mapping and non-raising `compute()`.

**Interfaces (lock these):**

`gui/request.py`:
```python
@dataclass
class GuiRequest:
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
    setup: Optional[Dict[str, Any]] = None
    sheet: str = ''
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    @property
    def ok(self) -> bool: ...  # error is None
```
Plus the five choice tuples from Global Constraints as module constants: `TIRE_COMPOUNDS`, `DRIVETRAINS`, `MODES`, `SYMPTOMS`, `SOLVE_OBJECTIVES`.

`gui/service.py`:
```python
class TuningService:
    def search_cars(self, query: str = '') -> List[Dict[str, Any]]      # db.interface.search_cars
    def get_car(self, car_id: str) -> Optional[Dict[str, Any]]          # db.interface.get_car
    def search_tracks(self, query: str = '') -> List[Dict[str, Any]]    # filter TRACKS_DB with db.interface.norm_str token logic
    def get_track(self, track_id: str) -> Optional[Dict[str, Any]]
    def get_swaps(self, car_id: str) -> List[Dict[str, Any]]            # get_swaps(car_id)['swaps_available'], [] when car missing
    def get_slider_ranges(self, car_id: str) -> Dict[str, Any]          # db.interface.get_slider_ranges (saved + preseeded merge)
    def save_sliders(self, car_id: str, ranges: Dict[str, Tuple]) -> bool  # db.interface.save_car_sliders; False on missing car
    def validate(self, req: GuiRequest) -> Tuple[List[str], List[str]]  # (errors, warnings)
    def compute(self, req: GuiRequest) -> GuiResult                     # NEVER raises; errors -> GuiResult(error=...)
```

**`validate` rules (errors = hard, warnings = soft):**
- error: car not found → `Car not found: {car_id}`
- error: any range field with `min > max` (message names the field) or any range value < 0
- warning: any of the 6 slider-range fields (df/height/fn) is None → `No {name} range — using saved/preseeded DB values` (only these have a DB fallback; `g_ref_df`/`stability` are not included — Ruling, Task 2)
- warning: `solve_objective` set but `g_forces` None → `Solver needs G-force calibration; solve will be skipped`
- warning: `custom_balance` set, `abs(sum-100) > 1` → `Balance front+rear = {n} (expected 100)`
- warning: `g_forces` set, `g_ref_df` None → `G-forces without reference downforce; profile anchored at current DF`

**`compute` mapping:** resolve `car` (error result if missing) and `track` (only when `track_id` truthy); kwargs dict exactly: `track, tire, mode, custom_mass, custom_power, custom_torque, custom_drivetrain, custom_balance, df_front_range=req.df_front, df_rear_range=req.df_rear, height_front_range=req.height_front, height_rear_range=req.height_rear, fn_front_range=req.fn_front, fn_rear_range=req.fn_rear, stability, symptoms, is_widebody, speed_kmh, is_controller, g_forces, g_ref_df, solve_objective` (None passes through; `height_range` never set). Wrap `build_setup` + `format_setup_sheet` in try/except → `GuiResult(error=repr(e))`. Attach `validate` warnings to the result.

**Steps:**
1. Write `gui/request.py` + `gui/service.py`.
2. `tests/test_gui_request.py`: dataclass defaults; `GuiResult.ok` True/False.
3. `tests/test_gui_service.py`:
   - `test_mr2_compute_ok`: `GuiRequest(car_id='207', df_front=(50,200), df_rear=(120,310), height_front=(90,160), height_rear=(90,160), fn_front=(1.5,3.5), fn_rear=(1.5,3.5), g_forces=(1.04,1.19,1.38), g_ref_df=(200,310), solve_objective='balanced', custom_power=630, custom_mass=1289, custom_balance=(42,58))` → `res.ok`, `sheet` contains 'MR2', 'Body Height', 'Quick-Trim' (match assertions in existing `tests/test_setup_orchestrator.py`).
   - `test_compute_bad_car`: `car_id='nope'` → `res.ok is False`, error `Car not found: nope`, no exception.
   - `test_validate_errors`: range (200,50) → error naming 'DF front'; negative min → error.
   - `test_validate_warnings`: solve w/o g_forces → solver warning; g_forces w/o g_ref_df → reference warning; balance (55,40) → warning containing '95'.
   - `test_swaps_and_ranges`: `get_swaps('207')` is a 1-entry list with engine 'BYH-R8'; `get_slider_ranges('3440')` is a dict containing `df_front: [50, 200]` (preseeded).
   - `test_save_sliders_roundtrip`: copy the real `cars_master.json` (via `db.loader.get_data_dir`) to a temp file, `save_sliders('3440', {'df_front': (10,20)}, db_path=temp)` — extend `TuningService.save_sliders` to accept `db_path: Optional[str] = None`; assert reload shows the new pair. Real DB file stays untouched.
   - `test_kwargs_mapping`: monkeypatch `gui.service.setup.build_setup` with a recording stub; compute the MR2 request; recorded kwargs equal expected (all ranges passed, `height_range` absent).
4. Run `.venv/bin/python -m unittest tests.test_gui_request tests.test_gui_service -v` → green.
5. Commit `gui: TuningService + request/result dataclasses`.

## Task 3: `Worker(QObject)` — off-thread compute

Deliverable: `compute` can run on a `QThread` without blocking the event loop.

**Interface (in `gui/service.py`):**
```python
class Worker(QObject):
    finished = Signal(object)   # emits GuiResult
    failed = Signal(str)
    def __init__(self, service: TuningService, req: GuiRequest, parent: Optional[QObject] = None): ...
    def run(self) -> None       # res = service.compute(req); emit finished(res). Wrap in try/except and emit failed(str) only on the unexpected (compute itself never raises)
```

**Steps:**
1. Implement `Worker`.
2. `tests/test_gui_service.py` — add `WorkerTests` (offscreen env): `QCoreApplication` in setUpClass; collector list; `worker = Worker(service, mr2_request)`; connect `finished` → `collector.append`; call `worker.run()` directly (synchronous, no thread needed for the unit test); assert one `GuiResult` in collector and `ok`.
3. Run `.venv/bin/python -m unittest tests.test_gui_service -v` → green.
4. Commit `gui: Worker thread wrapper`.

## Task 4: `SetupForm` part 1 — vehicle, tire, slider ranges, overrides

Deliverable: left-pane form (top half) where picking a car prefills everything derivable from the DB, plus the shared widget layer.

**`gui/components.py` interface (locked — used by form and tests):**
```python
class RangePair(QWidget):
    """Label + min/max spinbox pair; owns the (0,0)→None rule from Global Constraints."""
    min_spin, max_spin                     # QSpinBox or QDoubleSpinBox per kind
    def __init__(self, label: str, kind: str = 'int', max_v: float = 1000, parent=None): ...
    def value(self) -> Optional[tuple]     # (min, max); None when both values are 0
    def set_value(self, pair: Optional[tuple])   # None → both 0
```

**File `gui/form.py`. `SetupForm(QWidget)` with these public attributes (tests target them by name):**

- **Vehicle group**: `car_search: QLineEdit` (textChanged → `car_combo` refills from `service.search_cars(text)`), `car_combo: QComboBox` (itemText = name, `addItem(name, data=car['id'])`), `swap_combo: QComboBox` (item 0 = `'Stock engine'` data `''`, then each swap name data swap id), `db_info_label: QLabel` (read-only multi-line: mass, power, torque, drivetrain, weight balance — per the verified car shape; the DB car records have no axle-width fields, so none are shown).
- **Tire group**: `tire_combo: QComboBox` from `TIRE_COMPOUNDS`, default `'SS'`.
- **Slider ranges group**: 6 × `RangePair` instances — `df_f`, `df_r` (kind int, **max_v 2000** — preseeded/saved DF ranges reach 2000 in the DB; 1000 was a wrong lock, corrected after final review), `hf`, `hr` (int, 400), `fn_f`, `fn_r` (kind float, max_v 10.0, 2 dp). Plus `save_ranges_btn: QPushButton` ("Save ranges to DB") → `service.save_sliders` + status flash.
- **Overrides group**: `mass_use_db/power_use_db/torque_use_db/balance_use_db: QCheckBox` (checked by default); `mass_spin/power_spin: QSpinBox` (0–3000), `torque_spin: QDoubleSpinBox` (0–1500); `bal_f_spin/bal_r_spin: QSpinBox` (0–100); `drivetrain_combo: QComboBox` from `DRIVETRAINS`.
- `status_label: QLabel` at the bottom of the form for messages (warnings/errors, word-wrapped).

**Behavior — `on_car_selected(car_id)` (wired to `car_combo.currentIndexChanged`):**
1. `car = service.get_car(car_id)`; if None → clear groups, status `Car not found`.
2. Fill `db_info_label` from car fields (verified shape — car 207): `mass_kg`, `engine.power_hp`, `engine.torque_nm`, `drivetrain`, `balance.front_pct`/`balance.rear_pct`.
3. Reset override checkboxes to checked (use DB) and spinboxes to DB values.
4. Prefill range spinboxes from `service.get_slider_ranges(car_id)` keys `df_front, df_rear, height_front, height_rear, fn_front, fn_rear` (list of [min,max]); missing key → both spins to 0.
5. Refill `swap_combo` from `service.get_swaps(car_id)` (itemText `swap['engine']`, data `swap['donor_id']`); on swap selection → donor = `service.get_car(donor_id)`, set `power_spin`/`torque_spin` from `donor['engine']['power_hp'/'torque_nm']` (verified: donor 1365 BYH = 420 hp / 429.5 Nm), uncheck `power_use_db`/`torque_use_db`; donor missing → status message, no crash.

**`collect()` (partial in this task):** reads the groups above into a `GuiRequest` — `RangePair.value()` is None (both 0) → `None` for that pair; unchecked `*_use_db` → `None` override; `balance` only when `balance_use_db` is off (else `None`).

**Steps:**
1. Write `gui/components.py` (`RangePair`) first, then `gui/form.py` with the groups above + `on_car_selected` + partial `collect()` (session fields added in Task 5 — for now `collect()` returns defaults for them).
2. `tests/test_gui_components.py` + extend `tests/test_gui_form.py` (offscreen):
   - `test_range_pair_rule`: default `RangePair('X').value() is None`; `set_value((50, 200))` → `value() == (50, 200)`; `set_value(None)` → `value() is None`; float kind: `set_value((1.5, 3.5))` → exact tuple.
   - `test_car_prefill`: build form with real `TuningService`; select the car 3440 item; assert `db_info_label` contains its `short_name`; `form.df_f.value() == (50, 200)` (preseeded), `form.fn_f.value() is None` (not preseeded → empty).
   - `test_collect_empty_ranges_to_none`: set a range pair to 0/0 → `collect().df_front is None`; set 50/200 → `collect().df_front == (50, 200)`.
   - `test_swap_selection`: select car 207 (MR2 GT-S); pick the BYH-R8 item in `swap_combo` → `power_use_db.isChecked()` False, `power_spin.value() == 420`, `torque_spin.value() == 429.5`.
3. Run `.venv/bin/python -m unittest tests.test_gui_components tests.test_gui_form -v` → green.
4. Commit `gui: RangePair component + SetupForm vehicle/tire/ranges/overrides panels`.

## Task 5: `SetupForm` part 2 — calibration, session, symptoms + full `collect()`/`validate()`

Deliverable: the complete input form; `collect()` returns a fully-populated `GuiRequest`; `validate()` blocks compute on hard errors.

**New widgets (in `gui/form.py`):**
- **Calibration group**: `g60_spin`, `g120_spin`, `g240_spin: QDoubleSpinBox` (0–9, 2 dp, `setSpecialValueText('')` at 0.0 → value 0 means unset); `gref_f_spin`, `gref_r_spin: QSpinBox` (0–1000, 0 = unset); `solve_combo: QComboBox` from `SOLVE_OBJECTIVES` (item 0 `'—'` data `''`), **disabled** unless all three G spins are non-zero (re-checked on every `valueChanged`); hint label: "Measure peak lateral G in-game at 60/120/240 km/h and the downforce you were running."
- **Session group**: `track_combo: QComboBox` editable (item 0 `'— (no track)'` data `''`, then all `TRACKS_DB` names data `id`; `QCompleter` on the line-edit for search-as-you-type); `mode_combo: QComboBox` from `MODES`; `speed_spin: QDoubleSpinBox` (30–400, default 240); `widebody_check`, `controller_check: QCheckBox`.
- **Symptoms group**: `symptom_checks: Dict[str, QCheckBox]` keyed by the 6 `SYMPTOMS` values (display names, e.g. `entry_push` → "Entry push / understeer"); `stab_low_spin`, `stab_high_spin: QDoubleSpinBox` (0–1, 2 dp, specialValueText `''` at 0).

**`collect()` completion:** `g_forces` = tuple only if all 3 G spins non-zero (else None); `g_ref_df` = tuple of the two ref spins when either non-zero (a single set value is used for both axes — the service warning covers the gap); `solve_objective` = `solve_combo.currentData() or None`; `track_id` = `track_combo.currentData() or None` (edited text matching no track → None + status note "unknown track ignored"); `stability` = tuple if both non-zero else None; `symptoms` = list of checked keys, empty → None.

**`validate() -> List[str]`:** `req = collect()`; call `service.validate(req)`; show errors red and warnings (prefixed `⚠`) amber in `status_label`; return the error list.

**Steps:**
1. Implement the groups + `collect()`/`validate()`.
2. Extend `tests/test_gui_form.py`:
   - `test_gforces_gate_solve`: G spins 0 → `solve_combo.isEnabled()` False; set g60/g120/g240 = 1.04/1.19/1.38 → enabled.
   - `test_collect_full_request`: select car 207, fill MR2 tutorial values (ranges, G-forces, g_ref_df 200/310, solve 'balanced', power 630, mass 1289, balance 42/58, symptom `front_tire_wear`, stab 0.1/0.3); `req = form.collect()`; assert `req.car_id == '207'`, `req.g_forces == (1.04, 1.19, 1.38)`, `req.solve_objective == 'balanced'`, `req.custom_power == 630`, `req.symptoms == ['front_tire_wear']`, `req.stability == (0.1, 0.3)`.
   - `test_validate_blocks_bad_range`: `form.df_f.set_value((200, 50))` (min > max) → `validate()` returns ≥1 error, `status_label` text non-empty.
3. Run `.venv/bin/python -m unittest tests.test_gui_form -v` → green.
4. Commit `gui: SetupForm calibration/session/symptoms + collect/validate`.

## Task 6: `ResultsView` + `MainWindow` wiring (end-to-end)

Deliverable: click Compute → sheet appears in the right pane; UI stays responsive during solving.

**`gui/results.py`:**
```python
class ResultsView(QWidget):
    warnings_label: QLabel     # amber, word-wrap, hidden when empty
    browser: QTextBrowser      # monospace <pre>; setText('<pre style="...">' + html.escape(sheet) + '</pre>')
    copy_btn: QPushButton      # copies raw sheet text via QApplication.clipboard()
    def show_result(self, r: GuiResult)   # sheet + joined warnings (''); errors -> show_error(r.error)
    def show_error(self, msg: str)        # red text in browser, sheet cleared
    def clear(self)
```

**`gui/app.py` — `MainWindow(QMainWindow)`:**
- Layout: `QSplitter` — left `QScrollArea` containing `SetupForm`, right `ResultsView`; bottom bar: `compute_btn: QPushButton("Compute Setup")` + `status: QLabel`.
- `MainWindow.__init__(self, service: Optional[TuningService] = None)` (constructs one when None).
- **Compute flow (slot `_on_compute`):** `errors = form.validate()`; if errors → `status` shows the first, stop. Else `results.clear()`, `compute_btn` disabled + text "Computing…"; create `worker = Worker(service, req)`; `thread = QThread(self)`; `thread.started.connect(worker.run)`; `worker.finished.connect(self._on_finished)`; `worker.failed.connect(self._on_failed)`; `thread.finished.connect(thread.deleteLater)`; `worker.moveToThread(thread)`; `thread.start()`.
- **`_on_finished(r: GuiResult)`:** `thread.quit()`; `results.show_result(r)`; re-enable button; `status` = "N warning(s)" or "OK". `_on_failed(msg)`: same teardown + `results.show_error(msg)`. (Cross-thread signals are queued by default; `run()` completes before `thread.quit()` is handled.) `closeEvent` (added in final fix wave): if a solve thread is in flight, `quit()` + bounded 1.5 s `wait(50)`/`processEvents()` poll loop; accept the close only once the `thread.finished` handler has cleared the in-flight flag, else `event.ignore()` — re-entrancy-safe; prevents the qFatal/SIGABRT abort on close-during-solve.
- `main(auto_quit: int = 0) -> int`: `QApplication([])`, `MainWindow()`, `resize(1400, 900)`, QSS from Task 7, `show()`, `QTimer.singleShot(auto_quit, app.quit)` when `auto_quit > 0`, `return app.exec()`.

**Steps:**
1. Write `gui/results.py`; wire `gui/app.py` as specified (`gui/__main__.py` already calls `main()`).
2. `tests/test_gui_app.py` (offscreen):
   - `test_window_builds`: `MainWindow(TuningService())` constructs; `win.form`, `win.results`, `win.compute_btn` exist.
   - `test_compute_end_to_end`: on `win.form` select car 207 and set the MR2 tutorial values (ranges 50-200/120-310/90-160/90-160/1.5-3.5, G 1.04/1.19/1.38, ref 200/310, solve balanced, power 630, mass 1289, balance 42/58); `win._on_compute()`; spin `QApplication.processEvents()` in a loop (deadline 60 s — solver is heavy) until `compute_btn.isEnabled()`; assert `results.browser.toPlainText()` contains 'MR2', 'Body Height', 'Quick-Trim'; assert warnings label does not contain 'not found'.
   - `test_error_path`: call `win._on_finished(GuiResult(error='Car not found: nope'))` directly; assert `results.browser.toPlainText()` contains 'not found'.
3. Run `.venv/bin/python -m unittest tests.test_gui_smoke tests.test_gui_components tests.test_gui_request tests.test_gui_service tests.test_gui_form tests.test_gui_app -v` → green.
4. Commit `gui: ResultsView + MainWindow end-to-end wiring`.

## Task 7: Theme polish, launcher, docs, full-suite green

Deliverable: polished, runnable, documented GUI.

**Steps:**
1. **Theme polish pass** (`gui/theme.py` was already written in Task 1 from the Design Spec): run the app with the MR2 example loaded and check against the spec — sheet pane dominates the window (form side ~400px), focus rings visible on every input, warnings/errors readable at a glance, sheet crisp (12.5px monospace on white). Fix QSS gaps found during Tasks 4–6; token changes require a note in `docs/GUI.md`.
2. **`run_gui.sh`** (executable):
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   cd "$(dirname "$0")"
   if [ ! -d .venv ]; then python3 -m venv .venv && .venv/bin/pip install --upgrade pip 'PyQt6>=6.7,<7'; fi
   exec .venv/bin/python -m gui
   ```
3. **`docs/GUI.md`** (≤ 60 lines): what it is; `./run_gui.sh` to launch; the 4 input tiers (copy the short table from the tutorial); the MR2 worked example (car 207, tutorial command values); note which Qt binding was installed (PyQt6 or PySide6 fallback, per Task 1); troubleshooting (venv, offscreen).
4. **Full suite:** `.venv/bin/python -m unittest discover -s tests -v` → all existing + new tests green (existing 11 modules unaffected — GUI is additive).
5. **Manual smoke (user's desktop):** `./run_gui.sh`; pick Toyota MR2 GT-S '97; verify DB info label shows 241 hp / 42:58 / MR; select BYH-R8 swap → power prefill 420; enter tutorial ranges + G-forces; Compute → sheet renders with Quick-Trim; Copy → clipboard holds the sheet.
6. Commit `gui: theme, launcher, docs, full suite green`.

## Review Focus

Failure modes the spec implies but no single test fully pins — each is covered by the test named, and a reviewer should check these hard:

1. **Solver without calibration** — `solve` selected but G-forces empty: GUI disables `solve_combo` (Task 5 `test_gforces_gate_solve`) AND service warns (Task 2 `test_validate_warnings`). Both layers must agree; a gap here produces a silent no-op solve.
2. **Car not found** — bad/empty `car_id`: service returns `GuiResult(error=...)`, never raises (Task 2 `test_compute_bad_car`); UI shows it red (Task 6 `test_error_path`).
3. **Range min > max / negative** — hard validation error must block Compute (Task 5 `test_validate_blocks_bad_range`) and the (0,0)→None rule must not silently drop a legitimate range (Task 4 `test_collect_empty_ranges_to_none`).
4. **UI freeze during heavy solve** — compute must run off the main thread (Task 3 `WorkerTests`; Task 6 `test_compute_end_to_end` spins the event loop while the worker runs). A regression here makes the app appear hung.
5. **Balance sum ≠ 100** — soft warning only (never blocks), matching CLI behavior (Task 2 `test_validate_warnings`). Reviewer: confirm it is a warning, not an error.
6. **Swap with missing donor** — `donor_id` not in DB must not crash; status note only (Task 4 behavior + implicit in `test_swap_selection` coverage; add an explicit case if a reviewer wants it).

## Self-Review (run before first execution)

- **Spec coverage:** every one of the 4 input tiers maps to a panel (Vehicle/Overrides=Tasks 4, Slider ranges=Task 4, Calibration/Session=Task 5); every `build_setup` param the CLI exposes has a form field except `height_range` (intentionally per-side only) and `--save-sliders` (exposed as the Save-ranges button, Task 4); the visual design is fully specified in the Design Spec section (exact tokens, applied from Task 1, token-guarded by the smoke test). Gaps: none.
- **Proportion:** plan is decision-dense (signatures, verified DB shapes, exact test assertions) and does not transcribe widget layout code.
- **Type consistency:** `GuiRequest`/`GuiResult`/`TuningService`/`Worker`/`SetupForm`/`ResultsView`/`MainWindow` names are used identically across Tasks 2–7.
- **Verified against live DB (2026-07-12):** MR2 GT-S '97 = car `207` (engine 241 hp, balance 42/58, 1 swap BYH-R8 → donor `1365` = 420 hp / 429.5 Nm); car `3440` has preseeded `df_front [50,200]`; `TRACKS_DB` = 123 tracks keyed `id`/`name`; `build_setup` signature at `setup.py:146`.

