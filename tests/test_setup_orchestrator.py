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

    def test_controller_setup_and_171_meta(self):
        car = get_car("Toyota Mark II") or {'name': 'Mark II Tourer V', 'mass_kg': 1146, 'drivetrain': 'FR', 'power_hp': 746, 'torque_nm': 788}
        res = setup.build_setup(car, tire='RS', is_controller=True, mode='endurance')
        params = res['parameters']
        self.assertGreaterEqual(params['lsd_rear']['brake'], 80)
        sheet = cli.format_setup_sheet(res)
        self.assertIn("Controller / DualSense Setup", sheet)
        self.assertIn("PP Optimization Meta", sheet)

    def test_no_aero_rake_setup(self):
        car = {'name': 'Plymouth Superbird', 'mass_kg': 1600, 'drivetrain': 'FR', 'power_hp': 500, 'torque_nm': 600}
        res = setup.build_setup(car, tire='RS', df_front_range=(0, 0), df_rear_range=(0, 0))
        rh = res['parameters']['ride_height_mm']
        rake = rh['rear'] - rh['front']
        self.assertGreaterEqual(rake, 18)
        sheet = cli.format_setup_sheet(res)
        self.assertIn("No-Aero High Rake", sheet)

    def test_grip_mode_keeps_requested_tire(self):
        car = {'name': 'Grip Test', 'mass_kg': 1200, 'drivetrain': 'FR', 'power_hp': 400, 'torque_nm': 450}
        res = setup.build_setup(car, tire='SS', mode='grip')
        self.assertEqual(res['tire_compound'], 'SS')
        self.assertNotIn('tire_switched_from', res['telemetry'])

    def test_dirt_mode_forces_dirt_tire(self):
        """Dirt circuit + street tire: GT7 forces D-Tires there, so the
        orchestrator auto-switches and says so."""
        car = {'name': 'Dirt Test', 'mass_kg': 1200, 'drivetrain': 'FR', 'power_hp': 400, 'torque_nm': 450}
        res = setup.build_setup(car, tire='SS', mode='dirt')
        self.assertEqual(res['tire_compound'], 'Dirt')
        self.assertEqual(res['telemetry'].get('tire_switched_from'), 'SS')
        self.assertAlmostEqual(res['telemetry']['tire_friction_mu'], 0.90)
        sheet = cli.format_setup_sheet(res)
        self.assertIn('Tire auto-switched SS → Dirt', sheet)

    def test_dirt_mode_explicit_dirt_tire_no_switch(self):
        car = {'name': 'Dirt Test 2', 'mass_kg': 1200, 'drivetrain': 'FR', 'power_hp': 400, 'torque_nm': 450}
        res = setup.build_setup(car, tire='Dirt', mode='dirt')
        self.assertEqual(res['tire_compound'], 'Dirt')
        self.assertNotIn('tire_switched_from', res['telemetry'])

    def test_wet_mode_forces_wet_tire(self):
        car = {'name': 'Wet Test', 'mass_kg': 1200, 'drivetrain': 'FR', 'power_hp': 400, 'torque_nm': 450}
        res = setup.build_setup(car, tire='CS', mode='wet')
        self.assertEqual(res['tire_compound'], 'Wet')
        self.assertEqual(res['telemetry'].get('tire_switched_from'), 'CS')
        self.assertAlmostEqual(res['telemetry']['tire_friction_mu'], 1.00)


if __name__ == '__main__':
    unittest.main()
