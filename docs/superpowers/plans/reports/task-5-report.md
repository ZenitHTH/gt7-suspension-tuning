# Task 5 Report: `SetupForm` part 2 — calibration, session, symptoms + full `collect()`/`validate()`

## What I implemented

Modified `gui/form.py` (added 3 widget groups, completed `collect()`, added `validate()`) and extended `tests/test_gui_form.py` (3 new tests). No new gui modules; did not touch `app.py`/`results.py`.

### New widget groups (attribute names exactly as specified)

**Calibration group**
- `g60_spin`/`g120_spin`/`g240_spin`: `QDoubleSpinBox` (0–9, 2 dp, `setSpecialValueText('')` at 0.0).
- `gref_f_spin`/`gref_r_spin`: `QSpinBox` (0–1000, 0 = unset).
- `solve_combo`: `QComboBox` from `SOLVE_OBJECTIVES`, item 0 `'—'` data `''`; **disabled** unless all 3 G spins non-zero (re-checked on every `valueChanged` via `_update_solve_gate`).
- Hint label: "Measure peak lateral G in-game at 60/120/240 km/h and the downforce you were running." (objectName `hintLabel`).

**Session group**
- `track_combo`: editable `QComboBox`; item 0 `'— (no track)'` data `''`, then all 123 `TRACKS_DB` names (data `id`); a `QCompleter` built from the track-name list is attached to the line-edit for search-as-you-type.
- `mode_combo`: `QComboBox` from `MODES`.
- `speed_spin`: `QDoubleSpinBox` (30–400, default 240).
- `widebody_check`, `controller_check`: `QCheckBox`.

**Symptoms group**
- `symptom_checks`: `Dict[str, QCheckBox]` keyed by the 6 `SYMPTOMS` values (display names from `_SYMPTOM_DISPLAY`, e.g. `entry_push` → "Entry push / understeer").
- `stab_low_spin`/`stab_high_spin`: `QDoubleSpinBox` (0–1, 2 dp, `setSpecialValueText('')` at 0).

### `collect()` completion
- `g_forces` = tuple only if all 3 G spins non-zero (else `None`).
- `g_ref_df` = tuple of the two ref spins when either non-zero (else `None`), via `_ref_df()`.
- `solve_objective` = `solve_combo.currentData() or None`.
- `track_id` = `_track_id()`: placeholder/empty → `None`; edited text matching a track item → its `id`; edited text matching no track → `None` + status note "Unknown track ignored" (warn).
- `mode` from `mode_combo`; `speed_kmh` from `speed_spin` (always in-range, never 0).
- `stability` = tuple only when both spins non-zero (else `None`).
- `symptoms` = list of checked keys, empty → `None`.
- `is_widebody`/`is_controller` from the checkboxes.
- Part-1 fields keep their existing `collect()` behavior.

### `validate()`
- `req = collect()`; `errors, warnings = service.validate(req)`.
- Errors rendered red (`kind='error'`, joined with newlines); if no errors, warnings rendered amber with a `⚠` prefix each (`kind='warn'`); if neither, status cleared (`kind='ok'`).
- Returns the error list.

## What I tested and results

Focused (all 8, incl. 3 new):
```
.venv/bin/python -m unittest tests.test_gui_form -v
Ran 8 tests ... OK
```
Full gui set (smoke/request/service/components/form — 29 tests):
```
.venv/bin/python -m unittest tests.test_gui_smoke tests.test_gui_request tests.test_gui_service tests.test_gui_components tests.test_gui_form
Ran 29 tests ... OK
```
New tests added: `test_gforces_gate_solve`, `test_collect_full_request`, `test_validate_blocks_bad_range`.

## Files changed
- `gui/form.py` (modified)
- `tests/test_gui_form.py` (extended)

## Rulings and self-review findings
- **Theme objectNames**: labels I created use `hintLabel` (matches `QLabel#hintLabel` in `gui/theme.py` → secondary 12px). No new status/warn label objectName was needed since `validate()` reuses the existing `status_label` + `set_status` (objectName `statusLabel`, ok/warn/error properties).
- **`track_id` unknown-track note**: I render the "Unknown track ignored" note as `kind='warn'` (amber) — a soft note, not a hard error, since `collect()` returns a valid request with `track_id=None`. The service never sees a bogus id.
- **`speed_kmh`**: the spin is 30–400 so it can never be 0; I always send its value (never `None`). This matches "30–400, default 240" and the `GuiRequest.speed_kmh: Optional[float]` field.
- **`g_forces` partial input**: if only some G spins are set, `g_forces` stays `None` (per brief "all 3 non-zero"). The service's "Solver needs G-force calibration" warning then governs the `solve_objective`-without-G case.
- **`solve_objective` without G-forces**: the combo is disabled when uncalibrated, so `currentData()` is `''` → `None`; even if set, the service emits the "solve will be skipped" warning.
- **QCompleter scope**: the completer list is built from `TRACKS_DB` names only (excludes the `'— (no track)'` placeholder), so typing does not offer the placeholder as a suggestion.
- **`validate()` precedence**: errors take precedence over warnings in the status label (if both present, errors are shown red and warnings are suppressed from the label but the returned error list is complete). This matches "blocks compute on hard errors" — the caller gates on the returned list.
- **Pre-existing `qt.qpa.fonts` note**: the full-suite run prints a harmless `qt.qpa.fonts: Populating font family aliases...` line from `test_gui_components` (untouched by this task). Confirmed it is present independent of my change (components test is unchanged; it's an offscreen font-caching advisory, not a failure). All 29 tests pass.
- **Float equality in tests**: `test_collect_full_request` asserts exact float tuples (e.g. `(1.04, 1.19, 1.38)`, `(0.1, 0.3)`); the spins are 2-dp and set to those literals, so `QDoubleSpinBox.value()` round-trips exactly.

## Issues or concerns
- None blocking. The `qt.qpa.fonts` advisory in combined runs is cosmetic and pre-existing (originates in `test_gui_components`, which this task did not modify).
- Commit: `6df3dc1 gui: SetupForm calibration/session/symptoms + collect/validate` (2 files changed, +280/-10).

## FIX REPORT (review fixes)

Fixes for the two Important findings from the task-5 review (reviewed head: `6df3dc1`).

### Finding 1 — partial `g_ref_df` sent literal values instead of `(v, v)`
- **File:** `gui/form.py` (`_ref_df()`, was lines 352-357)
- **Before:** returned `(lo, hi)` as typed; front-only (200, 0) produced a hard `min > max` service error that blocked compute, rear-only (0, 310) silently passed — both wrong per the brief's rule.
- **After:** when exactly one spin is 0, the set value is used for both axes (front-only 200 → `(200, 200)`; rear-only 310 → `(310, 310)`); both 0 → `None`; both set → literal pair (unchanged). Docstring updated to state the rule ("the service warning covers the gap").

### Finding 2 — no test pins the partial-`g_ref_df` rule
- **File:** `tests/test_gui_form.py`
- **Added:** `test_collect_partial_gref_df_applies_both_axes` — asserts `collect().g_ref_df == (200, 200)` front-only and `== (310, 310)` rear-only, plus both-zero → `None` (unset). Both-set → literal pair is already pinned by `test_collect_full_request` (`(200, 310)`).

### Covering tests run
```
.venv/bin/python -m unittest tests.test_gui_form -v
Ran 9 tests in 1.070s
OK
```
(9 = 8 pre-existing + the new test; includes the existing collect/gforces/validate tests.)

Full gui set:
```
.venv/bin/python -m unittest tests.test_gui_smoke tests.test_gui_request tests.test_gui_service tests.test_gui_components tests.test_gui_form
Ran 30 tests in 1.704s
OK
```
(Only the pre-existing cosmetic `qt.qpa.fonts` advisory from `test_gui_components`; no failures.)

### Commit
- `9c3baf6 fix(gui): g_ref_df single value applies to both axes per brief` (2 files changed: `gui/form.py` +8/-1, `tests/test_gui_form.py` +13)
