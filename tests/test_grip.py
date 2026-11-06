import unittest
from types import SimpleNamespace
from lib.grip import calculate_grip_check


def _veh(wf=0.60, mass=1350.0, is_race=False):
    return SimpleNamespace(
        mass_kg=mass, front_weight_ratio=wf, hcg_m=0.468,
        track_width_m=1.53, wheelbase_m=2.61, is_racecar=is_race
    )


class TestGripCheck(unittest.TestCase):
    def test_front_heavy_saturates_front_understeer(self):
        gc = calculate_grip_check(_veh(wf=0.60), 1.35, 1.0, 0.45)
        self.assertEqual(gc['handling_balance'], 'understeer')
        self.assertLess(gc['margins']['front'], gc['margins']['rear'])
        self.assertEqual(gc['saturation'], 'front')
        self.assertEqual(gc['status'], 'pass')
        self.assertGreater(gc['understeer_gradient'], 0.005)

    def test_rear_heavy_oversteer(self):
        gc = calculate_grip_check(_veh(wf=0.35), 1.35, 1.0, 0.50)
        self.assertEqual(gc['handling_balance'], 'oversteer')
        self.assertLess(gc['understeer_gradient'], -0.003)

    def test_beyond_limit_warns(self):
        gc = calculate_grip_check(_veh(wf=0.50), 1.35, 2.0, 0.50, mu_is_measured=True)
        self.assertEqual(gc['status'], 'warn')
        self.assertLess(gc['margins']['min'], 1.0)

    def test_uncalibrated_sublimit_is_info_not_warn(self):
        # Without a measured anchor there is no independent tire data; a
        # sub-limit estimate is reference info, not a warning.
        gc = calculate_grip_check(_veh(wf=0.50), 1.55, 1.84, 0.50, aero_g=0.29)
        self.assertEqual(gc['status'], 'info')
        self.assertLess(gc['margins']['min'], 1.0)

    def test_corner_loads_split_around_static(self):
        gc = calculate_grip_check(_veh(wf=0.55), 1.35, 1.0, 0.45)
        fz = gc['corner_fz_n']
        static_f = gc['static_load_n']['front'] / 2.0
        self.assertGreater(fz['front_outside'], static_f)
        self.assertLess(fz['front_inside'], static_f)
        self.assertGreater(fz['front_outside'], fz['front_inside'])
        # total front Fz conserves static load
        self.assertAlmostEqual(fz['front_outside'] + fz['front_inside'], gc['static_load_n']['front'], delta=5)

    def test_racecar_stiffer_cornering_stiffness(self):
        road = calculate_grip_check(_veh(wf=0.35, is_race=False), 1.55, 1.0, 0.50)
        race = calculate_grip_check(_veh(wf=0.35, is_race=True), 1.55, 1.0, 0.50)
        self.assertGreater(race['understeer_gradient'], road['understeer_gradient'])

    def test_aero_share_relieves_friction_demand(self):
        # Calibrated aero car (MR2-like): 1.38G total at 240 km/h, of which
        # ~0.34G is carried by downforce. The tire friction only has to carry
        # the 1.04G anchor, so the SS map (1.35) has real headroom.
        with_aero = calculate_grip_check(_veh(wf=0.42, mass=1289.0), 1.35, 1.38, 0.45, aero_g=0.34)
        without_aero = calculate_grip_check(_veh(wf=0.42, mass=1289.0), 1.35, 1.38, 0.45)
        self.assertAlmostEqual(with_aero['ay_fric_g'], 1.04, places=2)
        self.assertEqual(with_aero['status'], 'pass')
        self.assertGreater(with_aero['margins']['min'], without_aero['margins']['min'])
        self.assertGreater(with_aero['margins']['min'], 1.2)

    def test_friction_exceeding_map_still_warns(self):
        # Pure-friction demand above the measured anchor: downforce doesn't
        # excuse it.
        gc = calculate_grip_check(_veh(wf=0.50), 1.35, 1.47, 0.50, aero_g=0.0,
                                  mu_is_measured=True)
        self.assertEqual(gc['status'], 'warn')
        self.assertAlmostEqual(gc['ay_fric_g'], 1.47, places=2)

    def test_negative_aero_g_clamped(self):
        clamped = calculate_grip_check(_veh(wf=0.50), 1.35, 1.38, 0.50, aero_g=-0.5)
        zero = calculate_grip_check(_veh(wf=0.50), 1.35, 1.38, 0.50)
        self.assertEqual(clamped['margins'], zero['margins'])
        self.assertEqual(clamped['aero_g'], 0.0)

    def test_measured_anchor_skips_load_sensitivity(self):
        # Calibrated anchor: measured G60 already reflects loaded-tire behavior,
        # so a setup whose friction demand equals the anchor is in-limit
        # (no spurious 5-10% sensitivity haircut on every calibrated car).
        gc = calculate_grip_check(_veh(wf=0.42, mass=1289.0), 1.04, 1.38, 0.45,
                                  aero_g=0.34, mu_is_measured=True)
        self.assertAlmostEqual(gc['margins']['min'], 1.0, places=2)
        self.assertEqual(gc['status'], 'pass')


if __name__ == '__main__':
    unittest.main()