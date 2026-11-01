import unittest
from db import get_car, get_track
from setup import build_setup


class TestBenchmarkValidation(unittest.TestCase):
    def test_genesis_g70_gr4_awd_benchmark(self):
        # Genesis G70 AWD at Red Bull Ring should yield bias in [-1, 0]
        car = get_car("Genesis G70") or {
            'name': 'Genesis G70 Gr.4', 'mass_kg': 1350, 'drivetrain': 'AWD',
            'group': 'Gr.4', 'balance': {'front_pct': 53, 'rear_pct': 47}
        }
        track = get_track("Red Bull Ring")
        res = build_setup(car=car, track=track, tire='RM', mode='grip')
        bias = res['parameters']['brake_bias']
        self.assertIn(bias, [-1, 0])

    def test_amg_gt3_fr_wheel_vs_controller_benchmark(self):
        # Front-heavy FR car (Mustang Gr.3: 54:46)
        car_mustang = get_car("Ford Mustang Gr.3") or {
            'name': 'Ford Mustang Gr.3', 'mass_kg': 1350, 'drivetrain': 'FR',
            'group': 'Gr.3', 'balance': {'front_pct': 54, 'rear_pct': 46}
        }
        track = get_track("Red Bull Ring")
        wheel_setup = build_setup(car=car_mustang, track=track, tire='RM', is_controller=False)
        self.assertGreaterEqual(wheel_setup['parameters']['brake_bias'], 1)

        pad_setup = build_setup(car=car_mustang, track=track, tire='RM', is_controller=True)
        self.assertLessEqual(pad_setup['parameters']['brake_bias'], 1)
        self.assertGreaterEqual(pad_setup['parameters']['lsd_rear']['brake'], 80)

        # Balanced/rear-biased FR car (AMG SLS GT3: 48:52) in endurance mode (Nurburgring)
        # must remain neutral (0) and not bump to rear bias
        car_amg = get_car("AMG GT3")
        track_endur = get_track("Nurburgring")
        amg_setup = build_setup(car=car_amg, track=track_endur, tire='RM', is_controller=False)
        self.assertEqual(amg_setup['parameters']['brake_bias'], 0)

    def test_alpine_a110_mr_benchmark(self):
        # Alpine A110 MR at Alsace
        car = get_car("Alpine A110") or {
            'name': 'Alpine A110', 'mass_kg': 1100, 'drivetrain': 'MR',
            'group': 'Road Car', 'balance': {'front_pct': 44, 'rear_pct': 56}
        }
        track = get_track("Alsace")
        res = build_setup(car=car, track=track, tire='SM')
        bias = res['parameters']['brake_bias']
        self.assertLessEqual(bias, 0)

    def test_mr_awd_and_controller_closed_loop_trim_safety_clamps(self):
        alpine = get_car("Alpine A110")
        track_alsace = get_track("Alsace")
        alpine_setup = build_setup(car=alpine, track=track_alsace, tire='SM', symptoms=['entry_push', 'entry_push'])
        self.assertLessEqual(alpine_setup['parameters']['brake_bias'], 0)

        g70 = get_car("Genesis G70")
        track_rbr = get_track("Red Bull Ring")
        g70_setup = build_setup(car=g70, track=track_rbr, tire='RM', symptoms=['entry_push', 'entry_push'])
        self.assertLessEqual(g70_setup['parameters']['brake_bias'], 0)

        mustang = get_car("Ford Mustang Gr.3")
        pad_setup = build_setup(car=mustang, track=track_rbr, tire='RM', is_controller=True, symptoms=['entry_push'])
        self.assertLessEqual(pad_setup['parameters']['brake_bias'], 1)

    def test_controller_notes_no_conflicting_lsd_recommendation(self):
        car = get_car("Ford Mustang Mach 1")
        track = get_track("Alsace")
        pad_setup = build_setup(car=car, track=track, tire='CS', is_controller=True)
        pad_notes = pad_setup['parameters']['endurance_notes']
        self.assertFalse(any("[Anti-Understeer]" in n and "22-26" in n for n in pad_notes))

        wheel_setup = build_setup(car=car, track=track, tire='CS', is_controller=False)
        wheel_notes = wheel_setup['parameters']['endurance_notes']
        self.assertTrue(any("[Anti-Understeer]" in n and "22-26" in n for n in wheel_notes))
