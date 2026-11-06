# Task 6 Report: `ResultsView` + `MainWindow` wiring (end-to-end)

## What I implemented

### `gui/results.py` (new)
`ResultsView(QWidget)` with the brief's exact interface:
- `warnings_label: QLabel` — objectName `warningsLabel` (theme: amber bold), `setWordWrap(True)`, hidden by default; shown with `⚠`-prefixed joined warnings when a result carries any.
- `browser: QTextBrowser` — objectName `sheetBrowser` (theme: white `#ffffff` bg, `#16181d` text, monospace 12.5px, 16px padding).
- `copy_btn: QPushButton` ("Copy sheet") — copies the raw (unescaped) sheet text via `QApplication.clipboard().setText(...)`; disabled while an error is shown.
- `show_result(r: GuiResult)` — error results route to `show_error(r.error)`; otherwise sheet rendered as `'<pre style="font-family: monospace; margin: 0;">' + html.escape(sheet) + '</pre>'` (QSS font-size 12.5px still applies since `<pre>` doesn't override it).
- `show_error(msg)` — cleared sheet; error rendered **inside the white browser** as `<span style="color:#c62828; font-weight: bold">` (error-on-sheet token applied inline in the HTML, since QSS cannot style QTextBrowser HTML spans); copy disabled.
- `clear()` — empties browser, hides warnings, re-enables copy.

### `gui/app.py` (rewritten; `__main__.py` untouched)
`MainWindow(QMainWindow)` per the brief:
- Layout: central `QWidget` with `QVBoxLayout`; `QSplitter(Horizontal)` — left `QScrollArea` (resizable, no frame) wrapping `SetupForm`, right `ResultsView`; splitter sizes [400, 1000] with stretch factor 1 only on the sheet side (design: sheet pane dominates). Bottom bar: `compute_btn = QPushButton("Compute Setup")` (objectName `computeButton`) + `status: QLabel` (objectName `statusLabel`, ok/warn/error properties as in the form's status idiom).
- `__init__(self, service: Optional[TuningService] = None)` — constructs a `TuningService` when `None`.
- `_on_compute` — `errors = form.validate()`; on errors, status shows the first error (kind `error`) and stops. Else `results.clear()`, button disabled + text `Computing…`, status `Computing…`; `worker = Worker(service, form.collect())`; `thread = QThread(self)`; `thread.started → worker.run`; `worker.finished → self._on_finished`; `worker.failed → self._on_failed`; `thread.finished → thread.deleteLater`; `worker.moveToThread(thread)`; `thread.start()`.
- `_on_finished(r)` — `thread.quit()`; `results.show_result(r)`; button re-enabled + text restored; status `"{n} warning(s)"` (kind `warn`) or `OK` (kind `ok`); on `r.error`, status = error (kind `error`).
- `_on_failed(msg)` — same teardown + `results.show_error(msg)` + status error.
- `main(auto_quit: int = 0) -> int` — `QApplication([])`, `gui.theme.apply(app)`, `MainWindow()`, `resize(1400, 900)`, `show()`, `QTimer.singleShot(auto_quit, app.quit)` when `auto_quit > 0`, `return app.exec()`. `gui/__main__.py` (GT7_GUI_AUTO_QUIT_MS feeder) unchanged and still works (smoke subprocess exits 0).

### `tests/test_gui_app.py` (new) — 3 tests
- `test_window_builds` — `MainWindow(TuningService())` constructs; `win.form`, `win.results`, `win.compute_btn` exist; button text `Compute Setup` and enabled.
- `test_compute_end_to_end` — selects car 207 via `car_combo.findData`, sets the MR2 tutorial values (ranges 50-200/120-310/90-160/90-160/1.5-3.5, G 1.04/1.19/1.38, ref 200/310, solve `balanced`, power 630, mass 1289, balance 42/58); asserts `form.validate()` is clean; calls `win._on_compute()`; spins `QApplication.instance().processEvents()` + 50 ms sleep in a loop (60 s deadline, `self.fail` with a clear message on overrun) until `compute_btn.isEnabled()`; asserts `browser.toPlainText()` contains `MR2`, `Body Height`, the Quick-Trim section (case-insensitive `QUICK-TRIM` — see Rulings), and warnings label has no `not found`. Prints the solve elapsed time.
- `test_error_path` — `win._on_finished(GuiResult(error='Car not found: nope'))` directly; asserts `not found` in `browser.toPlainText()` (plus button re-enabled).

App fixture: copied the `_ensure_app`/`_APP` guard from `tests/test_gui_form.py` (a leftover `QCoreApplication` from `test_gui_service.WorkerTests` makes bare `QApplication.instance() or ...` unreliable); `QT_QPA_PLATFORM=offscreen` set before any Qt import.

## What I tested

Commands (repo root, `.venv/bin/python`):

1. Fast tests: `unittest tests.test_gui_app.MainWindowTest.test_window_builds ...test_error_path -v` → `Ran 2 tests in 0.617s OK`.
2. End-to-end: `unittest tests.test_gui_app.MainWindowTest.test_compute_end_to_end -v` → `Ran 1 test in 0.465s OK`, `[e2e] solve finished in 0.1s`.
   - Note: the solver is **much faster than the brief's "tens of seconds" estimate on this machine** — a direct `TuningService().compute(MR2 fixture)` call returns in <0.1 s (`ok: True, warnings: [], sheet 5060 chars`). The 60 s deadline loop is retained as the anti-hang guard per the brief.
3. Module: `unittest tests.test_gui_app -v` → `Ran 3 tests in 0.490s OK`.
4. Full GUI set (twice): `unittest tests.test_gui_smoke tests.test_gui_request tests.test_gui_service tests.test_gui_components tests.test_gui_form tests.test_gui_app` → `Ran 33 tests ... OK` both runs. Includes the smoke test's `python -m gui` subprocess with `GT7_GUI_AUTO_QUIT_MS=500` exiting 0 (the rewritten `MainWindow` boots and auto-quits cleanly).

## Files changed
- `gui/results.py` (new, 102 lines)
- `gui/app.py` (rewritten, 141 lines: 133 ins / 8 del)
- `tests/test_gui_app.py` (new, 117 lines)
- Not touched: `gui/form.py`, `gui/service.py`, `gui/theme.py`, `gui/components.py`, `gui/request.py`, `gui/__main__.py`, all existing tests.

Commit: `ba0b129` — `gui: ResultsView + MainWindow end-to-end wiring` (exactly the 3 files above; unrelated dirty files left alone).

## Rulings and self-review findings
1. **Quick-Trim assertion casing.** The brief's test spec says assert the browser contains `'Quick-Trim'`, but `sheet_formatter.py` renders the section as `QUICK-TRIMS DELTA TABLE (… Section 2.F …)` — title-case `Quick-Trim` does not appear anywhere in the sheet. I assert `'QUICK-TRIM' in text.upper()`, which satisfies the brief's intent (Quick-Trim section rendered) without false failure.
2. **Worker lifetime (kept brief's exact wiring).** Per the brief, the worker is a childless `QObject` moved to a `QThread`; the thread is `deleteLater`'d on `thread.finished`. To prevent a mid-run GC of the worker's Python wrapper (which would delete the C++ object and hang the thread), I hold `self._worker = worker` on `MainWindow` and overwrite it on each compute. The previous worker's wrapper becomes reclaimable only after its thread has terminated (the button is disabled during compute, so a new compute can never race an old thread). Leaf QObjects deleted after their thread finished are safe in practice; the full suite is green with no Qt warnings/crashes. If repeated computes ever show trouble, the hardening step would be `thread.finished.connect(worker.deleteLater)` plus a reference swap.
3. **Error-result status.** The brief specifies status `N warning(s)` / `OK` for `_on_finished`; for the `r.error is not None` branch (which `show_result` routes into `show_error`) I set status to the error text with kind `error` — consistent with the Review Focus "UI shows it red" and with the form's status idiom.
4. **`qt.qpa.fonts` one-line warning** in the combined run's stderr is pre-existing (appears with the Tasks 1–5 modules alone, from `QApplication` creation in modules that don't set `QT_LOGGING_RULES`); not introduced by this task, left alone.
5. e2e test prints one line (`[e2e] solve finished in Xs`) — intentional: the brief asks for the end-to-end timing to be recorded; output otherwise pristine.
6. Verified `form.validate()` is clean for the MR2 fixture (no "No X range" warnings — all six ranges set; balance 42+58=100; g_forces + g_ref_df + solve consistent) so the e2e sheet arrives with `warnings == []`, matching `test_mr2_compute_ok`.

## Issues / concerns
- None blocking. Only observation: the solver timing estimate in the brief (tens of seconds) doesn't hold on this machine (<0.1 s), so the e2e test's main value today is pinning the off-thread wiring contract rather than exercising a long solve; the deadline guard still covers a regression where the solver runs on the UI thread.
