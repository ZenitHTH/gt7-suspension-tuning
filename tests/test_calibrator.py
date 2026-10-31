import unittest
from lib.calibrator import (
    GForceCalibrationInput,
    calibrate_g_model,
    predict_g_at_downforce,
    build_df_g_profile
)


class TestGForceCalibrator(unittest.TestCase):
    def test_calibrate_from_measured_sierra_telemetry(self):
        cfg = GForceCalibrationInput(
            measured_g=(1.46, 1.59, 1.75),
            ref_downforce=(110, 100),
            base_mu=1.55,
            front_weight_ratio=0.56,
            mass_kg=989.0
        )
        model = calibrate_g_model(cfg)
        at_ref = predict_g_at_downforce(model, (110, 100))
        self.assertAlmostEqual(at_ref['g_60'], 1.46, places=2)
        self.assertAlmostEqual(at_ref['g_240'], 1.75, places=2)
        self.assertEqual(at_ref['downforce'], {'front': 110, 'rear': 100})
        self.assertIn('@ DF 110/100', at_ref['summary'])

        # Increasing downforce to 135/185 increases 240 km/h G more than 60 km/h G
        at_high = predict_g_at_downforce(model, (135, 185))
        self.assertGreater(at_high['g_240'], at_ref['g_240'] + 0.05)
        self.assertGreater(
            at_high['g_240'] - at_ref['g_240'],
            at_high['g_60'] - at_ref['g_60']
        )

    def test_zero_aero_and_unprovided_fallback(self):
        cfg = GForceCalibrationInput(base_mu=1.35, front_weight_ratio=0.52, mass_kg=1200.0)
        model = calibrate_g_model(cfg)
        pred = predict_g_at_downforce(model, (0, 0))
        self.assertAlmostEqual(pred['g_60'], pred['g_240'], places=2)
        self.assertIn('@ DF 0/0', pred['summary'])

    def test_cp_imbalance_penalty_reduces_effective_g(self):
        cfg = GForceCalibrationInput(
            measured_g=(1.45, 1.58, 1.75),
            ref_downforce=(120, 180),
            front_weight_ratio=0.56,
            mass_kg=989.0
        )
        model = calibrate_g_model(cfg)
        # Same total downforce (300), but balanced (120/180) vs inverted front-heavy (200/100)
        g_balanced = predict_g_at_downforce(model, (120, 180))
        g_inverted = predict_g_at_downforce(model, (200, 100))
        self.assertGreater(g_balanced['g_240'], g_inverted['g_240'])

    def test_build_df_g_profile_returns_min_active_max(self):
        cfg = GForceCalibrationInput(
            measured_g=(1.46, 1.59, 1.75),
            ref_downforce=(110, 100),
            front_weight_ratio=0.56,
            mass_kg=989.0
        )
        model = calibrate_g_model(cfg)
        profile = build_df_g_profile(model, ((50, 200), (100, 250)), (118, 190))
        self.assertEqual(profile['active']['downforce'], {'front': 118, 'rear': 190})
        self.assertLess(profile['min_aero']['g_240'], profile['active']['g_240'])
        self.assertLess(profile['active']['g_240'], profile['max_aero']['g_240'])


if __name__ == '__main__':
    unittest.main()
