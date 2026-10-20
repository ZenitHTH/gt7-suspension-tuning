import unittest
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import gt7_dynamics

class TestGT7Dynamics(unittest.TestCase):
    def test_sprung_mass_calculation(self):
        # 1470 kg, 41% front, Road car (sprung ratio 0.88)
        total_s, corner_f, corner_r = gt7_dynamics.calculate_sprung_mass(1470.0, 0.41, 'Road Car')
        self.assertAlmostEqual(total_s, 1293.6, places=1)
        self.assertAlmostEqual(corner_f, 265.2, places=1)
        self.assertAlmostEqual(corner_r, 381.6, places=1)

    def test_flat_ride_frequency(self):
        # Sport Soft tire (mu = 1.35), 50% front, normal track
        fn_f, fn_r, ratio = gt7_dynamics.calculate_natural_frequencies(mu=1.35, wf=0.50, bumpiness='medium')
        self.assertGreater(fn_r, fn_f)
        self.assertAlmostEqual(ratio, 1.07, places=2)

    def test_lltd_and_anti_roll_bars(self):
        # Front-heavy FR car (58% front) should have soft front ARB and stiff rear ARB to eliminate understeer
        arb_f, arb_r, lltd_pct = gt7_dynamics.calculate_anti_roll_bars(wf=0.58, drivetrain='FR')
        self.assertLess(arb_f, arb_r)
        self.assertEqual(arb_f, 3)
        self.assertEqual(arb_r, 7)

        # Rear-heavy RR car (38% front) should have stiff front ARB to prevent snap
        arb_f_rr, arb_r_rr, _ = gt7_dynamics.calculate_anti_roll_bars(wf=0.38, drivetrain='RR')
        self.assertGreater(arb_f_rr, arb_r_rr)

    def test_differential_lsd_braking(self):
        # Front-heavy car (42% rear) must have relaxed braking sensitivity (12-15) for trail-braking
        lsd_rear, _ = gt7_dynamics.calculate_differential_lsd(torque=500.0, ptw=350.0, wr=0.42, drivetrain='FR')
        self.assertLessEqual(lsd_rear['brake'], 15)

        # Mid-engine car (59% rear) must have higher braking sensitivity to stabilize trail-braking
        lsd_mr, _ = gt7_dynamics.calculate_differential_lsd(torque=740.0, ptw=564.0, wr=0.59, drivetrain='MR')
        self.assertGreaterEqual(lsd_mr['brake'], 34)

    def test_dynamic_brake_bias(self):
        # Front-heavy car with heavy nose-dive must have rearward brake bias (-2 to -3)
        bias, transfer_pct = gt7_dynamics.calculate_brake_bias(wf=0.58, hcg_m=0.46, wheelbase_m=2.6, drivetrain='FR')
        self.assertLessEqual(bias, -2)
        self.assertGreater(transfer_pct, 15.0)

    def test_aerodynamic_downforce_with_ranges(self):
        # Custom slider range: 175-275 Front / 305-505 Rear for MR car
        df = gt7_dynamics.calculate_aerodynamics(
            df_front_range=(175, 275),
            df_rear_range=(305, 505),
            wf=0.41,
            group='Road Car'
        )
        self.assertEqual(df['front'], 235)
        self.assertEqual(df['rear'], 425)

    def test_elevation_crest_ride_height_and_dampers(self):
        # Steep elevation track (>= 50m like SUGO 69.8m or Bathurst 174m) adds ride height buffer and rear rebound
        rh_flat = gt7_dynamics.calculate_ride_height(bumpiness='medium', wf=0.50, elevation_diff_m=10.0)
        rh_steep = gt7_dynamics.calculate_ride_height(bumpiness='medium', wf=0.50, elevation_diff_m=69.8)
        self.assertEqual(rh_steep[0], rh_flat[0] + 4)

        _, _, _, exp_r_flat = gt7_dynamics.calculate_dampers(bumpiness='medium', ptw=300.0, elevation_diff_m=10.0)
        comp_f, comp_r, _, exp_r_steep = gt7_dynamics.calculate_dampers(bumpiness='medium', ptw=300.0, elevation_diff_m=69.8)
        self.assertGreater(exp_r_steep, exp_r_flat)
        self.assertGreaterEqual(exp_r_steep / comp_r, 1.48)

    def test_aerodynamics_downforce_demand_scaling(self):
        df_low = gt7_dynamics.calculate_aerodynamics((100, 200), (200, 400), wf=0.50, downforce_demand='low')
        df_med = gt7_dynamics.calculate_aerodynamics((100, 200), (200, 400), wf=0.50, downforce_demand='medium')
        df_high = gt7_dynamics.calculate_aerodynamics((100, 200), (200, 400), wf=0.50, downforce_demand='high')
        self.assertEqual((df_low['front'], df_low['rear']), (140, 280))
        self.assertEqual((df_med['front'], df_med['rear']), (160, 320))
        self.assertEqual((df_high['front'], df_high['rear']), (180, 350))

    def test_calculate_top_speed_by_straight_length(self):
        v_short = gt7_dynamics.calculate_top_speed(power=400, ptw=300, longest_straight_m=450)
        v_long = gt7_dynamics.calculate_top_speed(power=400, ptw=300, longest_straight_m=1500)
        self.assertGreater(v_long, v_short)

    def test_track_telemetry_missing_keys_fallback(self):
        import gt7_tuner
        car = {'id': '9999', 'name': 'Test Car', 'drivetrain': 'FR', 'mass_kg': 1350, 'balance': {'front_pct': 50}}
        sparse_track = {'name': 'Sparse Circuit', 'bumpiness': None, 'elevation_diff_m': None, 'downforce_demand': None, 'longest_straight_m': None}
        setup = gt7_tuner.build_setup(car=car, track=sparse_track)
        self.assertIn('ride_height_mm', setup['parameters'])

    def test_downforce_frequency_coupling(self):
        fn_low_df = gt7_dynamics.calculate_natural_frequencies(mu=1.45, wf=0.50, df_front=75, df_rear=110)
        fn_high_df = gt7_dynamics.calculate_natural_frequencies(mu=1.45, wf=0.50, df_front=400, df_rear=600)
        self.assertGreater(fn_high_df[0], fn_low_df[0])
        self.assertGreater(fn_high_df[1], fn_low_df[1])

    def test_downforce_frequency_coupling_clamped_to_slider_max(self):
        fn_f, fn_r, _ = gt7_dynamics.calculate_natural_frequencies(
            mu=1.65, wf=0.50, mass=2100.0,
            fn_front_range=(2.00, 3.10), fn_rear_range=(2.00, 3.20),
            df_front=900, df_rear=1400
        )
        self.assertLessEqual(fn_f, 3.10)
        self.assertLessEqual(fn_r, 3.20)

    def test_save_and_autoload_slider_ranges_partial_merge(self):
        import tempfile, json, gt7_db, gt7_tuner
        sample_cars = [{
            'id': '3614', 'name': "Ferrari F355 Berlinetta '94",
            'drivetrain': 'MR', 'mass_kg': 1350, 'balance': {'front_pct': 42}
        }]
        with tempfile.NamedTemporaryFile('w+', suffix='.json', delete=False) as tf:
            json.dump(sample_cars, tf)
            temp_path = tf.name
        try:
            gt7_db.save_car_sliders('3614', {'height_range': [85, 135]}, db_path=temp_path)
            merged = gt7_db.save_car_sliders('3614', {'df_front': [100, 200], 'df_rear': [200, 350]}, db_path=temp_path)
            self.assertEqual(merged['height_range'], [85, 135])
            self.assertEqual(merged['df_front'], [100, 200])

            with open(temp_path, 'r', encoding='utf-8') as f:
                saved_car = json.load(f)[0]
            setup = gt7_tuner.build_setup(car=saved_car)
            self.assertEqual(setup['parameters']['downforce']['range_f'], '100-200')
            self.assertEqual(setup['parameters']['ride_height_mm']['range'], '85-135')
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_closed_loop_trim_clamps_to_gt7_legal_bounds(self):
        import gt7_tuner
        car = {'id': '1', 'name': 'FF Hatch', 'drivetrain': 'FF', 'group': 'Road Car', 'mass_kg': 1100, 'balance': {'front_pct': 63}}
        setup = gt7_tuner.build_setup(
            car=car,
            stability=(-0.95, 0.85),
            symptoms=['entry_push', 'exit_snap', 'bottoming', 'curb_hop']
        )
        p = setup['parameters']
        self.assertGreaterEqual(p['anti_roll_bar']['front'], 1)
        self.assertLessEqual(p['anti_roll_bar']['rear'], 10)
        self.assertGreaterEqual(p['lsd_rear']['brake'], 5)
        self.assertLessEqual(p['lsd_rear']['brake'], 65)
        self.assertGreaterEqual(p['brake_bias'], 0)  # FF must never get negative rear brake bias

    def test_gr4_awd_preserves_fixed_split_under_symptom_trim(self):
        import gt7_tuner
        car = {'id': '2', 'name': 'WRX Gr.4', 'drivetrain': 'AWD', 'group': 'Gr.4', 'mass_kg': 1300, 'balance': {'front_pct': 56}}
        setup = gt7_tuner.build_setup(car=car, symptoms=['entry_push'])
        self.assertEqual(setup['parameters']['awd_torque_split'], 'Fixed (Homologation / ปรับไม่ได้ใน Gr.4)')

    def test_ff_lsd_routed_to_front_column(self):
        import gt7_tuner
        car = {'id': '3613', 'name': "Citroën 2 CV 6 Charleston '86", 'drivetrain': 'FF', 'group': 'Road Car', 'mass_kg': 585, 'balance': {'front_pct': 60}}
        setup = gt7_tuner.build_setup(car=car, custom_power=141)
        self.assertIsNotNone(setup['parameters']['lsd_front'])
        sheet = gt7_tuner.format_setup_sheet(setup)
        for line in sheet.splitlines():
            if 'LSD Initial Torque' in line:
                # Front column has numeric value, Rear column has '-'
                self.assertRegex(line, r'LSD Initial Torque\s+\d+\s+-')

    def test_group_x_normalization_and_x2019_preseeded_sliders(self):
        import gt7_db, gt7_tuner
        self.assertEqual(gt7_dynamics.normalize_group('X'), 'Gr.X')
        self.assertEqual(gt7_dynamics.normalize_group('B'), 'Gr.B')
        self.assertEqual(gt7_dynamics.normalize_group('N'), 'Road Car')

        x2019 = gt7_db.get_car('3374')
        setup = gt7_tuner.build_setup(car=x2019, tire='RM', mode='endurance')
        p = setup['parameters']
        self.assertTrue(45 <= p['ride_height_mm']['front'] <= 55)
        self.assertTrue(50 <= p['ride_height_mm']['rear'] <= 65)
        self.assertTrue(5.00 <= p['natural_frequency_hz']['front'] <= 5.30)
        self.assertTrue(5.30 <= p['natural_frequency_hz']['rear'] <= 5.55)
        self.assertTrue(800 <= p['downforce']['front'] <= 1200)
        self.assertTrue(1200 <= p['downforce']['rear'] <= 1600)

    def test_widebody_fender_clearance_clamped_to_slider_max(self):
        rh_std = gt7_dynamics.calculate_ride_height(wf=0.42, is_widebody=False)
        rh_wb = gt7_dynamics.calculate_ride_height(wf=0.42, is_widebody=True)
        self.assertEqual(rh_wb[0], rh_std[0] + 5)
        self.assertEqual(rh_wb[1] - rh_wb[0], rh_std[1] - rh_std[0])

        rh_clamped = gt7_dynamics.calculate_ride_height(
            wf=0.50, height_front_range=(90, 100), height_rear_range=(90, 105),
            elevation_diff_m=70.0, is_widebody=True
        )
        self.assertLessEqual(rh_clamped[0], 100)
        self.assertLessEqual(rh_clamped[1], 105)

    def test_endurance_aerodynamics_cp_and_fixed_front_clamp(self):
        # F355 (wf=0.42) with 50-200 / 100-250 in endurance mode -> 40% front (110) / 70% rear (205)
        df_f355 = gt7_dynamics.calculate_aerodynamics(
            df_front_range=(50, 200), df_rear_range=(100, 250),
            wf=0.42, group='Road Car', is_endurance=True
        )
        self.assertEqual((df_f355['front'], df_f355['rear']), (110, 205))

        # X2019 (wf=0.46) with 800-1200 / 1200-1600 in endurance mode -> 45% front (980) / 55% rear (1420)
        df_x2019 = gt7_dynamics.calculate_aerodynamics(
            df_front_range=(800, 1200), df_rear_range=(1200, 1600),
            wf=0.46, group='Gr.X', is_endurance=True
        )
        self.assertEqual((df_x2019['front'], df_x2019['rear']), (980, 1420))

        # Fixed front aero (200-200 / 400-500) must still clamp rear to floor (400) in endurance mode
        df_supra = gt7_dynamics.calculate_aerodynamics(
            df_front_range=(200, 200), df_rear_range=(400, 500),
            wf=0.53, group='Road Car', is_endurance=True
        )
        self.assertEqual((df_supra['front'], df_supra['rear']), (200, 400))

    def test_mr_endurance_alignment_and_maggiore_brake_bias(self):
        # F355 Full Tune (MR, wf=0.42, wr=0.58, 520 HP, RM ay_est=1.55) in endurance mode
        cam_f, cam_r, toe_f, toe_r = gt7_dynamics.calculate_wheel_alignment(
            ay_est=1.55, wf=0.42, wr=0.58, drivetrain='MR', power=520.0, is_endurance=True
        )
        self.assertEqual(cam_f, -2.2)
        self.assertEqual(cam_r, -1.2)
        self.assertEqual(toe_f, '0.00')
        self.assertEqual(toe_r, 'In 0.20')

        # X2019 (MR, wf=0.46, wr=0.54, 816 HP, RM ay_est=1.55) in endurance mode
        cam_f_x, cam_r_x, toe_f_x, toe_r_x = gt7_dynamics.calculate_wheel_alignment(
            ay_est=1.55, wf=0.46, wr=0.54, drivetrain='MR', power=816.0, is_endurance=True
        )
        self.assertEqual(cam_f_x, -2.2)
        self.assertEqual(cam_r_x, -1.2)
        self.assertEqual(toe_r_x, 'In 0.12')

        # Brake bias shifts -1 rearward on balanced/front-loaded endurance runs (wf >= 0.45) to save front tires
        bias_x, _ = gt7_dynamics.calculate_brake_bias(wf=0.46, hcg_m=0.32, wheelbase_m=2.95, drivetrain='MR', is_endurance=True)
        self.assertEqual(bias_x, -1)

    def test_damping_compression_clamped_to_40_pct_and_quick_trims_rendered(self):
        import gt7_tuner
        car = {'id': '3614', 'name': "Ferrari F355 Berlinetta '94", 'drivetrain': 'MR', 'group': 'Road Car', 'mass_kg': 1200, 'balance': {'front_pct': 42}}
        setup = gt7_tuner.build_setup(
            car=car, custom_power=520,
            symptoms=['bottoming', 'bottoming', 'bottoming', 'exit_snap', 'exit_snap']
        )
        p = setup['parameters']
        self.assertLessEqual(p['damping_compression_pct']['front'], 40)
        self.assertLessEqual(p['damping_compression_pct']['rear'], 40)
        self.assertIn('quick_trims', p)
        self.assertIn('tire_saver', p['quick_trims'])
        self.assertIn('max_stability', p['quick_trims'])

        sheet = gt7_tuner.format_setup_sheet(setup)
        self.assertIn('Tire-Saver Spec', sheet)
        self.assertIn('Max Stability Spec', sheet)

    def test_high_speed_trail_brake_compression_and_bottoming_guard(self):
        import gt7_tuner
        # Soft-sprung slammed widebody road car under 240 km/h trail-braking must trigger bottoming_or_fender_hit
        sim_slammed = gt7_dynamics.simulate_high_speed_trail_braking(
            speed_kmh=240.0, mass_kg=1350.0, corner_front_kg=250.0, corner_rear_kg=344.0,
            wf=0.42, hcg_m=0.42, wheelbase_m=2.45, track_width_m=1.62, mu=1.55,
            rh_front_mm=92, rh_rear_mm=100, fn_front_hz=2.00, fn_rear_hz=2.20,
            arb_front=3, arb_rear=6, df_front=180, df_rear=240,
            is_widebody=True, height_min_front_mm=90
        )
        self.assertTrue(sim_slammed['bottoming_or_fender_hit'])
        self.assertGreater(sim_slammed['total_outside_front_compression_mm'], 25.0)
        self.assertGreater(sim_slammed['recommended_front_rh_bump_mm'], 0)

        # Properly tuned F355 (105/113 mm, 2.50/2.70 Hz, ARB 5/5) at 200 km/h must clear fender & road safely
        car = {'id': '3614', 'name': "Ferrari F355 Berlinetta '94", 'drivetrain': 'MR', 'group': 'Road Car', 'mass_kg': 1200, 'balance': {'front_pct': 42}, 'dimensions_mm': {'length': 4250, 'width': 1900, 'height': 1170}}
        setup = gt7_tuner.build_setup(car=car, tire='RM', mode='endurance', is_widebody=True, speed_kmh=200.0)
        self.assertIn('high_speed_simulation', setup['telemetry'])
        self.assertFalse(setup['telemetry']['high_speed_simulation']['bottoming_or_fender_hit'])

if __name__ == '__main__':
    unittest.main()
