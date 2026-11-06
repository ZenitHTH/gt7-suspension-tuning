"""Tests for gui.form (Tasks 4-5): SetupForm vehicle/tire/ranges/overrides +
calibration/session/symptoms, collect(), validate()."""
import os
import sys
import unittest
from unittest import mock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.fonts.warning=false')

from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui.form import SetupForm  # noqa: E402
from gui.service import TuningService  # noqa: E402
from db.interface import TRACKS_DB  # noqa: E402


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


def _select_car(form: SetupForm, car_id: str) -> SetupForm:
    idx = form.car_combo.findData(car_id)
    assert idx >= 0, f'car {car_id!r} not in car_combo'
    form.car_combo.setCurrentIndex(idx)
    return form


class SetupFormTest(unittest.TestCase):
    def setUp(self):
        _ensure_app()
        self.form = SetupForm(TuningService())

    def test_car_prefill(self):
        form = _select_car(self.form, '3440')
        text = form.db_info_label.text()
        # 3440 = 911 Turbo S Leichtbau (964) '93, 1290 kg, 381 hp, RR, 40:60
        self.assertIn('911 Turbo S Leichtbau (964) \'93', text)  # short_name
        self.assertIn('381 hp', text)
        self.assertIn('490.3 Nm', text)
        self.assertIn('1290 kg', text)
        self.assertIn('RR', text)
        self.assertIn('40:60', text)
        # Preseeded ranges: df_front [50, 200], df_rear [140, 290]
        self.assertEqual(form.df_f.value(), (50, 200))
        self.assertEqual(form.df_r.value(), (140, 290))
        # Not preseeded → empty (0,0) → None
        self.assertIsNone(form.fn_f.value())
        self.assertIsNone(form.hf.value())
        # Overrides reset to use-DB with DB values
        self.assertTrue(form.mass_use_db.isChecked())
        self.assertTrue(form.power_use_db.isChecked())
        self.assertEqual(form.mass_spin.value(), 1290)
        self.assertEqual(form.power_spin.value(), 381)
        self.assertEqual(form.bal_f_spin.value(), 40)
        self.assertEqual(form.bal_r_spin.value(), 60)
        # Car 3440 has no swaps → stock item only
        self.assertEqual(form.swap_combo.count(), 1)
        self.assertEqual(form.swap_combo.itemText(0), 'Stock engine')

    def test_car_3374_prefill_df_ranges_not_clamped(self):
        """Regression (final review): df_f/df_r spinboxes used to cap at
        1000, silently clamping car 3374's DB preseeded DF ranges
        ([800,1200] / [1200,1600]) to (800,1000) / (1000,1000) — wrong
        default-flow sheets and a clobber path via Save-ranges-to-DB."""
        form = _select_car(self.form, '3374')
        self.assertEqual(form.df_f.value(), (800, 1200))
        self.assertEqual(form.df_r.value(), (1200, 1600))
        # The spinbox caps must at least reach the preseeded maxima.
        self.assertGreaterEqual(form.df_f.max_spin.maximum(), 1200)
        self.assertGreaterEqual(form.df_r.max_spin.maximum(), 1600)
        # Unclamped collect() hands the solver the exact DB ranges.
        req = form.collect()
        self.assertEqual(req.df_front, (800, 1200))
        self.assertEqual(req.df_rear, (1200, 1600))

    def test_car_not_found_clears_and_notes(self):
        form = self.form
        form.on_car_selected('nope')
        self.assertIn('Car not found', form.status_label.text())
        self.assertEqual(form.db_info_label.text(), '')
        self.assertIsNone(form.df_f.value())
        self.assertTrue(form.power_use_db.isChecked())

    def test_collect_empty_ranges_to_none(self):
        form = _select_car(self.form, '207')  # MR2: no preseeded ranges
        req = form.collect()
        self.assertEqual(req.car_id, '207')
        self.assertIsNone(req.df_front)
        self.assertIsNone(req.df_rear)
        self.assertIsNone(req.height_front)
        self.assertIsNone(req.fn_rear)
        form.df_f.set_value((50, 200))
        self.assertEqual(form.collect().df_front, (50, 200))
        # Overrides: checked → None; unchecked → spinbox value
        self.assertIsNone(req.custom_power)
        form.power_use_db.setChecked(False)
        form.power_spin.setValue(630)
        self.assertEqual(form.collect().custom_power, 630)
        self.assertIsNone(form.collect().custom_balance)  # balance_use_db on
        form.balance_use_db.setChecked(False)
        form.bal_f_spin.setValue(42)
        form.bal_r_spin.setValue(58)
        self.assertEqual(form.collect().custom_balance, (42, 58))
        # Session fields unset → None (placeholder track, no G-forces, no solve)
        self.assertIsNone(form.collect().track_id)
        self.assertIsNone(form.collect().g_forces)
        self.assertIsNone(form.collect().solve_objective)

    def test_track_search_filters_dropdown(self):
        # Track selector mirrors the car pattern: search box + filtered
        # dropdown (no free-text editing → _track_id can't see a bogus id).
        form = self.form
        target = next(t for t in TRACKS_DB if 'suz' in t['name'].lower())
        full_count = form.track_combo.count()
        self.assertGreater(full_count, 2, 'placeholder + all tracks')
        form.track_search.setText('suz')
        self.assertLess(form.track_combo.count(), full_count, 'search must filter')
        for i in range(1, form.track_combo.count()):
            self.assertIn('suz', form.track_combo.itemText(i).lower())
        self.assertEqual(form.track_combo.itemText(0), '— (no track)')
        self.assertGreater(form.track_combo.findData(target['id']), 0)
        form.track_combo.setCurrentIndex(form.track_combo.findData(target['id']))
        self.assertEqual(form.collect().track_id, target['id'])
        # clearing the search restores the full list; placeholder → None
        form.track_search.setText('')
        self.assertEqual(form.track_combo.count(), full_count)
        form.track_combo.setCurrentIndex(0)
        self.assertIsNone(form.collect().track_id)

    def test_stability_range_allows_negative_and_collects(self):
        # GT7 stability index spans −1.0 (understeer) … +1.0 (oversteer);
        # the form must accept negative readings and collect them.
        form = _select_car(self.form, '207')
        self.assertEqual(form.stab_low_spin.minimum(), -1.0)
        self.assertEqual(form.stab_low_spin.maximum(), 1.0)
        self.assertEqual(form.stab_high_spin.minimum(), -1.0)
        self.assertEqual(form.stab_high_spin.maximum(), 1.0)
        form.stab_low_spin.setValue(-0.5)  # loose/oversteer at low speed
        req = form.collect()
        self.assertEqual(req.stability, (-0.5, 0.0))
        form.stab_low_spin.setValue(0.0)   # neutral reading → treated as unset
        self.assertIsNone(form.collect().stability)

    def test_swap_selection(self):
        form = _select_car(self.form, '207')  # MR2 GT-S '97: 241 hp / 304 Nm
        self.assertTrue(form.power_use_db.isChecked())
        self.assertEqual(form.power_spin.value(), 241)
        self.assertEqual(form.torque_spin.value(), 304.0)
        self.assertEqual(form.swap_combo.itemText(0), 'Stock engine')
        swap_idx = form.swap_combo.findData('1365')
        assert swap_idx >= 0
        self.assertEqual(form.swap_combo.itemText(swap_idx), 'BYH-R8')
        form.swap_combo.setCurrentIndex(swap_idx)
        self.assertFalse(form.power_use_db.isChecked())
        self.assertFalse(form.torque_use_db.isChecked())
        self.assertEqual(form.power_spin.value(), 420)
        self.assertEqual(form.torque_spin.value(), 429.5)
        # Back to stock → DB values restored, use-DB re-checked
        form.swap_combo.setCurrentIndex(0)
        self.assertTrue(form.power_use_db.isChecked())
        self.assertTrue(form.torque_use_db.isChecked())
        self.assertEqual(form.power_spin.value(), 241)

    def test_swap_missing_donor_no_crash(self):
        form = _select_car(self.form, '207')
        form.swap_combo.addItem('Ghost', '99999')
        with mock.patch.object(form.service, 'get_car', return_value=None):
            form.swap_combo.setCurrentIndex(form.swap_combo.count() - 1)
        self.assertIn('not found', form.status_label.text())


    def test_gforces_gate_solve(self):
        form = self.form
        self.assertFalse(form.solve_combo.isEnabled())
        form.g60_spin.setValue(1.04)
        form.g120_spin.setValue(1.19)
        self.assertFalse(form.solve_combo.isEnabled())  # 240 still unset
        form.g240_spin.setValue(1.38)
        self.assertTrue(form.solve_combo.isEnabled())
        form.g120_spin.setValue(0.0)
        self.assertFalse(form.solve_combo.isEnabled())

    def test_collect_full_request(self):
        form = _select_car(self.form, '207')  # MR2: no preseeded ranges
        form.df_f.set_value((50, 200))
        form.df_r.set_value((140, 290))
        form.hf.set_value((185, 215))
        form.hr.set_value((190, 220))
        form.fn_f.set_value((1.0, 3.0))
        form.fn_r.set_value((1.0, 3.0))
        form.g60_spin.setValue(1.04)
        form.g120_spin.setValue(1.19)
        form.g240_spin.setValue(1.38)
        form.gref_f_spin.setValue(200)
        form.gref_r_spin.setValue(310)
        idx = form.solve_combo.findData('balanced')
        assert idx >= 0
        form.solve_combo.setCurrentIndex(idx)
        form.power_use_db.setChecked(False)
        form.power_spin.setValue(630)
        form.balance_use_db.setChecked(False)
        form.bal_f_spin.setValue(42)
        form.bal_r_spin.setValue(58)
        form.symptom_checks['front_tire_wear'].setChecked(True)
        form.stab_low_spin.setValue(0.1)
        form.stab_high_spin.setValue(0.3)
        req = form.collect()
        self.assertEqual(req.car_id, '207')
        self.assertEqual(req.g_forces, (1.04, 1.19, 1.38))
        self.assertEqual(req.g_ref_df, (200, 310))
        self.assertEqual(req.solve_objective, 'balanced')
        self.assertEqual(req.custom_power, 630)
        self.assertEqual(req.custom_balance, (42, 58))
        self.assertEqual(req.symptoms, ['front_tire_wear'])
        self.assertEqual(req.stability, (0.1, 0.3))

    def test_collect_partial_gref_df_applies_both_axes(self):
        form = _select_car(self.form, '207')
        # Ref DF must accept the top of preseeded DB DF ranges (1700);
        # a 1000 cap silently clamped it (same bug class as the DF pairs).
        self.assertGreaterEqual(form.gref_f_spin.maximum(), 1700)
        self.assertGreaterEqual(form.gref_r_spin.maximum(), 1700)
        # Front-only: the single set value is used for both axes
        form.gref_f_spin.setValue(200)
        self.assertEqual(form.collect().g_ref_df, (200, 200))
        # Rear-only: likewise
        form.gref_f_spin.setValue(0)
        form.gref_r_spin.setValue(310)
        self.assertEqual(form.collect().g_ref_df, (310, 310))
        # Both zero → unset
        form.gref_r_spin.setValue(0)
        self.assertIsNone(form.collect().g_ref_df)

    def test_validate_blocks_bad_range(self):
        form = self.form
        form.on_car_selected('207')  # valid car: only the range errors remain
        form.df_f.set_value((200, 50))  # min > max
        errors = form.validate()
        self.assertGreaterEqual(len(errors), 1)
        self.assertTrue(form.status_label.text())
        self.assertIn('DF front', form.status_label.text())

    def test_save_ranges_read_only_db_no_crash(self):
        """A save that raises (read-only volume / AV lock) must surface as a
        red status, never crash the GUI."""
        form = _select_car(self.form, '3440')  # preseeded df ranges → non-empty
        def _raise(*a, **k):
            raise PermissionError(13, 'Read-only file system', 'data/cars_master.json')
        form.service.save_sliders = _raise
        form._on_save_ranges()  # must not raise
        self.assertIn('Save failed', form.status_label.text())
        self.assertTrue(form.status_label.property('error'))


if __name__ == '__main__':
    unittest.main()
