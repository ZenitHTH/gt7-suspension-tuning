import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))

from lib.formulas import (
    calculate_wheel_rate,
    calculate_sprung_mass,
    calculate_acceleration_squat_dive,
    calculate_combined_trail_braking_load,
    calculate_tire_wear_index
)
from lib.springs import calculate_natural_frequencies, calculate_anti_roll_bars
from lib.shocks import calculate_dampers
from lib.wheels import calculate_wheel_alignment, calculate_brake_bias, get_tire_mu
from lib.aero_body import (
    calculate_ride_height,
    calculate_aerodynamics,
    simulate_high_speed_trail_braking,
    solve_suspension_equilibrium
)
from lib.drivetrain import calculate_differential_lsd, calculate_top_speed
from lib.trims import apply_closed_loop_trim, build_quick_trims

class TestLibModules(unittest.TestCase):
    def test_formulas(self):
        kw = calculate_wheel_rate(2.5, 300.0)
        self.assertGreater(kw, 50000.0)
        tot_s, c_f, c_r = calculate_sprung_mass(1000.0, 0.50, 'Road Car')
        self.assertEqual(tot_s, 880.0)

    def test_acceleration_squat_dive(self):
        res = calculate_acceleration_squat_dive(
            torque_nm=600.0, power_hp=500.0, mass_kg=1400.0, drivetrain='FR',
            hcg_m=0.45, wheelbase_m=2.6, wheel_rate_f=55000.0, wheel_rate_r=65000.0
        )
        self.assertIn('squat_rear_mm', res)
        self.assertIn('lift_front_mm', res)
        self.assertGreater(res['squat_rear_mm'], 0.0)
        self.assertGreater(res['lift_front_mm'], 0.0)

    def test_combined_trail_braking(self):
        res = calculate_combined_trail_braking_load(
            mass_kg=1350.0, mu=1.35, hcg_m=0.45, wheelbase_m=2.5,
            track_width_m=1.6, lltd_f=0.55, arb_f=5, wheel_rate_f=60000.0,
            speed_kmh=180.0, df_front=150.0
        )
        self.assertIn('total_deflection_mm', res)
        self.assertIn('pitch_component_mm', res)
        self.assertIn('roll_component_mm', res)
        self.assertIn('aero_component_mm', res)
        self.assertGreater(res['total_deflection_mm'], 10.0)

    def test_tire_wear_index(self):
        wear = calculate_tire_wear_index(
            fn_hz_f=2.8, fn_hz_r=3.0, camber_f=3.0, camber_r=2.0,
            toe_f=-0.10, toe_r=0.20, ptw=300.0, is_endurance=True
        )
        self.assertIn('front_wear_factor', wear)
        self.assertIn('rear_wear_factor', wear)
        self.assertGreater(wear['front_wear_factor'], 1.0)

    def test_suspension_equilibrium_solver(self):
        res = solve_suspension_equilibrium(
            mass_kg=1400.0, front_ratio=0.54, power_hp=500.0, torque_nm=650.0,
            drivetrain='FR', hcg_m=0.45, wheelbase_m=2.6, track_width_m=1.6,
            mu=1.35, fn_f=2.6, fn_r=2.8, arb_f=4, arb_r=6,
            df_f=120, df_r=200, height_front_range=(90, 140), height_rear_range=(95, 145),
            speed_kmh=220.0
        )
        self.assertIn('optimal_rh_front', res)
        self.assertIn('optimal_rh_rear', res)
        self.assertIn('trail_braking_feasible', res)
        self.assertIn('min_dynamic_clearance_mm', res)
        self.assertGreaterEqual(res['optimal_rh_front'], 90)
        self.assertGreaterEqual(res['min_dynamic_clearance_mm'], 0.0)

    def test_springs_and_shocks(self):
        fn_f, fn_r, ratio = calculate_natural_frequencies(1.35, 0.50, 'medium', 'Road Car', 1350.0)
        self.assertGreater(fn_f, 1.5)
        self.assertGreater(ratio, 1.0)
        c_f, c_r, e_f, e_r = calculate_dampers('medium', 200.0, False, 'FR', 0.50)
        self.assertLessEqual(c_f, 40)
        self.assertLessEqual(c_r, 40)

    def test_wheels_and_aero(self):
        self.assertEqual(get_tire_mu('SS'), 1.35)
        rh_f, rh_r = calculate_ride_height(is_widebody=True)
        self.assertGreaterEqual(rh_f, 100)
        aero = calculate_aerodynamics(wf=0.50, group='Gr.3')
        self.assertIn('front', aero)

    def test_drivetrain_and_trims(self):
        lsd_r, _ = calculate_differential_lsd(400.0, 250.0, 0.50, 'FR')
        self.assertIn('init', lsd_r)
        spd = calculate_top_speed(300.0, 200.0)
        self.assertGreaterEqual(spd, 230)

if __name__ == '__main__':
    unittest.main()
