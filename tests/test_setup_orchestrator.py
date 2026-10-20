import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import setup
import cli
from db.interface import get_car

class TestSetupOrchestrator(unittest.TestCase):
    def test_build_setup_and_format_sheet(self):
        car = get_car("Ferrari F355")
        self.assertIsNotNone(car)
        res = setup.build_setup(car, mode='endurance', is_widebody=True, speed_kmh=240.0)
        self.assertIn('parameters', res)
        self.assertIn('telemetry', res)

        sheet = cli.format_setup_sheet(res)
        self.assertIn("Ferrari F355", sheet)
        self.assertIn("QUICK-TRIMS DELTA TABLE", sheet)
        self.assertIn("⚠️ เสี่ยงกระแทกซุ้มล้อ/Bump Stop", sheet)

    def test_setup_equilibrium_telemetry(self):
        car = {'name': 'Corvette ZR1', 'mass_kg': 1500, 'drivetrain': 'FR', 'power_hp': 755, 'torque_nm': 969}
        track = {'name': 'Spa-Francorchamps', 'bumpiness': 'medium', 'elevation_diff_m': 100.0}
        res = setup.build_setup(car, track=track, tire='RM')
        self.assertIn('equilibrium_proof', res['telemetry'])
        self.assertIn('tire_wear_analysis', res['telemetry'])
        self.assertIn('trail_braking_feasible', res['telemetry']['equilibrium_proof'])

if __name__ == '__main__':
    unittest.main()
