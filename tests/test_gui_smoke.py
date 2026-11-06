"""Smoke test (Task 1): theme tokens present + `python -m gui` exits 0 offscreen."""
import os
import subprocess
import sys
import unittest
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtWidgets import QApplication  # noqa: E402

import gui.app  # noqa: E402
import gui.theme  # noqa: E402


def _ensure_app() -> QApplication:
    """Return the running QApplication, creating one if needed."""
    return QApplication.instance() or QApplication([])


def _venv_python() -> Optional[str]:
    """Project venv python, per platform; None when the venv is absent
    (e.g. running from a fresh checkout / git archive)."""
    rel = os.path.join('.venv', 'Scripts', 'python.exe') if os.name == 'nt' \
        else os.path.join('.venv', 'bin', 'python')
    path = os.path.join(BASE_DIR, rel)
    return path if os.path.exists(path) else None


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

    def test_theme_sets_noto_sans_font_and_white_text(self):
        # Regression: theme must use the bundled Noto Sans family (with
        # fallback stack) and pure white text on the dark chrome.
        app = _ensure_app()
        gui.theme.apply(app)
        self.assertIn('Noto Sans', app.font().families())
        self.assertNotIn('#e6e8ee', gui.theme.QSS,
                         'dark-chrome text must be pure white (#ffffff)')

    @unittest.skipUnless(_venv_python(), 'project venv not built (run the launcher first)')
    def test_subprocess_launch_offscreen_exits_zero(self):
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', GT7_GUI_AUTO_QUIT_MS='500')
        proc = subprocess.run(
            [_venv_python(), '-m', 'gui'],
            cwd=BASE_DIR, env=env, timeout=15, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == '__main__':
    unittest.main()
