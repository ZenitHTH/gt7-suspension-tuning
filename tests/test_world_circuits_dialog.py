"""Headless PyQt6 tests for WorldCircuitsDialog (Task 4)."""
import os
import sys
import unittest
from typing import Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.fonts.warning=false')

from PyQt6.QtWidgets import (  # noqa: E402
    QApplication,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
)

from db.catalog import TrackLayoutEntry  # noqa: E402
from gui.service import TuningService  # noqa: E402
from gui.world_circuits import WorldCircuitsDialog, format_layout_subtitle  # noqa: E402

_APP: Optional[QApplication] = None


def _ensure_app() -> QApplication:
    """Return the running QApplication, creating one if needed."""
    global _APP
    if _APP is None:
        existing = QApplication.instance()
        _APP = existing if isinstance(existing, QApplication) else QApplication([])
    return _APP


def _card_texts(btn: QPushButton) -> Tuple[str, str]:
    """Return (title, subtitle) rendered inside a make_picker_button card."""
    labels = btn.findChildren(QLabel)
    title = labels[0].text() if labels else ''
    subtitle = labels[1].text() if len(labels) > 1 else ''
    return title, subtitle


def _find_buttons(layout: QLayout) -> List[QPushButton]:
    """Collect QPushButtons recursively in layout order."""
    buttons: List[QPushButton] = []
    for idx in range(layout.count()):
        item = layout.itemAt(idx)
        widget = item.widget() if item is not None else None
        if isinstance(widget, QPushButton):
            buttons.append(widget)
            continue
        sub = item.layout() if item is not None else None
        if sub is not None:
            buttons.extend(_find_buttons(sub))
    return buttons


def _cards_by_title(layout: QLayout) -> Dict[str, Tuple[QPushButton, str]]:
    """Map card title -> (button, subtitle) for all card buttons in `layout`."""
    return {
        title: (btn, subtitle)
        for btn in _find_buttons(layout)
        for title, subtitle in (_card_texts(btn),)
    }


def _find_grid(layout: QLayout) -> Optional[QGridLayout]:
    """Find the first QGridLayout inside `layout`."""
    for idx in range(layout.count()):
        sub = layout.itemAt(idx).layout()
        if isinstance(sub, QGridLayout):
            return sub
    return None


def _breadcrumbs(dialog: WorldCircuitsDialog) -> List[str]:
    """Return visible breadcrumb button texts in order."""
    return [b.text() for b in dialog.breadcrumb_bar.findChildren(QPushButton)]


class WorldCircuitsDialogTest(unittest.TestCase):
    def setUp(self) -> None:
        _ensure_app()
        self.service = TuningService()
        self.dialog = WorldCircuitsDialog(self.service)

    def test_format_layout_subtitle_tags_and_metrics(self) -> None:
        rain = TrackLayoutEntry('471', 'Tsukuba Circuit', 'Tsukuba Circuit', 'Japan', 'Asia-Oceania', 2.04, 8, True, False, 'circuit')
        oval = TrackLayoutEntry('4', 'Daytona Tri-Oval', 'Daytona International Speedway', 'United States', 'Americas', 4.02, 4, False, True, 'circuit')
        dirt = TrackLayoutEntry('353', 'Fishermans Ranch', 'Fishermans Ranch', 'United States', 'Americas', 6.89, 40, False, False, 'snow_dirt')
        snow = TrackLayoutEntry('1273', 'Lake Louise Tri-Oval', 'Lake Louise', 'Canada', 'Americas', 3.07, 3, False, False, 'snow_dirt')
        plain = TrackLayoutEntry('2005', 'SUGO International Racing Course', 'SUGO International Racing Course', 'Japan', 'Asia-Oceania', 3.59, 12, False, False, 'circuit')

        self.assertEqual(format_layout_subtitle(rain), '2.04 km · 8 turns · Rain')
        self.assertEqual(format_layout_subtitle(oval), '4.02 km · 4 turns · Oval')
        self.assertEqual(format_layout_subtitle(dirt), '6.89 km · 40 turns · Dirt')
        self.assertEqual(format_layout_subtitle(snow), '3.07 km · 3 turns · Snow')
        self.assertEqual(format_layout_subtitle(plain), '3.59 km · 12 turns')

    def test_three_step_flow_grid_columns_and_accept(self) -> None:
        d = self.dialog
        self.assertIsNone(d.selected_track_id)
        self.assertEqual(d.stack.currentIndex(), 0)
        self.assertFalse(d.back_btn.isEnabled())
        self.assertEqual(_breadcrumbs(d), ['World Circuits'])

        step0 = d.step_container(0)
        self.assertIsInstance(step0.itemAt(0).layout(), QHBoxLayout)
        continents = _find_buttons(step0)
        self.assertEqual([_card_texts(b) for b in continents], [
            ('Americas', '15 circuits · 39 layouts'),
            ('Europe', '16 circuits · 59 layouts'),
            ('Asia-Oceania', '11 circuits · 25 layouts'),
        ])
        self.assertTrue(all(b.objectName() == 'pickerContinentCard' for b in continents))

        continents[0].click()
        self.assertEqual(d.stack.currentIndex(), 1)
        self.assertTrue(d.back_btn.isEnabled())
        self.assertEqual(_breadcrumbs(d), ['World Circuits', 'Americas'])

        step1 = d.step_container(1)
        grid1 = _find_grid(step1)
        self.assertIsNotNone(grid1)
        self.assertEqual(grid1.columnCount(), 3)
        self.assertEqual(d.stack.widget(1).widget().findChildren(QLabel, 'pickerCountryLabel'), [])
        circuits = _cards_by_title(step1)
        self.assertEqual(len(circuits), 15)
        self.assertEqual(circuits['Daytona International Speedway'][1], 'United States · 2 layouts')
        self.assertEqual(circuits['Road Atlanta'][1], 'United States · 1 layout')

        circuits['Daytona International Speedway'][0].click()
        self.assertEqual(d.stack.currentIndex(), 2)
        self.assertEqual(_breadcrumbs(d), ['World Circuits', 'Americas', 'Daytona International Speedway'])

        step2 = d.step_container(2)
        grid2 = _find_grid(step2)
        self.assertIsNotNone(grid2)
        self.assertEqual(grid2.columnCount(), 2)
        layouts = _cards_by_title(step2)
        self.assertEqual(layouts['Daytona Tri-Oval'][1], '4.02 km · 4 turns · Oval')
        self.assertEqual(layouts['Daytona Road Course'][1], '5.73 km · 12 turns')
        self.assertEqual(layouts['Daytona Tri-Oval'][0].accessibleName(),
                         'Daytona Tri-Oval — 4.02 km · 4 turns · Oval')

        layouts['Daytona Tri-Oval'][0].click()
        self.assertEqual(d.selected_track_id, '4')
        self.assertEqual(d.result(), QDialog.DialogCode.Accepted)

    def test_single_layout_circuit_enters_step_two_before_accept(self) -> None:
        d = self.dialog
        _cards_by_title(d.step_container(0))['Asia-Oceania'][0].click()
        circuits = _cards_by_title(d.step_container(1))
        self.assertEqual(circuits['Tsukuba Circuit'][1], 'Japan · 1 layout')

        circuits['Tsukuba Circuit'][0].click()
        self.assertEqual(d.stack.currentIndex(), 2)
        self.assertIsNone(d.selected_track_id)
        self.assertNotEqual(d.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(_breadcrumbs(d), ['World Circuits', 'Asia-Oceania', 'Tsukuba Circuit'])

        layouts = _cards_by_title(d.step_container(2))
        self.assertEqual(list(layouts.keys()), ['Tsukuba Circuit'])
        self.assertEqual(layouts['Tsukuba Circuit'][1], '2.04 km · 8 turns · Rain')
        layouts['Tsukuba Circuit'][0].click()
        self.assertEqual(d.selected_track_id, '471')
        self.assertEqual(d.result(), QDialog.DialogCode.Accepted)

    def test_search_empty_state_clear_restores_step_and_accept_from_search(self) -> None:
        d = self.dialog
        _cards_by_title(d.step_container(0))['Europe'][0].click()
        _cards_by_title(d.step_container(1))['Circuit de Spa-Francorchamps'][0].click()
        self.assertEqual(d.stack.currentIndex(), 2)

        d.search_edit.setText('zzzz_nonexistent')
        self.assertEqual(d.stack.currentIndex(), 3)
        self.assertTrue(d.back_btn.isEnabled())
        empty_labels = [
            w.text() for w in d.stack.widget(3).widget().findChildren(QLabel, 'pickerEmptyLabel')
        ]
        self.assertEqual(empty_labels, ['No matching tracks found'])

        d.search_edit.setText('')
        self.assertEqual(d.stack.currentIndex(), 2)
        self.assertEqual(_breadcrumbs(d), ['World Circuits', 'Europe', 'Circuit de Spa-Francorchamps'])

        d.search_edit.setText('lake louise')
        self.assertEqual(d.stack.currentIndex(), 3)
        d.back_btn.click()
        self.assertEqual(d.search_edit.text(), '')
        self.assertEqual(d.stack.currentIndex(), 2)

        d.search_edit.setText('suzuka')
        self.assertEqual(d.stack.currentIndex(), 3)
        search_grid = _find_grid(d.search_results_layout)
        self.assertIsNotNone(search_grid)
        self.assertEqual(search_grid.columnCount(), 2)
        matches = _cards_by_title(d.search_results_layout)
        self.assertEqual(set(matches.keys()), {'Suzuka Circuit', 'Suzuka Circuit East Course'})
        matches['Suzuka Circuit East Course'][0].click()
        self.assertEqual(d.selected_track_id, '442')
        self.assertEqual(d.result(), QDialog.DialogCode.Accepted)

    def test_back_navigation_step2_to_step1_to_step0_and_breadcrumbs(self) -> None:
        d = self.dialog
        _cards_by_title(d.step_container(0))['Asia-Oceania'][0].click()
        _cards_by_title(d.step_container(1))['Suzuka Circuit'][0].click()
        self.assertEqual(d.stack.currentIndex(), 2)
        self.assertEqual(_breadcrumbs(d), ['World Circuits', 'Asia-Oceania', 'Suzuka Circuit'])

        d.back_btn.click()
        self.assertEqual(d.stack.currentIndex(), 1)
        self.assertTrue(d.back_btn.isEnabled())
        self.assertEqual(_breadcrumbs(d), ['World Circuits', 'Asia-Oceania'])

        d.back_btn.click()
        self.assertEqual(d.stack.currentIndex(), 0)
        self.assertFalse(d.back_btn.isEnabled())
        self.assertEqual(_breadcrumbs(d), ['World Circuits'])

        _cards_by_title(d.step_container(0))['Europe'][0].click()
        _cards_by_title(d.step_container(1))['Nurburgring'][0].click()
        d.breadcrumb_bar.findChildren(QPushButton)[1].click()
        self.assertEqual(d.stack.currentIndex(), 1)
        self.assertEqual(_breadcrumbs(d), ['World Circuits', 'Europe'])

        d.breadcrumb_bar.findChildren(QPushButton)[0].click()
        self.assertEqual(d.stack.currentIndex(), 0)
        self.assertFalse(d.back_btn.isEnabled())
        self.assertEqual(_breadcrumbs(d), ['World Circuits'])

        d.reject()
        self.assertIsNone(d.selected_track_id)


if __name__ == '__main__':
    unittest.main()
