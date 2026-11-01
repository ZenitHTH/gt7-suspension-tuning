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

    def test_calculate_top_speed_power_to_weight_tiers(self):
        # Tier 1: Extreme Power-to-Weight (X2019 / Hypercar)
        spd_tier1 = calculate_top_speed(power=816.0, ptw=1255.0, longest_straight_m=800.0, elevation_diff_m=74.0)
        self.assertEqual(spd_tier1, 340)

        # Tier 2: Gr.3 / Downforce racecar
        spd_tier2 = calculate_top_speed(power=500.0, ptw=384.0, longest_straight_m=800.0, elevation_diff_m=74.0)
        self.assertEqual(spd_tier2, 290)

    def test_universal_tire_wear_rebalancing_symptoms(self):
        from lib.trims import apply_closed_loop_trim
        params = {
            'anti_roll_bar': {'front': 4, 'rear': 6},
            'downforce': {'front': 980, 'rear': 1420},
            'camber_deg': {'front': -2.2, 'rear': -1.2},
            'toe_angle': {'front': 'Out 0.04', 'rear': 'In 0.12'},
            'damping_compression_pct': {'front': 32, 'rear': 36},
            'damping_expansion_pct': {'front': 47, 'rear': 54},
            'ride_height_mm': {'front': 50, 'rear': 57},
            'brake_bias': -1,
            'lsd_rear': {'init': 5, 'accel': 16, 'brake': 48}
        }
        res = apply_closed_loop_trim(parameters=params, symptoms=['front_tire_wear'], drivetrain='MR')
        self.assertLess(res['anti_roll_bar']['front'], 4)
        self.assertGreater(res['anti_roll_bar']['rear'], 6)
        self.assertEqual(res['toe_angle']['front'], '0.00')
        self.assertLess(res['downforce']['front'], 980)
        self.assertGreater(res['camber_deg']['front'], -2.2) # Flattened (-1.7)
        self.assertEqual(res['brake_bias'], 0)

    def test_calculate_brake_bias_ground_truth(self):
        # FF must have front bias (negative)
        bias_ff, _ = calculate_brake_bias(wf=0.62, drivetrain='FF')
        self.assertIn(bias_ff, [-1, -2])
        # FR front-heavy on wheel should have rearward bias (positive) for trail-brake rotation
        bias_fr_wheel, _ = calculate_brake_bias(wf=0.54, drivetrain='FR', is_controller=False)
        self.assertIn(bias_fr_wheel, [1, 2, 3])
        # FR on controller must be clamped to <= 1 to avoid ABS snap
        bias_fr_pad, _ = calculate_brake_bias(wf=0.54, drivetrain='FR', is_controller=True)
        self.assertLessEqual(bias_fr_pad, 1)
        # FR balanced car (wf < 0.52) in endurance mode must remain neutral (0), not bump to 1
        bias_fr_bal_endur, _ = calculate_brake_bias(wf=0.48, drivetrain='FR', is_endurance=True, is_controller=False)
        self.assertEqual(bias_fr_bal_endur, 0)
        # FR heavy muscle car (wf=0.58) in endurance mode softens rear bias from 2 to 1
        bias_fr_heavy_sprint, _ = calculate_brake_bias(wf=0.58, drivetrain='FR', is_endurance=False, is_controller=False)
        bias_fr_heavy_endur, _ = calculate_brake_bias(wf=0.58, drivetrain='FR', is_endurance=True, is_controller=False)
        self.assertEqual(bias_fr_heavy_sprint, 2)
        self.assertEqual(bias_fr_heavy_endur, 1)
        # AWD (Genesis G70 Gr.4) must have slight front or center bias to avoid center diff binding
        bias_awd, _ = calculate_brake_bias(wf=0.53, drivetrain='AWD')
        self.assertIn(bias_awd, [-1, 0])
        # MR should have neutral or slight front bias (0 to -2) as yaw damper
        bias_mr, _ = calculate_brake_bias(wf=0.44, drivetrain='MR')
        self.assertIn(bias_mr, [-2, -1, 0])

    def test_asymmetric_slider_floor_rear_squat_buffer(self):
        # Asymmetric slider floors (e.g. Sierra RS: 100-200 Front / 120-220 Rear)
        # must guarantee rear travel buffer of h_min_r + margin + widebody
        rh_f, rh_r = calculate_ride_height(
            height_front_range=(100, 200),
            height_rear_range=(120, 220),
            wf=0.56,
            is_widebody=True
        )
        self.assertEqual(rh_f, 115)
        self.assertEqual(rh_r, 135)
        self.assertGreaterEqual(rh_r - 120, 15)

    def test_endurance_downforce_safety_clamp_and_precedence(self):
        # Front-heavy FR car (wf=0.56) in endurance mode with 50-200 / 100-250
        df = calculate_aerodynamics(
            df_front_range=(50, 200),
            df_rear_range=(100, 250),
            wf=0.56,
            is_endurance=True
        )
        self.assertEqual(df['front'], 118)
        self.assertEqual(df['rear'], 190)
        self.assertLessEqual(df['front'], df['rear'])

        # Constrained rear spoiler (50-200 / 50-100): front must clamp to rear
        df_constrained = calculate_aerodynamics(
            df_front_range=(50, 200),
            df_rear_range=(50, 100),
            wf=0.56,
            is_endurance=True
        )
        self.assertEqual(df_constrained['rear'], 80)
        self.assertEqual(df_constrained['front'], 80) # Clamped from 118 to 80!

if __name__ == '__main__':
    unittest.main()
