"""Tests for gui.app (Task 6): MainWindow wiring + end-to-end compute flow."""
import os
import sys
import time
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.fonts.warning=false')

from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui.app import MainWindow  # noqa: E402
from gui.request import GuiResult  # noqa: E402
from gui.service import TuningService  # noqa: E402

# Deadline for the end-to-end solve: the MR2 balanced solver is heavy
# (tens of seconds) but must never hang the test process.
SOLVE_DEADLINE_S = 60.0

_APP: QApplication | None = None  # keep a reference so the app isn't GC'd


def _ensure_app() -> QApplication:
    """Return the running QApplication, creating one if needed.

    A bare QCoreApplication left by another test module (test_gui_service
    WorkerTests) is not a QApplication: QApplication.instance() still
    returns it, so fall through and build a real QApplication.
    """
    global _APP
    if _APP is None:
        existing = QApplication.instance()
        _APP = existing if isinstance(existing, QApplication) else QApplication([])
    return _APP


def _fill_mr2_tutorial(win: MainWindow) -> None:
    """Select car 207 (MR2 GT-S '97) and set the tutorial/MR2 fixture values."""
    form = win.form
    idx = form.car_combo.findData('207')
    assert idx >= 0, 'car 207 not in car_combo'
    form.car_combo.setCurrentIndex(idx)
    form.df_f.set_value((50, 200))
    form.df_r.set_value((120, 310))
    form.hf.set_value((90, 160))
    form.hr.set_value((90, 160))
    form.fn_f.set_value((1.5, 3.5))
    form.fn_r.set_value((1.5, 3.5))
    form.g60_spin.setValue(1.04)
    form.g120_spin.setValue(1.19)
    form.g240_spin.setValue(1.38)
    form.gref_f_spin.setValue(200)
    form.gref_r_spin.setValue(310)
    solve_idx = form.solve_combo.findData('balanced')
    assert solve_idx >= 0, 'balanced not in solve_combo'
    form.solve_combo.setCurrentIndex(solve_idx)
    form.power_use_db.setChecked(False)
    form.power_spin.setValue(630)
    form.mass_use_db.setChecked(False)
    form.mass_spin.setValue(1289)
    form.balance_use_db.setChecked(False)
    form.bal_f_spin.setValue(42)
    form.bal_r_spin.setValue(58)


class MainWindowTest(unittest.TestCase):
    def setUp(self):
        _ensure_app()
        self.win = MainWindow(TuningService())

    def test_window_builds(self):
        """MainWindow exposes form/results/compute_btn (Task 6 step 2a)."""
        self.assertIsNotNone(self.win.form)
        self.assertIsNotNone(self.win.results)
        self.assertIsNotNone(self.win.compute_btn)
        self.assertEqual(self.win.compute_btn.text(), 'Compute Setup')
        self.assertTrue(self.win.compute_btn.isEnabled())

    def test_compute_end_to_end(self):
        """Click Compute → solver runs off-thread → sheet renders (slow)."""
        win = self.win
        _fill_mr2_tutorial(win)
        self.assertFalse(win.form.validate(), 'form must validate clean for MR2')

        t0 = time.monotonic()
        win._on_compute()
        # UI stays responsive: spin the event loop (worker runs on QThread)
        # until the compute button is re-enabled or the deadline passes.
        while not win.compute_btn.isEnabled():
            if time.monotonic() - t0 > SOLVE_DEADLINE_S:
                self.fail(
                    f'compute did not finish within {SOLVE_DEADLINE_S:.0f}s — '
                    'the solver is likely running on the UI thread')
            QApplication.instance().processEvents()
            time.sleep(0.05)
        elapsed = time.monotonic() - t0

        text = win.results.browser.toPlainText()
        self.assertIn('MR2', text)
        self.assertIn('Body Height', text)
        self.assertIn('QUICK-TRIM', text.upper())  # Quick-Trim section present
        self.assertNotIn('not found', win.results.warnings_label.text())
        print(f'  [e2e] solve finished in {elapsed:.1f}s')

    def test_error_path(self):
        """Error result renders 'not found' in the sheet browser."""
        win = self.win
        win._on_finished(GuiResult(error='Car not found: nope'))
        self.assertIn('not found', win.results.browser.toPlainText())
        self.assertTrue(win.compute_btn.isEnabled())

    def test_close_during_solve_stops_thread_cleanly(self):
        """Regression (final review): closing the window while a solve runs
        used to destroy the worker QThread while it was still running →
        qFatal 'QThread: Destroyed while thread is still running' +
        SIGABRT. closeEvent now polls (bounded) until the thread is
        provably stopped; the test process surviving is itself the
        assertion, plus the explicit state asserts below."""
        win = self.win
        _fill_mr2_tutorial(win)  # form validates clean (as in the e2e test)
        service = win.service
        ran = []

        def slow_compute(req):
            ran.append('compute')
            time.sleep(0.4)
            return GuiResult(error='slow compute (test stub)')
        original = service.compute
        service.compute = slow_compute
        try:
            win._on_compute()
            thread = win._thread
            self.assertIsNotNone(thread)
            # Closing *now* is the "during solve" moment: the worker
            # thread is alive and the solve is not finished. Do not pump
            # events first — a pump (in this offscreen environment) would
            # run the stub solve to completion and tear the thread down,
            # leaving no mid-solve close to exercise.
            t0 = time.monotonic()
            win.close()  # closeEvent: bounded quit+poll on the solve thread
            waited = time.monotonic() - t0
            # closeEvent absorbed the 0.4 s stub solve (inside its ~1.5 s
            # bound) → close accepted, window gone. waited >= 0.25 guards
            # against a vacuous instant-accept.
            self.assertGreaterEqual(waited, 0.25)
            self.assertLess(waited, 2.0)
            self.assertFalse(win.isVisible())
            # The worker really ran the stub, and the thread fully stopped:
            self.assertIn('compute', ran)
            self.assertFalse(win._in_flight)
            # Thread state, tolerating an already deleteLater'd wrapper.
            try:
                self.assertFalse(thread.isRunning(), 'solve thread still running')
            except RuntimeError:
                pass  # C++ thread object already deleted → stopped

            # Re-entrancy: a second close must accept immediately (no hang).
            t1 = time.monotonic()
            win.close()
            self.assertLess(time.monotonic() - t1, 0.5)
            self.assertFalse(win.isVisible())
        finally:
            service.compute = original


if __name__ == '__main__':
    unittest.main()
