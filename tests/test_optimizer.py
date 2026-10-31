import unittest
from models import VehicleSpec, TrackSpec
from setup_engine import resolve_slider_ranges, compute_baseline_suspension
from lib.calibrator import GForceCalibrationInput, calibrate_g_model
from lib.optimizer import SolverRequest, solve_optimal_setup


class TestReverseOptimizer(unittest.TestCase):
    def setUp(self):
        car = {
            'id': '3466', 'name': "Ford Sierra RS 500 Cosworth '87",
            'drivetrain': 'FR', 'mass_kg': 989, 'power_hp': 359, 'torque_nm': 368.9,
            'balance': {'front_pct': 56, 'rear_pct': 44}
        }
        explicit = {
            'df_front': (50, 200), 'df_rear': (100, 250),
            'height_front': (100, 200), 'height_rear': (120, 220),
            'fn_front': (1.50, 3.50), 'fn_rear': (1.50, 3.50),
            'height_range': None
        }
        self.sliders = resolve_slider_ranges(car, explicit)
        self.veh = VehicleSpec.from_dict(car, custom_overrides={}, is_widebody=True)
        self.trk = TrackSpec.from_dict(None, mode='endurance', tire='RM')
        self.params, self.telem = compute_baseline_suspension(
            self.veh, self.trk, 'RM', self.sliders, True, False
        )
        self.g_model = calibrate_g_model(GForceCalibrationInput(
            measured_g=(1.46, 1.59, 1.75), ref_downforce=(110, 100),
            base_mu=1.55, front_weight_ratio=0.56, mass_kg=989.0
        ))

    def test_solver_eliminates_bottoming_and_preserves_rake(self):
        # Force an unsafe low front height in baseline to verify solver fixes it
        self.params['ride_height_mm']['front'] = 105
        req = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='balanced', speed_kmh=240.0
        )
        res = solve_optimal_setup(req)
        self.assertFalse(res.trail_simulation['bottoming_or_fender_hit'])
        self.assertGreaterEqual(res.trail_simulation['dynamic_outside_front_clearance_mm'], 10.0)
        rh = res.parameters['ride_height_mm']
        self.assertGreater(rh['rear'], rh['front'])

    def test_max_grip_vs_min_tire_wear_objectives(self):
        req_grip = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='max_grip', speed_kmh=240.0
        )
        req_wear = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='min_tire_wear', speed_kmh=240.0
        )
        res_grip = solve_optimal_setup(req_grip)
        res_wear = solve_optimal_setup(req_wear)
        self.assertGreater(res_grip.g_prediction['g_240'], res_wear.g_prediction['g_240'])
        self.assertLess(
            res_wear.tire_wear['front_wear_factor'],
            res_grip.tire_wear['front_wear_factor']
        )

    def test_locked_parameters_remain_untouched(self):
        self.params['downforce']['front'] = 110
        self.params['downforce']['rear'] = 155
        req = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='max_grip', locked_params=('downforce',), speed_kmh=240.0
        )
        res = solve_optimal_setup(req)
        self.assertEqual(res.parameters['downforce']['front'], 110)
        self.assertEqual(res.parameters['downforce']['rear'], 155)

    def test_racecar_bounds_prevent_ride_height_jacking(self):
        car = {'name': 'Porsche 911 RSR Gr.3', 'mass_kg': 1243, 'drivetrain': 'MR', 'power_hp': 510, 'torque_nm': 500, 'group': 'Gr.3'}
        veh = VehicleSpec.from_dict(car, custom_overrides={}, is_widebody=False)
        sliders = resolve_slider_ranges(car, {})
        params, telem = compute_baseline_suspension(veh, self.trk, 'RM', sliders, False, False)
        req = SolverRequest(
            veh=veh, trk=self.trk, baseline_params=params,
            telem=telem, sliders=sliders, g_model=self.g_model,
            objective='balanced', speed_kmh=240.0
        )
        res = solve_optimal_setup(req)
        rh = res.parameters['ride_height_mm']
        self.assertLessEqual(rh['front'], 85)
        self.assertLessEqual(rh['rear'], 95)
        self.assertGreater(rh['rear'], rh['front'])

    def test_dirt_camber_preserved_under_solver(self):
        trk_dirt = TrackSpec.from_dict(None, mode='dirt', tire='Dirt')
        req_dirt = SolverRequest(
            veh=self.veh, trk=trk_dirt, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='max_grip', speed_kmh=160.0
        )
        self.params['camber_deg']['front'] = 0.0
        self.params['camber_deg']['rear'] = 0.0
        res = solve_optimal_setup(req_dirt)
        self.assertEqual(res.parameters['camber_deg']['front'], 0.0)
        self.assertEqual(res.parameters['camber_deg']['rear'], 0.0)


if __name__ == '__main__':
    unittest.main()
