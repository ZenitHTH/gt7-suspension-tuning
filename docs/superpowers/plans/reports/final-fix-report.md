# GT7 Suspension GUI — final review fix wave

## FIX WAVE (commit dbf104d — `fix(gui): df range cap 2000 + close-during-solve thread guard`)

Scope: the two findings in `.superpowers/sdd/2026-07-12-gt7-suspension-gui/final-findings.md`
(Critical: DF spinbox clamp; Important: close-during-solve qFatal).

### Issue 1 (Critical) — DF spinboxes clamp preseeded ranges

**Change** (gui/form.py): `df_f`/`df_r` `RangePair` `max_v` 1000 → 2000
(preseeded DF ranges in `db/interface.py` `PRESEEDED_SLIDER_RANGES` reach
1700 for cars 3342/3374/3517; 2000 ≥ 1700 leaves headroom).
Also: one-line docs/GUI.md note — "Save ranges to DB merges the current
form values into the car's saved `slider_ranges` in `data/cars_master.json`,
shadowing any preseeded values."

**Reproduction evidence (before fix)** — car 3374 prefill script
(offscreen): `df_f.value(): (800, 1000)` (DB wants (800, 1200)),
`df_r.value(): (1000, 1000)` (DB wants (1200, 1600)),
`max_spin.maximum(): 1000` → "PREFILL WRONG (clamped)".
**After fix**: `df_f (800, 1200)`, `df_r (1200, 1600)`, caps 2000 →
"PREFILL CORRECT".

**Covering test** (tests/test_gui_form.py):
`SetupFormTest.test_car_3374_prefill_df_ranges_not_clamped` — pins car 3374
prefill exactly ((800,1200)/(1200,1600)), asserts spin caps ≥ 1200/1600,
and `collect()` hands the solver the exact DB ranges.

### Issue 2 (Important) — closing the window during a running solve hard-aborts

**Change** (gui/app.py): `MainWindow.closeEvent` guard. A solve in flight
(`_in_flight`, set in `_on_compute`, cleared by `_on_thread_stopped` on the
thread's `finished` signal) makes closeEvent post `quit()` to the solve
thread's event loop, then poll (`wait(50)` + `processEvents()` + 5 ms sleep)
up to `_CLOSE_WAIT_S = 1.5 s`; the event is accepted only once the thread is
provably stopped (`_in_flight` cleared by the delivered `thread.finished`),
otherwise the event is ignored so the window stays open until the solve
finishes (a later close then succeeds). Re-entrancy-safe via `_closing`
(a second closeEvent while the first polls ignores). Note in the docstring:
with the offscreen platform `processEvents()` can itself block until the
in-flight solve finishes, so the bound is enforced between event passes;
on real platforms the bound holds strictly.

**Reproduction evidence (before fix)** — worker `QThread` with a running
Python solve, window/process teardown while the thread is still running
(offscreen, stubbed 1–3 s solve): `QThread: Destroyed while thread '' is
still running` → `Abort trap: 6` (SIGABRT), process exit code 134
(reproduced twice: minimal QThread probe and MainWindow close probe).
**After fix** — same scenario (close called while the solve thread is
running): `close()` returns after 1.02 s having absorbed the 1.0 s stub
solve, `visible=False`, worker ran the compute, `in_flight=False`, process
exit code 0 with no qFatal.

**Covering test** (tests/test_gui_app.py):
`MainWindowTest.test_close_during_solve_stops_thread_cleanly` — starts a
compute with a stubbed 0.4 s `service.compute`, closes the window while the
solve is in flight (no event pump before the close, which would complete the
solve first), then asserts: close accepted within bounds (0.25 s ≤ waited
< 2 s — the lower bound guards a vacuous instant-accept), window hidden,
worker ran the stub (`ran` flag), `_in_flight` cleared (thread fully
stopped, `thread.finished` delivered), thread not running (tolerating an
already deleteLater'd C++ wrapper), and a second (re-entrant) close accepts
immediately. The test process surviving is itself the no-abort assertion.
Run 5× consecutively: all OK (the offscreen PyQt6 6.12 / Python 3.15 combo
makes worker-slot dispatch sensitive to when the main thread pumps events;
this flow is deterministic with respect to that).

### Verification

Commands (repo root):
- `.venv/bin/python -m unittest tests.test_gui_form -v` → `Ran 10 tests … OK`
- `.venv/bin/python -m unittest tests.test_gui_app -v` → `Ran 4 tests … OK`
  (`[e2e] solve finished in 0.1s`)
- `.venv/bin/python -m unittest discover -s tests` →
  `Ran 118 tests in 2.335s / OK` (was 116; +2 new tests), pristine output
  (only the e2e `[e2e]` print on stdout).

Commit: `dbf104d fix(gui): df range cap 2000 + close-during-solve thread
guard` — only in-scope paths staged: gui/form.py, gui/app.py, docs/GUI.md,
tests/test_gui_form.py, tests/test_gui_app.py. Pre-existing dirty/untracked
files (pycache, .DS_Store, lib/grip.py, tests/test_grip.py,
docs/superpowers plan/ledger edits) left untouched.
