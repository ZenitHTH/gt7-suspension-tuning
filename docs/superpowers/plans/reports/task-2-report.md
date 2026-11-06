# Task 2 Report: `GuiRequest` / `GuiResult` + `TuningService`

**Status:** DONE
**Commit:** `9c155b3` — `gui: TuningService + request/result dataclasses` (4 files, 464 insertions)

## What the prior attempt had done and what I found wrong/missing

The crashed session left four untracked files:

| File | State found | Verdict vs brief |
|---|---|---|
| `gui/request.py` | Complete | **Correct.** All 23 `GuiRequest` fields with brief defaults, `GuiResult` with `ok` property, and the five choice tuples verbatim (checked against Global Constraints and `cli.py` values). No changes needed. |
| `tests/test_gui_request.py` | Complete | **Correct.** Covers the brief's "dataclass defaults; `GuiResult.ok` True/False" list (plus a choice-tuple verbatim check and a warnings-list-independence check, both additive and passing). No changes needed. |
| `tests/test_gui_service.py` | Complete | **Correct.** All 7 brief-listed tests present (`test_mr2_compute_ok`, `test_compute_bad_car`, `test_validate_errors`, `test_validate_warnings`, `test_swaps_and_ranges`, `test_save_sliders_roundtrip`, `test_kwargs_mapping`) plus an extra `test_search_cars_and_tracks`. Fixture facts verified against the real DB (car '207' = MR2 GT-S '97, 241 hp, 42/58, one swap `BYH-R8`/donor '1365'; car '3440' preseeded `df_front [50,200]`; no car fuzzy-matches 'nope'). No changes needed. |
| `gui/service.py` | **Partial stub — file ended at `get_slider_ranges`** | Missing the three methods the brief mandates: `save_sliders` (with `db_path` override), `validate`, `compute`. The six lookup methods (`search_cars`, `get_car`, `search_tracks`, `get_track`, `get_swaps`, `get_slider_ranges`) were complete and correct, including the saved+preseeded merge (needed because `db.interface.get_slider_ranges` returns preseeded-only values). The stub's two module constants (`_SLIDER_RANGE_FIELDS` = 6 slider fields, `_RANGE_FIELDS` = 8 two-value range fields) revealed the intended validate design. |

Baseline confirmed: 13 tests ran, 6 errors (`AttributeError` on `validate`/`save_sliders`/`compute`).

## What I implemented/changed

Only `gui/service.py` was modified (appended 3 methods, ~90 lines; no test files touched):

1. **`save_sliders(car_id, ranges, db_path=None) -> bool`** — delegates to `db.interface.save_car_sliders(car_id, ranges, db_path=db_path)`. Important: the DB function returns the merged `slider_ranges` dict (`{}` on missing file/car), not a bool, so the service converts via `bool(saved)` → `False` on missing car, satisfying the locked signature.
2. **`validate(req) -> (errors, warnings)`** — implements the brief's rules verbatim:
   - error `Car not found: {car_id}` when `get_car` returns None
   - error naming the field for `min > max` and for any value `< 0` across all 8 two-value range fields
   - warning `No {name} range — using saved/preseeded DB values` for None fields (see Ruling 1 below for the field set)
   - warning `Solver needs G-force calibration; solve will be skipped`
   - warning `Balance front+rear = {n} (expected 100)` when `abs(sum-100) > 1`
   - warning `G-forces without reference downforce; profile anchored at current DF`
   - Defensive guard: a non-pair range value produces a "must be a (min, max) pair" error instead of an exception (protects `compute`'s never-raises contract).
3. **`compute(req) -> GuiResult`** — never raises. Resolves car (error result on missing, message `Car not found: {car_id}`), resolves track only when `track_id` is truthy, builds the **exact 22-key kwargs dict** from the brief (`df_*_range`, `height_front_range`/`height_rear_range` per-side, `fn_*_range`, etc.; `height_range` never set), wraps `setup.build_setup` + `format_setup_sheet` in try/except → `GuiResult(error=repr(e))`, and attaches `validate` warnings to the result (success and error paths alike). `format_setup_sheet` is called through the `gui.service` module global so the kwargs-mapping test's `mock.patch.object(gui.service, 'format_setup_sheet')` intercepts it; `build_setup` is called through the `setup` module object so `mock.patch.object(gui.service.setup, 'build_setup')` works.

## What I tested and test results

```
$ QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.test_gui_request tests.test_gui_service tests.test_gui_smoke -v
test_choice_tuples_match_cli_verbatim (tests.test_gui_request.GuiRequestTest) ... ok
test_defaults (tests.test_gui_request.GuiRequestTest) ... ok
test_ok_false_when_error (tests.test_gui_request.GuiResultTest) ... ok
test_ok_true_when_no_error (tests.test_gui_request.GuiResultTest) ... ok
test_warnings_lists_are_independent (tests.test_gui_request.GuiResultTest) ... ok
test_compute_bad_car (tests.test_gui_service.TuningServiceTest) ... ok
test_kwargs_mapping (tests.test_gui_service.TuningServiceTest) ... ok
test_mr2_compute_ok (tests.test_gui_service.TuningServiceTest) ... ok
test_save_sliders_roundtrip (tests.test_gui_service.TuningServiceTest) ... ok
test_search_cars_and_tracks (tests.test_gui_service.TuningServiceTest) ... ok
test_swaps_and_ranges (tests.test_gui_service.TuningServiceTest) ... ok
test_validate_errors (tests.test_gui_service.TuningServiceTest) ... ok
test_validate_warnings (tests.test_gui_service.TuningServiceTest) ... ok
test_main_defined_in_gui_app (tests.test_gui_smoke.GuiSmokeTest) ... ok
test_subprocess_launch_offscreen_exits_zero (tests.test_gui_smoke.GuiSmokeTest) ... ok
test_theme_qss_uses_design_tokens (tests.test_gui_smoke.GuiSmokeTest) ... ok
----------------------------------------------------------------------
Ran 16 tests in 0.705s

OK
```

- 16/16 green, pristine output (no warnings, no stray prints).
- Extra robustness probes (manual): `compute(GuiRequest(car_id='207', df_front='junk'))` → no raise, `ok=True` (core tolerated the junk range; contract is never-raises, held); `compute` with an unresolvable `track_id` → `track=None` passes through, `ok=True` (brief mandates no track-missing error).
- `test_save_sliders_roundtrip` copies `data/cars_master.json` to a temp file via `db.loader.get_data_dir`, saves into the copy with `db_path=tmp`, asserts the reload shows `[10, 20]`, asserts `save_sliders('nope', ...)` → `False`, and byte-compares the real file before/after — untouched (also confirmed via `git status` on `data/`).

## TDD Evidence

Red→green within this session: after appending the three methods, the first run was 15/16 with a single failure — `test_mr2_compute_ok`, `assertEqual(res.warnings, [])` hit `['No stability range — using saved/preseeded DB values']` (see Ruling 1). Fixed the None-warning field set, reran → 16/16 green. The full brief test list was present (written by the prior attempt) before any of my implementation work, so the tests were the spec and stayed untouched.

## Files changed

- `gui/service.py` — added `save_sliders`, `validate`, `compute`; clarified the `_SLIDER_RANGE_FIELDS` comment. Committed in `9c155b3` together with the prior attempt's `gui/request.py` and both test files (verified correct and committed as-is).

## Rulings and self-review findings

1. **Ruling — "8 range fields" vs the None-range warning (brief/test conflict).** The brief's validate rule says the `No {name} range — using saved/preseeded DB values` warning fires for "any of the 8 range fields" (the 6 slider fields + `g_ref_df` + `stability`), but the brief's own `test_mr2_compute_ok` fixture leaves `stability=None` and the delivered test asserts `res.warnings == []` — the two cannot both hold. I resolved in favor of the tests and the message's own semantics: the None warning applies to the **6 slider fields** (the only fields with saved/preseeded DB fallback values — the warning literally promises "using saved/preseeded DB values", which is false for `stability`); the `min > max` / `< 0` error checks still cover **all 8** two-value range fields. This also matches the prior implementer's two-constant design left in the stub. `g_ref_df=None` has its own dedicated warning per the brief, so nothing is lost.
2. **Ruling — warnings attached to error results.** The brief says "attach `validate` warnings to the result" without scoping; I attach them on both success and error paths (harmless, informative; no test contradicts).
3. **Ruling — missing track is not an error.** Brief: "resolve `track` (only when `track_id` truthy)"; only the car gets an explicit error result. An unresolvable `track_id` passes `track=None` into `build_setup` (its default). No extra error invented.
4. **Quality/YAGNI:** no new deps, no shelling out, direct imports only (`setup`, `sheet_formatter`, `db.interface`, `scripts.gt7_db`); no `lib/`/`setup.py`/`db/` modifications; stdlib `unittest` conventions with `QT_QPA_PLATFORM=offscreen` setdefault before imports; `GuiResult.warnings` uses `default_factory` (independence verified by test). Committed exactly the 4 task paths; unrelated dirty files (pycache, `.DS_Store`, `lib/grip.py`, `tests/test_grip.py`, `lib/__init__.py`) left alone.

## Issues / concerns

- The brief's literal "8 range fields" wording remains in conflict with its own test expectations if read as covering the None-warning; resolved per Ruling 1. If a later task (e.g. `gui/form.py`) expects a "No stability range" warning, no such expectation exists in the brief or tests today.
- `save_car_sliders` returns the merged dict rather than a bool; `save_sliders` bridges with `bool(...)`. Untested edge: a found car whose merged `slider_ranges` is empty (only if `ranges={}` were passed) would report `False` — not reachable from the GUI (ranges are non-empty pairs) and out of brief scope.
- `compute` does not pre-block on `validate` errors (e.g. an inverted range still reaches `build_setup`); the brief mandates only the car-missing error result and try/except for core failures, and `validate` is the consumer-facing gate — matches the locked behavior.


