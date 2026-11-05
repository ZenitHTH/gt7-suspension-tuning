"""Smoke test (Task 1): theme tokens present + `python -m gui` exits 0 offscreen."""
import os
import subprocess
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtWidgets import QApplication  # noqa: E402

import gui.app  # noqa: E402
import gui.theme  # noqa: E402


def _ensure_app() -> QApplication:
    """Return the running QApplication, creating one if needed."""
    return QApplication.instance() or QApplication([])


class GuiSmokeTest(unittest.TestCase):
    def test_main_defined_in_gui_app(self):
        _ensure_app()
        self.assertEqual(gui.app.main.__module__, 'gui.app')

    def test_theme_qss_uses_design_tokens(self):
        # Theme guard: key Design Spec token literals must survive any edit.
        for token in ('#1b1d23', '#e5484d', 'monospace'):
            self.assertIn(token, gui.theme.QSS, f'missing design token {token!r}')
        qss_lines = [line for line in gui.theme.QSS.splitlines() if line.strip()]
        self.assertLessEqual(len(qss_lines), 70, 'QSS must stay <= 70 lines')

    def test_subprocess_launch_offscreen_exits_zero(self):
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', GT7_GUI_AUTO_QUIT_MS='500')
        proc = subprocess.run(
            [os.path.join(BASE_DIR, '.venv', 'bin', 'python'), '-m', 'gui'],
            cwd=BASE_DIR, env=env, timeout=15, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == '__main__':
    unittest.main()
