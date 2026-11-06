# Task 1 Report: Venv, PyQt6, gui package skeleton

**Status:** DONE
**Commit:** `1aa3175` — `gui: venv scaffold + themed skeleton window (Design Spec tokens)` (branch `cline/c8601`)

## What was implemented

1. **`.venv`** created with `python3 -m venv .venv` (Python 3.15.2), then
   `.venv/bin/pip install --upgrade pip 'PyQt6>=6.7,<7'` →
   **PyQt6 6.12.0** (+ PyQt6-Qt6 6.12.0, PyQt6-sip 13.13.0, pip 26.3).
   - Verify step passed on first try:
     `.venv/bin/python -c "from PyQt6.QtWidgets import QApplication; print('ok')"` → `ok`.
   - **No PySide6 fallback needed.** PyQt6 is the binding for all later tasks.
2. **`.gitignore`** — appended `.venv/` (file had 3 pre-existing lines).
3. **`gui/__init__.py`** — empty package marker.
4. **`gui/theme.py`** — `QSS: str` + `apply(app)`. 31 non-blank QSS lines (limit 70).
   All 15 Design Spec tokens present verbatim: `#1b1d23 #23262e #14161a #3a3f4d
   #e6e8ee #9aa0ae #e5484d #f2555a #c73a3f #ffb454 #ff6369 #c62828 #4ade80
   #ffffff #16181d` + `monospace` 12.5px / 16px padding. Per-component rules
   implemented: QGroupBox (bg-panel, 1px border, 8px radius, 12px padding, bold
   title); inputs (bg-field, 4px radius, 4px 8px padding, 28px min-height,
   2px accent focus border, disabled 50% opacity + text-secondary); buttons
   (default bg-panel + hover border lightening; `#computeButton` accent bg /
   white bold / 40px with hover `#f2555a` / pressed `#c73a3f`); secondary
   labels 12px `#9aa0ae`; warnings label bold `#ffb454`; status label 12px with
   `ok`/`warn`/`error` dynamic-property states; sheet QTextBrowser white +
   monospace 12.5px; 10px transparent-track scrollbars.
   - QSS objectName selectors chosen for widgets named by later tasks:
     `statusLabel`, `dbInfoLabel`, `hintLabel`, `warningsLabel`,
     `computeButton`, `sheetBrowser`.
5. **`gui/app.py`** — `main(auto_quit: int = 0) -> int`: `QApplication([])`,
   `gui.theme.apply(app)`, 600x400 `QMainWindow` titled "GT7 Suspension Tuner",
   `win.show()`, `QTimer.singleShot(auto_quit, app.quit)` when > 0, returns
   `app.exec()`.
6. **`gui/__main__.py`** — entry point, `raise SystemExit(main(auto_quit))`;
   `auto_quit` read from `GT7_GUI_AUTO_QUIT_MS` env (default 0).
7. **`tests/test_gui_smoke.py`** — stdlib unittest, `BASE_DIR` + `sys.path`
   pattern, `os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')` before Qt
   imports. 3 tests: (a) `gui.app.main.__module__ == 'gui.app'`; (b) QSS token
   guard (`#1b1d23`, `#e5484d`, `monospace`) + ≤ 70 non-blank QSS lines;
   (c) subprocess `.venv/bin/python -m gui` with `QT_QPA_PLATFORM=offscreen`
   + 15 s timeout → returncode 0.

## What was tested (commands + results)

- `.venv/bin/python -c "from PyQt6.QtWidgets import QApplication; print('ok')"`
  → `ok`
- `.venv/bin/python -m unittest tests.test_gui_smoke -v`
  → 3/3 OK (subprocess launch + auto-quit via env, ~1.1 s)
- `.venv/bin/python -m unittest discover -s tests` → `Ran 86 tests ... OK`
  (83 pre-existing + 3 new; GUI is additive, nothing else affected)
- Token audit: all 15 Design Spec literals + `monospace`/`12.5px` present;
  QSS = 31 non-blank lines ≤ 70.
- `git show --name-only 1aa3175` → exactly the 6 allowed paths.

## Files changed

| Path | Change |
|---|---|
| `.gitignore` | + `.venv/` |
| `gui/__init__.py` | new (empty) |
| `gui/theme.py` | new — QSS + apply() |
| `gui/__main__.py` | new — entry point |
| `gui/app.py` | new — skeleton main() |
| `tests/test_gui_smoke.py` | new — 3 smoke tests |

## Rulings

1. **`__main__` auto-quit channel (brief contradiction).** The brief's literal
   `__main__` snippet calls `main()` with no args (i.e. `auto_quit=0`), yet the
   smoke test must run a subprocess of exactly `.venv/bin/python -m gui` and
   assert returncode 0 within 15 s. Both are unsatisfiable together: with
   `auto_quit=0` the event loop never exits. Smallest fix: `__main__` reads
   `GT7_GUI_AUTO_QUIT_MS` (default `0`) and passes it to `main(auto_quit=...)`.
   Normal `python -m gui` still passes 0, exactly as specified; the test sets
   the env var to `500`.
2. **`#c62828` (error-on-sheet) in QSS.** Qt QSS cannot target text spans inside
   a `QTextBrowser`'s rendered content, so the token is present in the QSS as
   a dedicated comment line documenting that ResultsView applies it inline
   (HTML span color) when rendering errors inside the white sheet. The token
   literal is present so the design can't be silently dropped; Task 6/7 own the
   inline rendering.
3. **Widget objectNames** (`statusLabel`, `dbInfoLabel`, `hintLabel`,
   `warningsLabel`, `computeButton`, `sheetBrowser`) chosen now so the QSS
   selectors are live from the first launch; later tasks just set matching
   `setObjectName()` calls.
4. **Timeout mechanism:** test uses `subprocess.run(..., timeout=15)` (portable;
   macOS has no `timeout` binary by default) — equivalent to the brief's
   "timeout 15" guard.

## Self-review findings

- **Completeness vs brief:** every checkbox covered — venv + install, verify
  step, `.gitignore`, `__init__`, theme (exact tokens), `__main__`, `app.main`,
  smoke test with the three specified assertions + token guard, `unittest
  tests.test_gui_smoke -v` passes, committed with the exact message.
- **YAGNI:** no `request.py`/`service.py`/`form.py`/`components.py`/`results.py`
  created; no launcher script or docs (Task 7); no extra helpers in `app.py`.
- **Test output pristine:** no warnings, no stray Qt stderr; discover run OK.
- **Commit hygiene:** only the 6 task paths committed; unrelated dirty files
  (pycache, .DS_Store, untracked `lib/grip.py`, `tests/test_grip.py`) untouched.

## Issues / concerns

- None blocking. Minor: `git commit` printed the default identity notice
  (auto-configured user name/email); commit metadata is cosmetic only.
- Task 7's `run_gui.sh` should keep `python3 -m venv .venv && .venv/bin/pip
  install ... 'PyQt6>=6.7,<7'` — PyQt6 (not PySide6) was installed and verified.
