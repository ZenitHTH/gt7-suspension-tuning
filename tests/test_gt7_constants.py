import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
import gt7_constants

class TestGT7Constants(unittest.TestCase):
    def test_tire_mu_map_entries(self):
        self.assertEqual(gt7_constants.TIRE_MU_MAP['SS'], 1.35)
        self.assertEqual(gt7_constants.TIRE_MU_MAP['RM'], 1.55)
        self.assertEqual(gt7_constants.TIRE_MU_MAP['CH'], 0.85)

    def test_slider_bounds(self):
        self.assertEqual(gt7_constants.SLIDER_BOUNDS['damping_compression'], (20, 40))
        self.assertEqual(gt7_constants.SLIDER_BOUNDS['damping_expansion'], (30, 80))
        self.assertEqual(gt7_constants.SLIDER_BOUNDS['anti_roll_bar'], (1, 10))

    def test_chassis_and_aero_defaults(self):
        self.assertEqual(gt7_constants.AERO_REFERENCE_SPEED_KMH, 240.0)
        self.assertAlmostEqual(gt7_constants.CHASSIS_RATIOS['wheelbase_from_length'], 0.58)
        self.assertAlmostEqual(gt7_constants.CHASSIS_RATIOS['track_width_from_width'], 0.85)
        self.assertEqual(gt7_constants.STROKE_CLEARANCE_FLOOR_MM['widebody'], 16.0)
        self.assertEqual(gt7_constants.STROKE_CLEARANCE_FLOOR_MM['standard'], 22.0)

if __name__ == '__main__':
    unittest.main()
