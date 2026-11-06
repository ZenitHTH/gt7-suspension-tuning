# Task 4 Report — `SetupForm` part 1: RangePair + vehicle/tire/ranges/overrides

## Status: DONE

Commit: `46313b6` `gui: RangePair component + SetupForm vehicle/tire/ranges/overrides panels` (branch `cline/c8601`; 4 files, 639 insertions).

## What was implemented

### `gui/components.py` — `RangePair` (locked interface)
- `RangePair(QWidget)` with `min_spin`/`max_spin` (`QSpinBox` for `kind='int'`, `QDoubleSpinBox` 2 dp for `kind='float'`), ctor `(label, kind='int', max_v=1000, parent=None)`.
- `value() -> Optional[tuple]`: `(min, max)`, `None` iff both are 0 — the (0,0)→None rule lives **only** here.
- `set_value(pair)`: `None` → both spins 0.
- The name label carries `objectName('hintLabel')` (theme secondary-text selector).

### `gui/form.py` — `SetupForm(QWidget)`
All public attributes exactly as the brief lists them:
- **Vehicle**: `car_search` (textChanged → `_refill_cars` refills `car_combo` from `service.search_cars(text)`), `car_combo` (itemText=name, data=car id), `swap_combo` (item 0 `'Stock engine'` data `''`, then swap engine / `donor_id`), `db_info_label` (`objectName('dbInfoLabel')`, word-wrapped, text-selectable; name, mass, power hp, torque Nm, drivetrain, weight balance F:R, engine code).
- **Tire**: `tire_combo` from `TIRE_COMPOUNDS`, default `'SS'`.
- **Slider ranges**: `df_f`, `df_r` (int, 1000), `hf`, `hr` (int, 400), `fn_f`, `fn_r` (float, 10.0, 2 dp) + `save_ranges_btn` ("Save ranges to DB").
- **Overrides**: `mass_use_db`/`power_use_db`/`torque_use_db`/`balance_use_db` checkboxes (checked by default), `mass_spin`/`power_spin` (QSpinBox 0–3000), `torque_spin` (QDoubleSpinBox 0–1500), `bal_f_spin`/`bal_r_spin` (0–100), `drivetrain_combo` from `DRIVETRAINS`.
- `status_label` at the bottom (`objectName('statusLabel')`, word-wrapped); `set_status(text, kind)` sets the `ok`/`warn`/`error` dynamic properties the theme QSS targets and re-polishes.
- `on_car_selected(car_id)` wired to `car_combo.currentIndexChanged[int]` (via a small adapter; PyQt6 overload disambiguation needed for the data-based signal) implementing all 5 brief steps: None → clear + status `Car not found`; fill `db_info_label`; reset checkboxes checked + spinboxes to DB values (incl. drivetrain combo synced to car's drivetrain); prefill ranges from `service.get_slider_ranges` (missing key → 0/0); refill `swap_combo`, swap selection → donor `power_hp`/`torque_nm` into spinboxes + uncheck `power_use_db`/`torque_use_db`; donor missing → status error, no crash. Selecting `'Stock engine'` again restores DB values and re-checks.
- `save_ranges_btn` → collects the 6 pairs, saves only non-None pairs via `service.save_sliders(car_id, ...)`, flashes ok/warn/error status.
- `collect()` (partial): `car_id`, `tire`, 6 range pairs via `RangePair.value()`; unchecked `*_use_db` → spinbox override (checked → `None`); `custom_balance` only when `balance_use_db` is off; `custom_drivetrain` = combo text; all session/calibration fields keep `GuiRequest` defaults (Task 5).

### Tests (offscreen, shared-`QApplication` idiom)
- `tests/test_gui_components.py`: `test_range_pair_rule` (brief), `test_int_kind_uses_int_spins`, `test_float_kind_exact_tuple` (exact `(1.5, 3.5)`), `test_zero_min_only_is_not_none` (single-0 is a legitimate range).
- `tests/test_gui_form.py`: `test_car_prefill` (car 3440: label contains short_name + `381 hp`/`490.3 Nm`/`1290 kg`/`RR`/`40:60`; `df_f == (50, 200)`, `df_r == (140, 290)`, `fn_f is None`, `hf is None`; overrides at DB values; swap combo stock-only), `test_car_not_found_clears_and_notes`, `test_collect_empty_ranges_to_none` (0/0 → `None`; 50/200 → `(50, 200)`; unchecked overrides → values; balance off → `(42, 58)`; session fields at defaults), `test_swap_selection` (car 207: stock 241 hp/304 Nm → BYH-R8 → `power_use_db` False, 420 hp, 429.5 Nm → back to stock restores), `test_swap_missing_donor_no_crash` (mocked missing donor → status note, no crash — plan Review Focus item 6 explicit case).

## Test results (commands + output)

- Focused: `.venv/bin/python -m unittest tests.test_gui_components tests.test_gui_form -v`
  → `Ran 9 tests ... OK` — pristine output (no Qt warnings; see Ruling 4 on ordering).
- Full gui set (brief order): `.venv/bin/python -m unittest tests.test_gui_smoke tests.test_gui_request tests.test_gui_service tests.test_gui_components tests.test_gui_form`
  → `Ran 26 tests ... OK`.
- Canonical discover order: `.venv/bin/python -m unittest discover -s tests -p 'test_gui_*.py'`
  → `Ran 26 tests ... OK`, zero `qt.qpa.fonts` lines.
- Whole suite: `.venv/bin/python -m unittest discover -s tests`
  → `Ran 109 tests ... OK`.

## Files changed
- `gui/components.py` (new, 59 lines)
- `gui/form.py` (new, 370 lines)
- `tests/test_gui_components.py` (new, 73 lines)
- `tests/test_gui_form.py` (new, 137 lines)

Committed exactly these four paths; unrelated dirty files (pycache, .DS_Store, lib/grip.py, etc.) left as found.

## Rulings and self-review findings

1. **"8 × RangePair" is a plan typo — implemented 6.** The brief/plan both say "8 ×" but enumerate exactly 6 named pairs (`df_f, df_r, hf, hr, fn_f, fn_r`); `GuiRequest` has exactly 6 range fields and the service defines 6 slider-range fields. Implemented the 6 named pairs.
2. **collect() override semantics.** The brief line "unchecked `*_use_db` → `None` override" conflicts with the balance line ("balance only when `balance_use_db` is off"), with the swap behavior (swap unchecks `power/torque_use_db` so donor values take effect), and with Task 5's `test_collect_full_request` (`custom_power == 630`). Ruled: **unchecked → spinbox value becomes the override; checked → `None`** (checkbox means "use DB"). Documented in `collect()`'s docstring.
3. **`custom_drivetrain` always sent as `drivetrain_combo.currentText()`.** The brief gives no use-DB checkbox for drivetrain. `on_car_selected` syncs the combo to the car's stock drivetrain, so the sent value equals the stock value unless the user changes it (a no-op override); Task 5/6 flows unaffected.
4. **Test-process coexistence fixes (both new test files).**
   - The shared `QApplication` is kept in a module-level `_APP` — the plain `QApplication.instance() or QApplication([])` idiom silently loses the app (PyQt deletes the C++ object when the wrapper is GC'd → "Must construct a QApplication before a QWidget").
   - `_ensure_app` treats a leftover bare `QCoreApplication` (held by `tests/test_gui_service` `WorkerTests.setUpClass`) as *not* a QApplication: `QApplication.instance()` returns it, so the `or` short-circuits and no widget-capable app exists. A real `QApplication([])` is built when the instance is not a `QApplication`. Both orders (service-first and components-first) now pass in one process.
   - `os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.fonts.warning=false')` before the Qt import suppresses the macOS "Populating font family aliases" stderr line in the focused command and the discover order. **Residual:** if a module that imports PyQt6 without the rule (e.g. `test_gui_smoke` listed first) initializes PyQt6 first in the same process, Qt reads the rule at its first PyQt6 import and one cosmetic line can still appear (26/26 green; verified: 1 line in smoke-first explicit order, 0 lines in discover/focused order). Fully silencing it would require touching Task 1's `test_gui_smoke.py` (out of scope; commit restricted to the four paths).
5. **Axle widths not in the DB.** The brief's `db_info_label` description mentions "axle widths", but car records only carry `dimensions_mm` {length, width, height} — no axle fields (verified on cars 207 and 3440). The label shows name, mass, power, torque, drivetrain, weight balance F:R (matching the plan's manual-smoke "241 hp / 42:58 / MR" expectation) and engine code; no invented field.
6. **Extra behaviors beyond the brief's minimum (small, aligned with brief/plan):** selecting `'Stock engine'` restores DB power/torque and re-checks the use-DB boxes (consistent inverse of the swap action); `car_combo` prefilled with all cars at init; status messages styled via the theme's `statusLabel` ok/warn/error properties; explicit missing-donor test (plan Review Focus 6: "add an explicit case if a reviewer wants it" — added, it's cheap).
7. **Quality/YAGNI:** no results/app changes (Tasks 6–7); no new deps; (0,0)→None confined to `RangePair`; `collect()` returns a plain `GuiRequest` with Task 5 fields at defaults; private helpers stay private; public surface matches the brief's attribute list verbatim (later tasks' tests target them by name).

## Issues / concerns
- None blocking. Only the residual cosmetic `qt.qpa.fonts` line in smoke-first single-process orderings (Ruling 4), and the plan's "8 ×" typo (Ruling 1) worth correcting in the plan doc if desired.
- Init prefills `car_combo` with the full car list and loads the first car, so the form is live immediately; typing filters while preserving the selection when it survives.