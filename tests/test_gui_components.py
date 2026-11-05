"""Tests for gui.components (Task 4): RangePair (0,0)→None rule."""
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.fonts.warning=false')

from PyQt6.QtWidgets import QApplication, QDoubleSpinBox, QSpinBox  # noqa: E402

from gui.components import RangePair  # noqa: E402


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


class RangePairTest(unittest.TestCase):
    def setUp(self):
        _ensure_app()

    def test_range_pair_rule(self):
        pair = RangePair('X')
        self.assertIsNone(pair.value(), 'default pair must be unset (None)')

        pair.set_value((50, 200))
        self.assertEqual(pair.value(), (50, 200))

        pair.set_value(None)
        self.assertIsNone(pair.value(), 'None must reset both spins to 0')

    def test_int_kind_uses_int_spins(self):
        pair = RangePair('DF', kind='int', max_v=1000)
        self.assertIsInstance(pair.min_spin, QSpinBox)
        self.assertIsInstance(pair.max_spin, QSpinBox)
        self.assertEqual(pair.min_spin.maximum(), 1000)
        pair.set_value((50, 200))
        self.assertEqual(pair.value(), (50, 200))
        self.assertIsInstance(pair.value()[0], int)

    def test_float_kind_exact_tuple(self):
        pair = RangePair('FN', kind='float', max_v=10.0)
        self.assertIsInstance(pair.min_spin, QDoubleSpinBox)
        self.assertEqual(pair.min_spin.decimals(), 2)
        pair.set_value((1.5, 3.5))
        self.assertEqual(pair.value(), (1.5, 3.5))

    def test_zero_min_only_is_not_none(self):
        # Rule is both-zero → None; a single 0 is a legitimate range.
        pair = RangePair('X')
        pair.min_spin.setValue(0)
        pair.max_spin.setValue(200)
        self.assertEqual(pair.value(), (0, 200))


if __name__ == '__main__':
    unittest.main()
