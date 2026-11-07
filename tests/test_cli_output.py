import unittest
from cli import format_setup_sheet
from setup import build_setup

class TestCLIOutput(unittest.TestCase):
    def test_cli_sheet_contains_correct_brake_bias_format(self):
        mock_setup = {
            'car': {'name': 'Test FR', 'drivetrain': 'FR', 'mass_kg': 1300, 'balance': {'ratio_str': '54:46'}},
            'track': {'name': 'Nurburgring', 'mode': 'grip'},
            'tire_compound': 'RM',
            'setup_mode': 'GRIP',
            'telemetry': {'ay_est': 1.5, 'mu': 1.5, 'tot_s': 1100, 'c_f': 280, 'c_r': 270, 'fr_ratio': 1.05, 'lltd_pct': 48.0, 'pitch_transfer_pct': 18.0, 'is_no_aero': False},
            'parameters': {
                'ride_height_mm': {'front': 95, 'rear': 105},
                'natural_frequency_hz': {'front': 2.6, 'rear': 2.8},
                'anti_roll_bar': {'front': 4, 'rear': 6},
                'damping_compression_pct': {'front': 30, 'rear': 32},
                'damping_expansion_pct': {'front': 48, 'rear': 50},
                'camber_deg': {'front': -2.2, 'rear': -1.2},
                'toe_angle': {'front': '0.00', 'rear': 'In 0.10'},
                'downforce': {'front': 100, 'rear': 200},
                'lsd_rear': {'init': 6, 'accel': 24, 'brake': 14},
                'brake_bias': 2,
                'transmission_top_speed_kmh': 280
            }
        }
        sheet = format_setup_sheet(mock_setup)
        self.assertIn("+2 (หลัง / Rear)", sheet)
        self.assertNotIn("(หน้า + / หลัง -)", sheet)

    def test_format_brake_bias_ground_truth_label(self):
        from sheet_formatter import format_brake_bias_label
        self.assertEqual(format_brake_bias_label(-1), "-1 (หน้า / Front)")
        self.assertEqual(format_brake_bias_label(2), "+2 (หลัง / Rear)")
        self.assertEqual(format_brake_bias_label(0), "0 (กลาง / Center)")

    def test_format_setup_sheet_contains_proofs(self):
        car = {'name': 'Porsche 911 GT3 RS', 'mass_kg': 1430, 'drivetrain': 'RR', 'power_hp': 520, 'torque_nm': 470}
        setup_dict = build_setup(car, tire='RS')
        sheet = format_setup_sheet(setup_dict)
        self.assertIn('Trail-Braking', sheet)
        self.assertIn('Squat', sheet)
        self.assertIn('Tire Wear', sheet)

    def test_dynamic_g_force_at_downforce_and_solver_in_sheet(self):
        car = {
            'id': '3466', 'name': "Ford Sierra RS 500 Cosworth '87",
            'drivetrain': 'FR', 'mass_kg': 989, 'power_hp': 359, 'torque_nm': 368.9,
            'balance': {'front_pct': 56, 'rear_pct': 44}
        }
        res = build_setup(
            car=car, tire='RM', mode='endurance',
            df_front_range=(50, 200), df_rear_range=(100, 250),
            height_front_range=(100, 200), height_rear_range=(120, 220),
            fn_front_range=(1.50, 3.50), fn_rear_range=(1.50, 3.50),
            g_forces=(1.46, 1.59, 1.75), g_ref_df=(110, 100),
            solve_objective='balanced', is_widebody=True, speed_kmh=240.0
        )
        sheet = format_setup_sheet(res)
        df_f = res['parameters']['downforce']['front']
        df_r = res['parameters']['downforce']['rear']
        self.assertIn(f"@ DF {df_f}/{df_r}", sheet)
        self.assertIn("Min DF", sheet)
        self.assertIn("Max DF", sheet)
        self.assertFalse(res['telemetry']['high_speed_simulation']['bottoming_or_fender_hit'])

    def test_omitted_g_ref_df_anchors_to_baseline_and_syncs_lateral_g(self):
        car = {
            'id': '3466', 'name': "Ford Sierra RS 500 Cosworth '87",
            'drivetrain': 'FR', 'mass_kg': 989, 'power_hp': 359, 'torque_nm': 368.9,
            'balance': {'front_pct': 56, 'rear_pct': 44}
        }
        res = build_setup(
            car=car, tire='RM', df_front_range=(50, 200), df_rear_range=(100, 250),
            g_forces=(1.46, 1.59, 1.75)
        )
        # Should anchor at baseline downforce without double-counting G
        dyn = res['telemetry']['dynamic_g_force']
        self.assertAlmostEqual(dyn['g_240'], 1.75, places=2)
        self.assertAlmostEqual(res['telemetry']['lateral_g_capacity'], 1.75, places=2)

    def test_wingless_car_sheet_avoids_redundant_min_max_comparison(self):
        car = {'name': 'Civic Type R', 'mass_kg': 1050, 'drivetrain': 'FF', 'power_hp': 185, 'torque_nm': 160}
        res = build_setup(car, tire='SS', df_front_range=(0, 0), df_rear_range=(0, 0), solve_objective='balanced')
        sheet = format_setup_sheet(res)
        self.assertIn("DF 0/0", sheet)
        self.assertNotIn("Min DF (0/0)", sheet)

    def test_measured_g_forces_couple_spring_rate_and_camber(self):
        car = {
            'id': '451', 'name': "Subaru Impreza 22B-STi '98",
            'drivetrain': 'AWD', 'mass_kg': 990, 'power_hp': 401, 'torque_nm': 436.2,
            'balance': {'front_pct': 58, 'rear_pct': 42}
        }
        sport_res = build_setup(
            car=car, tire='SS', mode='grip',
            fn_front_range=(1.50, 3.50), fn_rear_range=(1.50, 3.50),
            g_forces=(1.09, 1.17, 1.32), g_ref_df=(100, 187), solve_objective='balanced'
        )
        racing_res = build_setup(
            car=car, tire='RS', mode='grip',
            fn_front_range=(1.50, 3.50), fn_rear_range=(1.50, 3.50),
            g_forces=(1.29, 1.36, 1.55), g_ref_df=(100, 180), solve_objective='balanced'
        )
        self.assertLess(
            sport_res['parameters']['natural_frequency_hz']['front'],
            racing_res['parameters']['natural_frequency_hz']['front']
        )
        # Sport camber is flatter (closer to 0, so numerically greater than racing negative camber)
        self.assertGreater(
            sport_res['parameters']['camber_deg']['front'],
            racing_res['parameters']['camber_deg']['front']
        )

    def test_symptom_trim_preserves_camber_and_syncs_telemetry_under_solver(self):
        car = {
            'id': '1900', 'name': "Lamborghini Diablo GT '00",
            'drivetrain': 'MR', 'mass_kg': 1490, 'power_hp': 653, 'torque_nm': 695.2,
            'balance': {'front_pct': 41, 'rear_pct': 59}
        }
        base_res = build_setup(
            car=car, tire='SS', mode='grip',
            df_front_range=(0, 100), df_rear_range=(130, 280),
            g_forces=(1.11, 1.22, 1.34), g_ref_df=(80, 150), solve_objective='balanced'
        )
        trim_res = build_setup(
            car=car, tire='SS', mode='grip',
            df_front_range=(0, 100), df_rear_range=(130, 280),
            g_forces=(1.11, 1.22, 1.34), g_ref_df=(80, 150), solve_objective='balanced',
            symptoms=['front_tire_wear']
        )
        self.assertGreater(
            trim_res['parameters']['camber_deg']['front'],
            base_res['parameters']['camber_deg']['front']
        )
        self.assertLess(
            trim_res['telemetry']['tire_wear_analysis']['front_wear_factor'],
            base_res['telemetry']['tire_wear_analysis']['front_wear_factor']
        )

class TestWarningAdvisories(unittest.TestCase):
    """Warning lines must carry actionable advice: setup-safe vs pace-limit vs data-issue."""

    def _gc(self, status='pass', mg_min=1.25, map_headroom=None):
        return {
            'status': status,
            'handling_balance': 'neutral',
            'corner_fz_n': {'front_outside': 4000, 'front_inside': 3800,
                            'rear_outside': 4600, 'rear_inside': 4300},
            'transfer_front_n': 350,
            'margins': {'front': 1.25, 'rear': 1.30, 'min': mg_min},
            'ay_check_g': 1.59, 'aero_g': 0.0, 'mu_ref': 1.55,
            'map_headroom': map_headroom, 'understeer_gradient': 0.02,
            'ay_fric_g': 1.59,
        }

    def test_grip_pace_warn_explains_not_setup_fault(self):
        from sheet_formatter import _format_grip_check_lines
        sheet = '\n'.join(_format_grip_check_lines(self._gc('warn', mg_min=0.87)))
        self.assertIn('Pace limit, NOT a setup fault', sheet)
        self.assertIn('cannot add tire friction', sheet)
        self.assertIn(f'~{0.87 * 1.59:.2f}G', sheet)
        self.assertNotIn('Check tire compound', sheet)

    def test_grip_map_warn_is_data_check_not_pace(self):
        from sheet_formatter import _format_grip_check_lines
        sheet = '\n'.join(_format_grip_check_lines(
            self._gc('warn', mg_min=1.05, map_headroom=0.90)))
        self.assertIn('Check tire compound', sheet)
        self.assertNotIn('Pace limit', sheet)

    def test_grip_pass_and_info_advisories(self):
        from sheet_formatter import _format_grip_check_lines
        p = '\n'.join(_format_grip_check_lines(self._gc('pass')))
        for needle in ('Pace limit', 'Reference only', 'Check tire compound'):
            self.assertNotIn(needle, p)
        i = '\n'.join(_format_grip_check_lines(self._gc('info', mg_min=0.95)))
        self.assertIn('Reference only', i)
        self.assertNotIn('Pace limit', i)

    def test_equilibrium_warn_explains_pace_limit(self):
        from sheet_formatter import _format_equilibrium_lines
        eq = {'trail_braking_feasible': False, 'acceleration_squat_rear_mm': 4,
              'acceleration_lift_front_mm': 2, 'dynamic_rake_accel_mm': 2,
              'min_dynamic_clearance_mm': 0,
              'total_trail_compression_front_mm': 60,
              'dynamic_rake_brake_mm': 3}
        warn = '\n'.join(_format_equilibrium_lines(eq))
        self.assertIn('treat as pace limit', warn)
        self.assertIn('highest safe height', warn)
        ok = dict(eq, trail_braking_feasible=True, min_dynamic_clearance_mm=12)
        self.assertNotIn('treat as pace limit',
                         '\n'.join(_format_equilibrium_lines(ok)))


if __name__ == '__main__':
    unittest.main()
