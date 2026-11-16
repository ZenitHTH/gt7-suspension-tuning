"""Headless PyQt6 tests for StepPickerDialog shell and helpers (Task 3)."""
import os
import sys
import unittest
from typing import List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.fonts.warning=false')

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.brand_central import BrandCentralDialog  # noqa: E402
from gui.picker_dialog import (  # noqa: E402
    StepPickerDialog,
    clear_layout,
    make_picker_button,
    picker_stylesheet,
)
from gui.service import TuningService  # noqa: E402
from gui.world_circuits import WorldCircuitsDialog  # noqa: E402

_APP: Optional[QApplication] = None


def _ensure_app() -> QApplication:
    """Return the running QApplication, creating one if needed."""
    global _APP
    if _APP is None:
        existing = QApplication.instance()
        _APP = existing if isinstance(existing, QApplication) else QApplication([])
    return _APP


def _pump(app: QApplication) -> None:
    """Process pending Qt layout events so widget geometries settle."""
    for _ in range(3):
        app.processEvents()


def _find_card(page: QWidget, prefix: str) -> QPushButton:
    """Find first picker button inside `page` whose title equals or starts with `prefix`."""
    for btn in page.findChildren(QPushButton):
        lbl = btn.findChild(QLabel, 'pickerCardTitle')
        if lbl is not None and (lbl.text() == prefix or lbl.text().startswith(prefix)):
            return btn
    raise AssertionError(f'No card matching {prefix!r}')


def _assert_no_clipped_cards(case: unittest.TestCase, page: QWidget) -> int:
    """Assert every visible card button and inner label fits its heightForWidth."""
    buttons = [b for b in page.findChildren(QPushButton) if b.isVisible()]
    case.assertGreater(len(buttons), 0)
    for btn in buttons:
        lbl = btn.findChild(QLabel, 'pickerCardTitle')
        title = lbl.text() if lbl is not None else btn.objectName()
        case.assertGreaterEqual(btn.height(), btn.heightForWidth(btn.width()), title)
        for child_lbl in [c for c in btn.findChildren(QLabel) if c.isVisible()]:
            case.assertGreaterEqual(
                child_lbl.height(), child_lbl.heightForWidth(child_lbl.width()), child_lbl.text()
            )
    return len(buttons)


class _DummyPickerDialog(StepPickerDialog):
    """Minimal StepPickerDialog subclass for shell navigation tests."""

    def __init__(self) -> None:
        self.search_queries: List[str] = []
        super().__init__('Dummy Picker', 'Root', 'Search items...')

    def _on_search_changed(self, query: str) -> None:
        self.search_queries.append(query)
        clear_layout(self.search_results_layout)
        self.search_results_layout.addWidget(QLabel(f'Result: {query}'))


class StepPickerDialogTest(unittest.TestCase):
    def setUp(self) -> None:
        _ensure_app()
        self.dialog = _DummyPickerDialog()

    def test_step_navigation_and_breadcrumbs(self) -> None:
        d = self.dialog
        self.assertEqual(d.stack.currentIndex(), 0)
        self.assertFalse(d.back_btn.isEnabled())
        d.show_step(1)
        self.assertEqual(d.stack.currentIndex(), 1)
        self.assertTrue(d.back_btn.isEnabled())
        d.show_step(2)
        d.set_breadcrumbs([
            ('Root', lambda: d.show_step(0)),
            ('Region', lambda: d.show_step(1)),
            ('Brand', lambda: d.show_step(2)),
        ])
        crumbs = d.breadcrumb_bar.findChildren(QPushButton)
        self.assertEqual([b.text() for b in crumbs], ['Root', 'Region', 'Brand'])
        crumbs[0].click()
        self.assertEqual(d.stack.currentIndex(), 0)
        self.assertFalse(d.back_btn.isEnabled())

    def test_search_and_back_navigation_recovery(self) -> None:
        d = self.dialog
        d.show_step(1)
        d.search_edit.setText('test')
        self.assertEqual(d.stack.currentIndex(), 3)
        self.assertTrue(d.back_btn.isEnabled())
        self.assertEqual(d.search_queries, ['test'])
        d.back_btn.click()
        self.assertEqual(d.search_edit.text(), '')
        self.assertEqual(d.stack.currentIndex(), 1)
        self.assertTrue(d.back_btn.isEnabled())
        d.search_edit.setText('again')
        self.assertEqual(d.stack.currentIndex(), 3)
        d.search_edit.setText('')
        self.assertEqual(d.stack.currentIndex(), 1)

    def test_search_from_step_zero_restores_step_zero(self) -> None:
        d = self.dialog
        self.assertFalse(d.back_btn.isEnabled())
        d.search_edit.setText('civic')
        self.assertEqual(d.stack.currentIndex(), 3)
        self.assertTrue(d.back_btn.isEnabled())
        d.back_btn.click()
        self.assertEqual(d.stack.currentIndex(), 0)
        self.assertFalse(d.back_btn.isEnabled())

    def test_breadcrumb_clears_active_search_and_back_steps_down(self) -> None:
        d = self.dialog
        d.show_step(2)
        d.set_breadcrumbs([('Root', lambda: d.show_step(0)), ('End', lambda: d.show_step(2))])
        d.search_edit.setText('nsx')
        self.assertEqual(d.stack.currentIndex(), 3)
        d.breadcrumb_bar.findChildren(QPushButton)[0].click()
        self.assertEqual(d.stack.currentIndex(), 0)
        self.assertEqual(d.search_edit.text(), '')
        d.show_step(2)
        d.back_btn.click()
        self.assertEqual(d.stack.currentIndex(), 1)
        d.back_btn.click()
        self.assertEqual(d.stack.currentIndex(), 0)

    def test_make_picker_button_labels_and_clicks(self) -> None:
        clicked: List[str] = []
        btn = make_picker_button('Toyota', '12 cars')
        self.assertEqual(btn.objectName(), 'pickerCard')
        self.assertIsInstance(btn, QPushButton)
        labels = btn.findChildren(QLabel)
        self.assertEqual([lbl.text() for lbl in labels], ['Toyota', '12 cars'])
        for lbl in labels:
            self.assertTrue(lbl.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        btn.clicked.connect(lambda: clicked.append('yes'))
        btn.click()
        self.assertEqual(clicked, ['yes'])
        plain = make_picker_button('Americas', object_name='pickerContinentCard')
        self.assertEqual(plain.objectName(), 'pickerContinentCard')
        self.assertEqual([lbl.text() for lbl in plain.findChildren(QLabel)], ['Americas'])

    def test_clear_layout_removes_nested_widgets_and_layouts(self) -> None:
        host = QWidget()
        outer = QVBoxLayout(host)
        sub = QHBoxLayout()
        sub.addWidget(make_picker_button('Alpha'))
        outer.addLayout(sub)
        outer.addWidget(QLabel('Footer'))
        outer.addStretch(1)
        clear_layout(outer)
        self.assertEqual(outer.count(), 0)
        self.assertEqual(host.findChildren(QPushButton), [])
        self.assertEqual(host.findChildren(QLabel), [])

    def test_step_containers_distinct_and_palette_tokens_present(self) -> None:
        d = self.dialog
        containers = [d.step_container(i) for i in range(4)]
        self.assertEqual(len({id(c) for c in containers}), 4)
        self.assertIs(containers[3], d.search_results_layout)
        qss = picker_stylesheet()
        for token in ('#1b1d23', '#23262e', '#14161a', '#3a3f4d', '#e5484d', '#ffffff', '#9aa3b5'):
            self.assertIn(token, qss)


class PickerLayoutRegressionTest(unittest.TestCase):
    """Reproduction tests for wrapped card clipping and long breadcrumb overflow."""

    def test_brand_central_single_char_search_no_clipped_cards(self) -> None:
        app = _ensure_app()
        d = BrandCentralDialog(TuningService())
        d.resize(780, 560)
        d.show()
        _pump(app)
        d.search_edit.setText('a')
        _pump(app)
        count = _assert_no_clipped_cards(self, d.stack.widget(3))
        self.assertGreaterEqual(count, 500)
        d.close()

    def test_brand_central_min_size_europe_and_genesis_no_clipping(self) -> None:
        app = _ensure_app()
        d = BrandCentralDialog(TuningService())
        d.resize(620, 440)
        d.show()
        _pump(app)
        _find_card(d.stack.widget(0), 'Europe').click()
        _pump(app)
        self.assertGreater(_assert_no_clipped_cards(self, d.stack.widget(1)), 0)
        d.back_btn.click()
        _pump(app)
        _find_card(d.stack.widget(0), 'Asia-Pacific').click()
        _pump(app)
        _find_card(d.stack.widget(1), 'Genesis (').click()
        _pump(app)
        self.assertGreater(_assert_no_clipped_cards(self, d.stack.widget(2)), 0)
        _find_card(d.stack.widget(2), 'Genesis X Gran Racer Vision Gran Turismo Concept')
        d.close()

    def test_world_circuits_long_breadcrumb_preserves_min_width(self) -> None:
        app = _ensure_app()
        d = WorldCircuitsDialog(TuningService())
        d.show()
        _pump(app)
        _find_card(d.stack.widget(0), 'Asia-Oceania').click()
        _pump(app)
        _find_card(d.stack.widget(1), 'SUGO International Racing Course').click()
        d.resize(620, 440)
        _pump(app)
        self.assertLessEqual(d.minimumSizeHint().width(), 620)
        self.assertGreaterEqual(d.search_edit.width(), 220)
        self.assertGreaterEqual(d.back_btn.width(), d.back_btn.minimumSizeHint().width())
        crumbs = d.breadcrumb_bar.findChildren(QPushButton)
        self.assertEqual([b.text() for b in crumbs], ['World Circuits', 'Asia-Oceania', 'SUGO International Racing Course'])
        self.assertEqual(crumbs[-1].toolTip(), 'SUGO International Racing Course')
        d.close()


if __name__ == '__main__':
    unittest.main()
