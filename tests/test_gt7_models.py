import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from gt7_models import VehicleSpec, TrackSpec

class TestGT7Models(unittest.TestCase):
    def test_vehicle_spec_from_dict_heuristic_fallback(self):
        raw_car = {
            'name': "Ferrari F355 Berlinetta '94",
            'mass_kg': 1350,
            'drivetrain': 'MR',
            'group': 'Road Car',
            'balance': {'front_pct': 42},
            'dimensions_mm': {'length': 4250, 'width': 1900, 'height': 1170},
            'engine': {'power_hp': 380, 'torque_nm': 363}
        }
        spec = VehicleSpec.from_dict(raw_car, is_widebody=True)
        self.assertEqual(spec.mass_kg, 1350)
        self.assertEqual(spec.drivetrain, 'MR')
        self.assertAlmostEqual(spec.front_weight_ratio, 0.42)
        self.assertAlmostEqual(spec.rear_weight_ratio, 0.58)
        self.assertAlmostEqual(spec.wheelbase_m, 4.250 * 0.58, places=3)
        self.assertAlmostEqual(spec.track_width_m, 1.900 * 0.85, places=3)
        self.assertAlmostEqual(spec.hcg_m, 1.170 * 0.36, places=3)
        self.assertTrue(spec.is_widebody)

    def test_vehicle_spec_overrides_and_racecar_cg(self):
        raw_car = {
            'name': "Gran Turismo Red Bull X2019 Competition",
            'mass_kg': 650,
            'drivetrain': 'MR',
            'group': 'Gr.X',
            'balance': {'front_pct': 46},
            'dimensions_mm': {'length': 4750, 'width': 2000, 'height': 1000}
        }
        spec = VehicleSpec.from_dict(
            raw_car,
            custom_overrides={'mass': 670, 'power': 850, 'balance': (45, 55)}
        )
        self.assertEqual(spec.mass_kg, 670)
        self.assertEqual(spec.power_hp, 850)
        self.assertAlmostEqual(spec.front_weight_ratio, 0.45)
        # Racecar CG ratio: 0.32
        self.assertAlmostEqual(spec.hcg_m, 1.000 * 0.32, places=3)
        self.assertTrue(spec.is_racecar)

    def test_track_spec_from_dict(self):
        raw_track = {
            'name': "Autodromo Lago Maggiore",
            'category': "circuit",
            'bumpiness': "low",
            'elevation_diff_m': 45.0,
            'downforce_demand': "high",
            'longest_straight_m': 800.0
        }
        track = TrackSpec.from_dict(raw_track, mode='endurance')
        self.assertEqual(track.name, "Autodromo Lago Maggiore")
        self.assertEqual(track.bumpiness, "low")
        self.assertEqual(track.elevation_diff_m, 45.0)
        self.assertEqual(track.downforce_demand, "high")
        self.assertEqual(track.longest_straight_m, 800.0)
        self.assertFalse(track.is_oval)
        self.assertFalse(track.is_dirt)
        self.assertTrue(track.is_endurance)

    def test_track_spec_grip_modifier(self):
        # Per-surface grip multiplier: read from dict, sane default, clamped.
        self.assertAlmostEqual(TrackSpec.from_dict({'name': 'X', 'grip_modifier': 0.95}).grip_modifier, 0.95)
        self.assertAlmostEqual(TrackSpec.from_dict({'name': 'X', 'grip_modifier': 0.65}).grip_modifier, 0.65)
        self.assertAlmostEqual(TrackSpec.from_dict({'name': 'X'}).grip_modifier, 1.0)
        self.assertAlmostEqual(TrackSpec.from_dict({'grip_modifier': 0.1}).grip_modifier, 0.3)
        self.assertAlmostEqual(TrackSpec.from_dict({'grip_modifier': 2.0}).grip_modifier, 1.2)
        self.assertAlmostEqual(TrackSpec().grip_modifier, 1.0)

if __name__ == '__main__':
    unittest.main()
