"""Tests for gui.service (Tasks 2-3): TuningService + Worker(QObject)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from unittest import mock  # noqa: E402

from db.interface import TRACKS_DB, norm_str  # noqa: E402
from db.loader import get_data_dir  # noqa: E402
from PyQt6.QtCore import QCoreApplication  # noqa: E402

import gui.service  # noqa: E402
from gui.request import GuiRequest, GuiResult  # noqa: E402
from gui.service import TuningService, Worker  # noqa: E402


def _mr2_request() -> GuiRequest:
    return GuiRequest(
        car_id='207',
        df_front=(50, 200),
        df_rear=(120, 310),
        height_front=(90, 160),
        height_rear=(90, 160),
        fn_front=(1.5, 3.5),
        fn_rear=(1.5, 3.5),
        g_forces=(1.04, 1.19, 1.38),
        g_ref_df=(200, 310),
        solve_objective='balanced',
        custom_power=630,
        custom_mass=1289,
        custom_balance=(42, 58),
    )


class TuningServiceTest(unittest.TestCase):
    def setUp(self):
        self.svc = TuningService()

    def test_mr2_compute_ok(self):
        res = self.svc.compute(_mr2_request())
        self.assertTrue(res.ok, msg=res.error)
        self.assertIsInstance(res.setup, dict)
        self.assertIn('MR2', res.sheet)
        self.assertIn('Body Height', res.sheet)
        self.assertIn('QUICK-TRIMS DELTA TABLE', res.sheet)
        self.assertEqual(res.warnings, [])

    def test_compute_bad_car(self):
        res = self.svc.compute(GuiRequest(car_id='nope'))
        self.assertFalse(res.ok)
        self.assertIn('Car not found: nope', res.error)
        self.assertIsNone(res.setup)

    def test_dirt_mode_switches_tire_and_warns(self):
        req = _mr2_request()
        req.tire, req.mode = 'SS', 'dirt'
        res = self.svc.compute(req)
        self.assertTrue(res.ok, msg=res.error)
        self.assertEqual(res.setup['tire_compound'], 'Dirt')
        self.assertTrue(any('Tire auto-switched SS → Dirt' in w for w in res.warnings))
        self.assertIn('Tire auto-switched SS → Dirt', res.sheet)

    def test_validate_errors(self):
        errors, _ = self.svc.validate(GuiRequest(car_id='nope'))
        self.assertIn('Car not found: nope', errors)

        errors, _ = self.svc.validate(GuiRequest(car_id='207', df_front=(200, 50)))
        self.assertTrue(any('Downforce front' in e for e in errors), errors)

        errors, _ = self.svc.validate(GuiRequest(car_id='207', fn_front=(-1.5, 3.5)))
        self.assertTrue(any('natural frequency front' in e for e in errors), errors)

    def test_validate_stability_allows_negatives(self):
        # stability is a signed (low, high) index (−1.00 understeer …
        # +1.00 oversteer), NOT a min/max range: negative readings are
        # valid and must not raise a 'value below 0' error, and no
        # min>max ordering applies (low-speed may exceed high-speed).
        req = _mr2_request()
        req.stability = (-0.35, 0.25)  # SKILL.md §2.A example reading
        errors, _ = self.svc.validate(req)
        self.assertEqual(errors, [], errors)
        errors, _ = self.svc.validate(GuiRequest(car_id='207', stability=(-0.9, -0.5)))
        self.assertEqual(errors, [], errors)

    def test_validate_warnings(self):
        _, warnings = self.svc.validate(GuiRequest(car_id='207', solve_objective='balanced'))
        self.assertTrue(any('Solver needs G-force calibration' in w for w in warnings), warnings)

        _, warnings = self.svc.validate(GuiRequest(car_id='207', g_forces=(1.04, 1.19, 1.38)))
        self.assertTrue(any('G-forces without reference downforce' in w for w in warnings), warnings)

        _, warnings = self.svc.validate(GuiRequest(car_id='207', custom_balance=(55, 40)))
        self.assertTrue(any('Balance front+rear = 95 (expected 100)' in w for w in warnings), warnings)

    def test_swaps_and_ranges(self):
        swaps = self.svc.get_swaps('207')
        self.assertEqual(len(swaps), 1)
        self.assertEqual(swaps[0]['engine'], 'BYH-R8')
        self.assertEqual(self.svc.get_swaps('nope'), [])

        ranges = self.svc.get_slider_ranges('3440')
        self.assertIsInstance(ranges, dict)
        self.assertEqual(ranges['df_front'], [50, 200])

    def test_search_cars_and_tracks(self):
        cars = self.svc.search_cars('MR2')
        self.assertTrue(any(str(c.get('id')) == '207' for c in cars), cars)
        self.assertIsNone(self.svc.get_car('nope'))
        self.assertEqual(self.svc.get_car('207')['name'], "Toyota MR2 GT-S '97")

        self.assertEqual(len(self.svc.search_tracks('')), len(TRACKS_DB))
        first = TRACKS_DB[0]
        token = norm_str(first['name']).split()[0]
        self.assertIn(first, self.svc.search_tracks(token))
        self.assertIs(self.svc.get_track(str(first['id'])), first)
        self.assertIsNone(self.svc.get_track('zz-9999-not-a-track'))

    def test_save_sliders_roundtrip(self):
        src = os.path.join(get_data_dir(), 'cars_master.json')
        with open(src, 'rb') as f:
            before = f.read()
        fd, tmp = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        try:
            shutil.copyfile(src, tmp)
            self.assertTrue(self.svc.save_sliders('3440', {'df_front': (10, 20)}, db_path=tmp))
            with open(tmp, encoding='utf-8') as f:
                cars = json.load(f)
            car = next(c for c in cars if str(c.get('id')) == '3440')
            self.assertEqual(car['slider_ranges']['df_front'], [10, 20])
            self.assertFalse(self.svc.save_sliders('nope', {'df_front': (10, 20)}, db_path=tmp))
        finally:
            os.unlink(tmp)
        with open(src, 'rb') as f:
            self.assertEqual(before, f.read(), 'real DB file must stay untouched')

    def test_kwargs_mapping(self):
        req = _mr2_request()
        captured = {}

        def stub(car, **kwargs):
            captured['car'] = car
            captured['kwargs'] = kwargs
            return {'car': car, 'track': None, 'tire_compound': req.tire,
                    'setup_mode': req.mode, 'telemetry': {}, 'parameters': {}}

        expected = {
            'track': None, 'tire': 'SS', 'mode': 'grip',
            'custom_mass': 1289, 'custom_power': 630, 'custom_torque': None,
            'custom_drivetrain': None, 'custom_balance': (42, 58),
            'df_front_range': (50, 200), 'df_rear_range': (120, 310),
            'height_front_range': (90, 160), 'height_rear_range': (90, 160),
            'fn_front_range': (1.5, 3.5), 'fn_rear_range': (1.5, 3.5),
            'stability': None, 'symptoms': None, 'is_widebody': False,
            'speed_kmh': None, 'is_controller': False,
            'g_forces': (1.04, 1.19, 1.38), 'g_ref_df': (200, 310),
            'solve_objective': 'balanced',
        }
        with mock.patch.object(gui.service.setup, 'build_setup', stub), \
             mock.patch.object(gui.service, 'format_setup_sheet', return_value='SHEET'):
            res = self.svc.compute(req)
        self.assertTrue(res.ok, msg=res.error)
        self.assertEqual(res.sheet, 'SHEET')
        self.assertNotIn('height_range', captured['kwargs'])
        self.assertEqual(captured['kwargs'], expected)
        self.assertEqual(captured['car']['name'], "Toyota MR2 GT-S '97")


class WorkerTests(unittest.TestCase):
    """Worker(QObject) emits `finished` with a GuiResult (Task 3)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(['test'])

    def test_run_emits_finished(self):
        collector = []
        worker = Worker(TuningService(), _mr2_request())
        worker.finished.connect(collector.append)
        worker.run()  # synchronous — no QThread needed for the unit test
        self.assertEqual(len(collector), 1)
        self.assertIsInstance(collector[0], GuiResult)
        self.assertTrue(collector[0].ok, msg=collector[0].error)


if __name__ == '__main__':
    unittest.main()
