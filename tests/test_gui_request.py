"""Tests for gui.request dataclasses + choice tuples (Task 2)."""
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from gui.request import (  # noqa: E402
    DRIVETRAINS,
    MODES,
    SOLVE_OBJECTIVES,
    SYMPTOMS,
    TIRE_COMPOUNDS,
    GuiRequest,
    GuiResult,
)


class GuiRequestTest(unittest.TestCase):
    def test_defaults(self):
        req = GuiRequest(car_id='207')
        self.assertEqual(req.car_id, '207')
        self.assertEqual(req.tire, 'SS')
        self.assertEqual(req.mode, 'grip')
        for field in (
            'df_front', 'df_rear', 'height_front', 'height_rear',
            'fn_front', 'fn_rear', 'compression_range', 'expansion_range',
            'custom_mass', 'custom_power',
            'custom_torque', 'custom_drivetrain', 'custom_balance',
            'track_id', 'g_forces', 'g_ref_df', 'solve_objective',
            'speed_kmh', 'stability', 'symptoms',
        ):
            self.assertIsNone(getattr(req, field), field)
        self.assertFalse(req.is_widebody)
        self.assertFalse(req.is_controller)

    def test_choice_tuples_match_cli_verbatim(self):
        self.assertEqual(TIRE_COMPOUNDS, ('CH', 'CM', 'CS', 'SH', 'SM', 'SS', 'RH', 'RM', 'RS', 'Dirt', 'Wet'))
        self.assertEqual(DRIVETRAINS, ('FF', 'FR', 'MR', 'RR', 'AWD', '4WD', '4x4'))
        self.assertEqual(MODES, ('grip', 'time_attack', 'wet', 'dirt', 'drift', 'endurance'))
        self.assertEqual(SYMPTOMS, ('entry_push', 'exit_snap', 'bottoming', 'curb_hop', 'front_tire_wear', 'rear_tire_wear'))
        self.assertEqual(SOLVE_OBJECTIVES, ('balanced', 'max_grip', 'min_tire_wear'))


class GuiResultTest(unittest.TestCase):
    def test_ok_true_when_no_error(self):
        res = GuiResult(setup={'a': 1}, sheet='x')
        self.assertTrue(res.ok)
        self.assertIsNone(res.error)
        self.assertEqual(res.warnings, [])

    def test_ok_false_when_error(self):
        res = GuiResult(error='boom')
        self.assertFalse(res.ok)
        self.assertIsNone(res.setup)
        self.assertEqual(res.sheet, '')

    def test_warnings_lists_are_independent(self):
        a = GuiResult(warnings=['w1'])
        b = GuiResult()
        a.warnings.append('w2')
        self.assertEqual(b.warnings, [])


if __name__ == '__main__':
    unittest.main()
