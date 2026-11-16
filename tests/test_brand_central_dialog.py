"""Headless PyQt6 tests for BrandCentralDialog and format_car_subtitle (Task 4)."""
import os
import sys
import unittest
from typing import List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.fonts.warning=false')

from PyQt6.QtWidgets import (  # noqa: E402
    QApplication,
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
)

from db.catalog import CarEntry  # noqa: E402
from gui.brand_central import BrandCentralDialog, format_car_subtitle  # noqa: E402
from gui.service import TuningService  # noqa: E402

_APP: Optional[QApplication] = None


def _ensure_app() -> QApplication:
    """Return the running QApplication, creating one if needed."""
    global _APP
    if _APP is None:
        existing = QApplication.instance()
        _APP = existing if isinstance(existing, QApplication) else QApplication([])
    return _APP


def _label_text(btn: QPushButton, object_name: str) -> str:
    """Read text of child QLabel matching `object_name` inside a picker button."""
    lbl = btn.findChild(QLabel, object_name)
    return lbl.text() if lbl is not None else ''


def _step_buttons(dialog: BrandCentralDialog, step_index: int) -> List[QPushButton]:
    """Return all picker card buttons rendered on stack page `step_index`."""
    return dialog.stack.widget(step_index).findChildren(QPushButton)


def _find_button(buttons: List[QPushButton], prefix: str) -> QPushButton:
    """Find first picker button whose title equals or starts with `prefix`."""
    for btn in buttons:
        title = _label_text(btn, 'pickerCardTitle')
        if title == prefix or title.startswith(prefix):
            return btn
    raise AssertionError(f'No picker button matching {prefix!r}')


def _crumbs(dialog: BrandCentralDialog) -> List[str]:
    """Return current breadcrumb labels in display order."""
    return [btn.text() for btn in dialog.breadcrumb_bar.findChildren(QPushButton)]


class BrandCentralDialogTest(unittest.TestCase):
    """Test suite for BrandCentralDialog navigation, layout, and formatting."""

    def setUp(self) -> None:
        _ensure_app()
        self.service = TuningService()
        self.dialog = BrandCentralDialog(self.service)

    def test_step0_renders_three_continents_and_counts(self) -> None:
        d = self.dialog
        self.assertEqual(d.stack.currentIndex(), 0)
        self.assertFalse(d.back_btn.isEnabled())
        self.assertIsNone(d.selected_car_id)
        self.assertEqual(_crumbs(d), ['Brand Central'])
        btns = _step_buttons(d, 0)
        self.assertEqual([_label_text(b, 'pickerCardTitle') for b in btns],
                         ['Americas', 'Europe', 'Asia-Pacific'])
        counts = self.service.brand_central_continents()
        for btn, cont in zip(btns, ('Americas', 'Europe', 'Asia-Pacific')):
            b_n, c_n = counts[cont]
            self.assertEqual(_label_text(btn, 'pickerCardSubtitle'), f'{b_n} brands · {c_n} cars')
            self.assertTrue(btn.icon().isNull())

    def test_step1_asia_pacific_country_rows_and_no_partners(self) -> None:
        d = self.dialog
        _find_button(_step_buttons(d, 0), 'Asia-Pacific').click()
        self.assertEqual(d.stack.currentIndex(), 1)
        self.assertTrue(d.back_btn.isEnabled())
        country_lbls = d.stack.widget(1).findChildren(QLabel, 'pickerCountryLabel')
        self.assertEqual([lbl.text() for lbl in country_lbls], ['Japan', 'Korea', 'China'])
        self.assertTrue(all(lbl.minimumWidth() == 120 and lbl.maximumWidth() == 120 for lbl in country_lbls))
        self.assertTrue(all(g.columnCount() == 3 for g in d.stack.widget(1).findChildren(QGridLayout)))
        titles = [_label_text(b, 'pickerCardTitle') for b in _step_buttons(d, 1)]
        self.assertIn('Gran Turismo (8)', titles)
        for partner in ('Fanatec', 'Brembo', 'BBS', 'Sony AI'):
            self.assertFalse(any(t.startswith(partner) for t in titles))

    def test_step2_toyota_car_grid_and_accept_sets_selected_car_id(self) -> None:
        d = self.dialog
        _find_button(_step_buttons(d, 0), 'Asia-Pacific').click()
        _find_button(_step_buttons(d, 1), 'Toyota (').click()
        self.assertEqual(d.stack.currentIndex(), 2)
        grids = d.stack.widget(2).findChildren(QGridLayout)
        self.assertEqual(len(grids), 1)
        self.assertEqual(grids[0].columnCount(), 3)
        mr2 = [c for c in self.service.cars_in_brand('Asia-Pacific', 'Toyota') if c.id == '207'][0]
        mr2_btn = _find_button(_step_buttons(d, 2), mr2.short_name)
        expected_sub = format_car_subtitle(mr2)
        self.assertEqual(_label_text(mr2_btn, 'pickerCardSubtitle'), expected_sub)
        self.assertEqual(mr2_btn.accessibleName(), f'{mr2.short_name} — {expected_sub}')
        self.assertTrue(mr2_btn.icon().isNull())
        mr2_btn.click()
        self.assertEqual(d.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(d.selected_car_id, '207')

    def test_citroen_merge_and_bugatti_under_europe_france(self) -> None:
        _find_button(_step_buttons(self.dialog, 0), 'Europe').click()
        titles = [_label_text(b, 'pickerCardTitle') for b in _step_buttons(self.dialog, 1)]
        self.assertIn('Citroën (6)', titles)
        self.assertIn('Bugatti (5)', titles)
        self.assertFalse(any(t.startswith('Citroen (') for t in titles))

    def test_format_car_subtitle_with_and_without_stock_pp(self) -> None:
        with_pp = CarEntry('207', "MR2 GT-S '97", "Toyota MR2 GT-S '97", 'Toyota',
                           'Japan', 'Asia-Pacific', 'N', 'MR', 241, 1270, 484.17)
        self.assertEqual(format_car_subtitle(with_pp), 'N · MR · 241 hp · 1270 kg · PP 484.17')
        bmw_3604 = [c for c in self.service.cars_in_brand('Europe', 'BMW') if c.id == '3604'][0]
        sub = format_car_subtitle(bmw_3604)
        self.assertNotIn('PP', sub)
        self.assertNotIn('None', sub)
        self.assertEqual(sub, 'Gr.1 · MR · 671 hp · 1030 kg')
        _find_button(_step_buttons(self.dialog, 0), 'Europe').click()
        _find_button(_step_buttons(self.dialog, 1), 'BMW (').click()
        btn = _find_button(_step_buttons(self.dialog, 2), bmw_3604.short_name)
        self.assertEqual(_label_text(btn, 'pickerCardSubtitle'), sub)

    def test_search_empty_state_restore_and_accept(self) -> None:
        d = self.dialog
        _find_button(_step_buttons(d, 0), 'Americas').click()
        d.search_edit.setText('zzzz_nonexistent')
        self.assertEqual(d.stack.currentIndex(), 3)
        empty = d.stack.widget(3).findChild(QLabel, 'pickerEmptyLabel')
        self.assertIsNotNone(empty)
        self.assertEqual(empty.text(), 'No matching cars found')
        d.search_edit.setText('')
        self.assertEqual(d.stack.currentIndex(), 1)
        d.search_edit.setText('mr2 gt-s')
        grids = d.stack.widget(3).findChildren(QGridLayout)
        self.assertEqual(len(grids), 1)
        self.assertEqual(grids[0].columnCount(), 3)
        _find_button(_step_buttons(d, 3), "MR2 GT-S '97").click()
        self.assertEqual(d.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(d.selected_car_id, '207')

    def test_back_navigation_step2_to_step1_to_step0(self) -> None:
        d = self.dialog
        _find_button(_step_buttons(d, 0), 'Asia-Pacific').click()
        _find_button(_step_buttons(d, 1), 'Toyota (').click()
        self.assertEqual(d.stack.currentIndex(), 2)
        self.assertEqual(_crumbs(d), ['Brand Central', 'Asia-Pacific', 'Toyota'])
        d.search_edit.setText('supra')
        self.assertEqual(d.stack.currentIndex(), 3)
        d.back_btn.click()
        self.assertEqual(d.stack.currentIndex(), 2)
        d.back_btn.click()
        self.assertEqual(d.stack.currentIndex(), 1)
        self.assertEqual(_crumbs(d), ['Brand Central', 'Asia-Pacific'])
        d.back_btn.click()
        self.assertEqual(d.stack.currentIndex(), 0)
        self.assertFalse(d.back_btn.isEnabled())
        self.assertEqual(_crumbs(d), ['Brand Central'])

    def test_breadcrumb_navigation_and_reject(self) -> None:
        d = self.dialog
        _find_button(_step_buttons(d, 0), 'Asia-Pacific').click()
        _find_button(_step_buttons(d, 1), 'Toyota (').click()
        d.breadcrumb_bar.findChildren(QPushButton)[1].click()
        self.assertEqual(d.stack.currentIndex(), 1)
        self.assertEqual(_crumbs(d), ['Brand Central', 'Asia-Pacific'])
        d.breadcrumb_bar.findChildren(QPushButton)[0].click()
        self.assertEqual(d.stack.currentIndex(), 0)
        self.assertEqual(_crumbs(d), ['Brand Central'])
        d.reject()
        self.assertEqual(d.result(), QDialog.DialogCode.Rejected)
        self.assertIsNone(d.selected_car_id)


if __name__ == '__main__':
    unittest.main()
