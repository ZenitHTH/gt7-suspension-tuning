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
        gc = calculate_grip_check(_veh(wf=0.50), 1.35, 2.0, 0.50)
        self.assertEqual(gc['status'], 'warn')
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


if __name__ == '__main__':
    unittest.main()