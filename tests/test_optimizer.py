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

    def test_trims_brake_bias_direction(self):
        from lib.trims import _apply_corner_symptom, _apply_stability_trims
        # Understeer entry push should shift bias rearward (+1 in GT7)
        params = {'anti_roll_bar': {'front': 5, 'rear': 5}, 'ride_height_mm': {'rear': 100}, 'brake_bias': 0}
        _apply_corner_symptom(params, 'entry_push', drivetrain='FR')
        self.assertEqual(params['brake_bias'], 1)

        # Twitchy high-speed stability should shift bias forward (<= 1 in GT7)
        params2 = {'anti_roll_bar': {'front': 5, 'rear': 5}, 'damping_expansion_pct': {'rear': 45}, 'brake_bias': 2}
        _apply_stability_trims(params2, stability=(0.0, 0.25), drivetrain='FR')
        self.assertLessEqual(params2['brake_bias'], 1)

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
        # max_grip maximizes G; min_tire_wear's score (-wear) is DF-agnostic,
        # so its winner may match max_grip's downforce (equal G) — it may not
        # exceed it.
        self.assertGreaterEqual(res_grip.g_prediction['g_240'], res_wear.g_prediction['g_240'])
        # Grid semantics: max_grip does not penalize wear, so its winner can tie
        # min_tire_wear on wear (both may pick the soft-fn/neutral-camber setup).
        # Invariant: min_tire_wear winner never wears MORE than max_grip winner.
        self.assertLessEqual(
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
        import copy as _copy
        dirt_params = _copy.deepcopy(self.params)
        dirt_params['camber_deg']['front'] = 0.0
        dirt_params['camber_deg']['rear'] = 0.0
        req_dirt = SolverRequest(
            veh=self.veh, trk=trk_dirt, baseline_params=dirt_params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='max_grip', speed_kmh=160.0
        )
        res = solve_optimal_setup(req_dirt)
        self.assertEqual(res.parameters['camber_deg']['front'], 0.0)
        self.assertEqual(res.parameters['camber_deg']['rear'], 0.0)


    def test_span_parameter_exposes_downforce_axis(self):
        """Span 0.90 must push more downforce than span 0.40 and raise G."""
        from lib.optimizer import _optimize_downforce, predict_g_at_downforce
        import copy as _copy
        p_hi = _copy.deepcopy(self.params)
        p_lo = _copy.deepcopy(self.params)
        req_hi = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=p_hi,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='balanced', speed_kmh=240.0
        )
        req_lo = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=p_lo,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='balanced', speed_kmh=240.0
        )
        _optimize_downforce(req_hi, p_hi, span=0.90)
        _optimize_downforce(req_lo, p_lo, span=0.40)
        self.assertGreater(p_hi['downforce']['rear'], p_lo['downforce']['rear'])
        g_hi = predict_g_at_downforce(self.g_model, (p_hi['downforce']['front'], p_hi['downforce']['rear']))
        g_lo = predict_g_at_downforce(self.g_model, (p_lo['downforce']['front'], p_lo['downforce']['rear']))
        self.assertGreater(g_hi['g_240'], g_lo['g_240'])


    def test_grid_score_meets_or_beats_baseline_heuristic(self):
        """The grid contains the old single-heuristic candidate (span 0.65, fn 0.0,
        camber (0,0)); best-of-grid must score at least as well."""
        import copy as _copy
        from lib.optimizer import (
            _optimize_downforce, _optimize_frequencies, _optimize_ride_heights,
            _evaluate, _resolve_height_bounds
        )
        req = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='balanced', speed_kmh=240.0
        )
        res = solve_optimal_setup(req)
        base_params = _copy.deepcopy(self.params)
        _optimize_downforce(req, base_params, span=0.65)
        _optimize_frequencies(req, base_params, delta=0.0)
        bounds = _resolve_height_bounds(req)
        sim = _optimize_ride_heights(req, base_params, bounds)
        base = _evaluate(req, base_params, sim, bounds)
        self.assertGreaterEqual(res.objective_score, base.objective_score - 1e-9)

    def test_grid_all_locked_axes_preserves_baseline_values(self):
        """With all three axes locked the grid collapses to the baseline path."""
        df_f, df_r = self.params['downforce']['front'], self.params['downforce']['rear']
        fn_f = self.params['natural_frequency_hz']['front']
        cam_f = self.params['camber_deg']['front']
        req = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='max_grip',
            locked_params=('downforce', 'natural_frequency_hz', 'camber_deg'),
            speed_kmh=240.0
        )
        res = solve_optimal_setup(req)
        self.assertEqual(res.parameters['downforce']['front'], df_f)
        self.assertEqual(res.parameters['downforce']['rear'], df_r)
        self.assertEqual(res.parameters['natural_frequency_hz']['front'], fn_f)
        self.assertEqual(res.parameters['camber_deg']['front'], cam_f)


    def test_refine_never_degrades_score_and_stays_feasible(self):
        """Refinement is a non-degrading improvement gate: disabling it must give
        a score <= the full solver's score, and both must be feasible."""
        import copy as _copy
        from lib import optimizer
        req = SolverRequest(
            veh=self.veh, trk=self.trk, baseline_params=self.params,
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='balanced', speed_kmh=240.0
        )
        res_full = solve_optimal_setup(req)
        original_refine = optimizer._refine
        optimizer._refine = lambda *a, **k: None
        try:
            res_grid = solve_optimal_setup(SolverRequest(
                veh=self.veh, trk=self.trk,
                baseline_params=_copy.deepcopy(self.params),
                telem=self.telem, sliders=self.sliders, g_model=self.g_model,
                objective='balanced', speed_kmh=240.0
            ))
        finally:
            optimizer._refine = original_refine
        self.assertGreaterEqual(res_full.objective_score, res_grid.objective_score - 1e-9)
        self.assertFalse(res_full.trail_simulation['bottoming_or_fender_hit'])
        self.assertFalse(res_grid.trail_simulation['bottoming_or_fender_hit'])


    def test_score_penalizes_sub_1x_grip_margin(self):
        """Objective score must penalize candidates whose tire margin < 1.0x."""
        import unittest.mock as mock
        from lib import optimizer
        from lib.optimizer import _calculate_score
        score_ok = _calculate_score('balanced', 1.8, 1.2, 1.35)

        def _low_margin(*a, **k):
            return {'margins': {'min': 0.85}, 'status': 'warn'}

        with mock.patch.object(optimizer, 'calculate_grip_check', side_effect=_low_margin):
            req = SolverRequest(
                veh=self.veh, trk=self.trk, baseline_params=self.params,
                telem=self.telem, sliders=self.sliders, g_model=self.g_model,
                objective='balanced', speed_kmh=240.0
            )
            res = solve_optimal_setup(req)
        score_low = _calculate_score('balanced', 1.8, 1.2, 0.85)
        self.assertLess(score_low, score_ok)
        self.assertEqual(res.grip_check['margins']['min'], 0.85)


if __name__ == '__main__':
    unittest.main()
