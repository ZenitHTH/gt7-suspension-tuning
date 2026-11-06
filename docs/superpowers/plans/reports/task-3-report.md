# Task 3 Report: `Worker(QObject)` — off-thread compute

**Commit:** `7b0abdb` — `gui: Worker thread wrapper` (branch `cline/c8601`)
**Date:** 2026-07-12

## What was implemented

Per the task brief and the plan's File Structure, `Worker(QObject)` was added
to `gui/service.py` (the plan places it there alongside `TuningService`):

```python
class Worker(QObject):
    finished = pyqtSignal(object)   # GuiResult
    failed = pyqtSignal(str)

    def __init__(self, service: TuningService, req: GuiRequest,
                 parent: Optional[QObject] = None) -> None: ...

    def run(self) -> None           # res = service.compute(req); emit finished(res)
```

- `run()` calls `service.compute(req)` and emits `finished` with the
  `GuiResult`; the whole call is wrapped in `try/except Exception` emitting
  `failed(str(e))` only on the unexpected (belt-and-braces, since
  `compute()` never raises — errors arrive as `GuiResult(error=...)`).
- `__init__` stores `service` + `req` and forwards `parent` to `QObject`.
- Module docstring updated: "Qt-free tuning facade (Task 2)" →
  "Tuning service facade + off-thread worker (Tasks 2-3)", noting that
  `Worker` is the off-UI-thread wrapper. The class docstring documents the
  intended app-layer usage (connect signals → `moveToThread()` → connect
  thread `started` to `run()`), which Task 6 will wire up.
- Imports: `from PyQt6.QtCore import QObject, pyqtSignal` added between the
  stdlib and local import groups (consistent with `gui/app.py`'s PyQt6
  import prefix).

Also added `WorkerTests` to `tests/test_gui_service.py` exactly per the
brief: reuses the existing `_mr2_request()` fixture (car 207, tutorial
values); `QCoreApplication` created in `setUpClass` via
`QCoreApplication.instance() or QCoreApplication(['test'])` (same
ensure-app idiom as `tests/test_gui_smoke.py`); collector list;
`worker = Worker(TuningService(), _mr2_request())`;
`worker.finished.connect(collector.append)`; `worker.run()` called directly
(synchronous, no `QThread` needed); asserts exactly one `GuiResult` in the
collector and that `res.ok` is True. The test file's existing
`os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')` (line 12) already
precedes all Qt imports; the new `QCoreApplication` import sits after it.

## What was tested and results

All commands run from the repo root with the project venv.

1. **Target module (brief step 3):**
   `.venv/bin/python -m unittest tests.test_gui_service -v`
   → `Ran 9 tests ... OK` — all 8 pre-existing `TuningServiceTest` cases plus
   `WorkerTests.test_run_emits_finished` pass:
   ```
   test_run_emits_finished (tests.test_gui_service.WorkerTests.test_run_emits_finished) ... ok
   ----------------------------------------------------------------------
   Ran 9 tests in 0.051s
   OK
   ```
2. **Smoke test regression check:**
   `.venv/bin/python -m unittest tests.test_gui_smoke tests.test_gui_request -v`
   → `Ran 8 tests ... OK` (theme tokens, subprocess `python -m gui` exit 0,
   request dataclasses all green).
3. **Full-suite safety net:**
   `.venv/bin/python -m unittest discover -s tests -v`
   → `Ran 100 tests ... OK`. Only `tests/test_gui_service.py` imports
   `gui.service` (verified by grep), so the new module-level PyQt6 import
   cannot affect non-GUI tests; the full suite confirms no incidental break.

## Files changed

- `gui/service.py` — module docstring updated; `from PyQt6.QtCore import
  QObject, pyqtSignal` added; `Worker(QObject)` class appended (~26 lines).
- `tests/test_gui_service.py` — module docstring updated; imports extended
  (`QCoreApplication`, `GuiResult`, `Worker`); `WorkerTests` class added
  (~16 lines).

Total: 2 files, +55/−5. Committed **only** these two paths; the unrelated
dirty files (pycache, `.DS_Store`, untracked `lib/grip.py` /
`tests/test_grip.py` / `lib/__init__.py` changes, plan-doc edits under
`docs/`) were left untouched as instructed.

## Rulings

1. **`pyqtSignal` instead of the brief's `Signal`.** The installed PyQt6
   build (3.15-compatible wheel in `.venv/`) does not expose the `Signal`
   alias — `from PyQt6.QtCore import Signal` fails with
   `ImportError: cannot import name 'Signal'`; only `pyqtSignal` is
   available (verified via introspection: `PyQt6.QtCore` has `pyqtSignal`,
   no `Signal`). Used `pyqtSignal(object)` / `pyqtSignal(str)` — the same
   API the brief intends, only the name differs in this build. Staying on
   `pyqtSignal` is consistent across both.
2. **Module is no longer strictly Qt-free.** `gui/service.py` now imports
   `PyQt6.QtCore` at module level because `Worker` lives there (the plan's
   File Structure explicitly assigns `Worker(QObject)` to this file).
   This is the intended design consequence; `TuningService` itself remains
   plain Python, and the test file's offscreen guard runs before the
   import, so no behavioral change for consumers.
3. **`WorkerTests` uses `QCoreApplication.instance() or QCoreApplication([...])`**
   rather than unconditionally creating a new instance, matching the
   existing `_ensure_app()` idiom in `tests/test_gui_smoke.py` and avoiding
   a "second QCoreApplication" crash if tests run in one process.
4. **No `failed`-path test.** The brief specifies only the `finished` test
   (one `GuiResult`, `ok`). The `failed` branch is defensive by design
   (`compute()` never raises), so forcing it via a mock that raises was
   judged out of scope for the brief; left to the Task 6 integration test
   if deemed useful.

## Self-review findings

- Interface matches the brief 1:1: `finished` (object → `GuiResult`),
  `failed` (str), `__init__(service, req, parent=None)`, `run()` =
  `compute` + emit with `try/except` belt-and-braces. ✓
- Test matches the brief step 2 point-by-point (offscreen env already set
  before Qt imports; `QCoreApplication` in `setUpClass`; collector; direct
  synchronous `run()`; asserts one `GuiResult` + `ok`). ✓
- No new gui modules created; `gui/form.py`, `gui/app.py`,
  `gui/components.py` untouched (later tasks). ✓
- `Worker` does not itself start threads or event loops — it's a plain
  callable worker, which is what makes the unit test synchronous and the
  later `moveToThread` wiring (Task 6) the sole owner of threading. ✓
- `pyqtSignal(object)` passing a dataclass across a queued (cross-thread)
  connection is the documented PyQt way to pass arbitrary Python objects;
  the direct-connection unit path (verified green) has no marshalling
  concern. Minor residual risk for the cross-thread path in Task 6: none
  expected, but it's exercised for the first time there.
- Commit contains exactly the two intended paths:
  `2 files changed, 55 insertions(+), 5 deletions(-)`. ✓

## Issues / concerns

None blocking. Only notes: the `failed`-signal path is untested (ruling 4,
intentional per the brief), and the `pyqtSignal` naming is a build-specific
deviation from the brief's literal `Signal` (ruling 1) — both documented
above.

