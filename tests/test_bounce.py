#!/usr/bin/env python3
"""Kangarooing (wheel hop / body bounce) simulator tests."""
import unittest
from types import SimpleNamespace

from lib.bounce import bounce_report, bounce_risk
from lib.grip import calculate_grip_check
from sheet_formatter import _format_bounce_check_lines


def _veh(wf=0.55, mass=1500.0):
    return SimpleNamespace(mass_kg=mass, front_weight_ratio=wf, hcg_m=0.468,
                           track_width_m=1.53, wheelbase_m=2.61, is_racecar=False)


def _track(bumpiness='medium', is_dirt=False, elev=0.0):
    return SimpleNamespace(bumpiness=bumpiness, is_dirt=is_dirt,
                           elevation_diff_m=elev)


def _params(fn_f=1.4, fn_r=1.5, comp=50, exp=50, rh_f=100, rh_r=110):
    return {
        'natural_frequency_hz': {'front': fn_f, 'rear': fn_r},
        'damping_compression_pct': {'front': comp, 'rear': comp},
        'damping_expansion_pct': {'front': exp, 'rear': exp},
        'ride_height_mm': {'front': rh_f, 'rear': rh_r},
    }


class TestBounceReport(unittest.TestCase):
    def test_stiff_fast_dampers_hop_on_extreme_road(self):
        veh, trk = _veh(), _track(bumpiness='extreme')
        stiff = bounce_report(veh, trk, _params(fn_f=2.2, fn_r=2.4, comp=8, exp=8), 1.2)
        soft = bounce_report(veh, trk, _params(fn_f=1.2, fn_r=1.3, comp=80, exp=80), 1.2)
        self.assertGreater(stiff['scenarios']['rough_road']['hop_ms'], 0)
        self.assertGreater(stiff['index'], soft['index'])
        self.assertGreaterEqual(stiff['scenarios']['rough_road']['hop_ms'],
                                soft['scenarios']['rough_road']['hop_ms'])

    def test_smooth_track_no_bounce(self):
        veh, trk = _veh(), _track(bumpiness='low')
        rep = bounce_report(veh, trk, _params(fn_f=2.0, fn_r=2.1, comp=15, exp=15), 1.2)
        self.assertEqual(rep['scenarios']['rough_road']['hop_ms'], 0)
        self.assertEqual(rep['scenarios']['rough_road']['status'], 'pass')

    def test_cornering_inside_wheel_unload(self):
        veh = _veh(wf=0.65)
        trk = _track(bumpiness='medium')
        rep = bounce_report(veh, trk, _params(comp=30, exp=30), 1.6, lltd_frac=0.45)
        co = rep['scenarios']['cornering']
        # Front-heavy car: rear inside wheel is the most unloaded corner.
        self.assertLess(co['inside_fz_pct']['front'], 70)
        self.assertLess(co['inside_fz_pct']['rear'], co['inside_fz_pct']['front'])
        self.assertGreater(co['ay_g'], 1.0)

    def test_landing_scenario_on_mountain_track(self):
        # Fishermans Ranch: 145 m elevation -> h_eff 0.48 m -> v ~3.1 m/s
        rep = bounce_report(_veh(), _track(elev=145.0), _params(), 1.2)
        ld = rep['scenarios']['landing']
        self.assertIsNotNone(ld)
        self.assertGreater(ld['impact_v_ms'], 2.0)
        self.assertIn(ld['status'], ('pass', 'warn'))

    def test_landing_soft_bottoms_more_than_stiff(self):
        trk = _track(elev=145.0)
        stiff = bounce_report(_veh(), trk, _params(fn_f=2.2, fn_r=2.3,
                                                   comp=8, exp=8), 1.2)
        soft = bounce_report(_veh(), trk, _params(fn_f=1.2, fn_r=1.3,
                                                  comp=80, exp=80), 1.2)
        # Soft springs sink deep into travel on the landing impact;
        # stiff springs resist and bounce instead.
        self.assertGreater(soft['scenarios']['landing']['bottom_pct'],
                           stiff['scenarios']['landing']['bottom_pct'])

    def test_landing_skipped_on_flat_track(self):
        rep = bounce_report(_veh(), _track(elev=0.0), _params(), 1.2)
        self.assertIsNone(rep['scenarios']['landing'])

    def test_dirt_surface_pumps_body_more_than_tarmac(self):
        # On dirt, surface compliance filters the high-frequency wheel-hop
        # band, but low-frequency gravel undulation pumps the body: a soft
        # damped setup stays clean on tarmac yet pumps hard on dirt.
        veh = _veh()
        soft = _params(fn_f=1.2, fn_r=1.3, comp=80, exp=80)
        dirt = bounce_report(veh, _track(bumpiness='extreme', is_dirt=True), soft, 1.2)
        tarmac = bounce_report(veh, _track(bumpiness='extreme', is_dirt=False), soft, 1.2)
        self.assertTrue(dirt['is_dirt'])
        self.assertGreater(dirt['scenarios']['rough_road']['bounce_amp_mm'],
                           tarmac['scenarios']['rough_road']['bounce_amp_mm'])
        # And surface compliance reduces pure wheel hop on the same stiff setup.
        stiff = _params(fn_f=2.2, fn_r=2.3, comp=8, exp=8)
        dirt_s = bounce_report(veh, _track(bumpiness='extreme', is_dirt=True), stiff, 1.2)
        tarmac_s = bounce_report(veh, _track(bumpiness='extreme', is_dirt=False), stiff, 1.2)
        self.assertLessEqual(dirt_s['scenarios']['cornering']['hop_ms'],
                             tarmac_s['scenarios']['cornering']['hop_ms'])

    def test_index_bounded_and_level_consistent(self):
        rep = bounce_report(_veh(), _track(bumpiness='extreme', is_dirt=True, elev=145.0),
                            _params(fn_f=2.4, fn_r=2.6, comp=5, exp=5), 1.6)
        self.assertTrue(0 <= rep['index'] <= 100)
        self.assertIn(rep['level'], ('low', 'moderate', 'high'))
        self.assertEqual(rep['level'] == 'low', rep['index'] < 30)


class TestBounceRiskGate(unittest.TestCase):
    def _grip(self, wf=0.70):
        return calculate_grip_check(_veh(wf=wf), 1.35, 1.8, 0.50)

    def test_underdamped_with_unloaded_inside_wheel_is_risky(self):
        self.assertTrue(bounce_risk(_veh(wf=0.70), _track(bumpiness='medium'),
                                    _params(comp=20, exp=20), self._grip()))

    def test_well_damped_is_not_risky(self):
        self.assertFalse(bounce_risk(_veh(wf=0.70), _track(bumpiness='medium'),
                                     _params(comp=100, exp=100), self._grip()))

    def test_smooth_track_is_never_risky(self):
        self.assertFalse(bounce_risk(_veh(wf=0.70), _track(bumpiness='low'),
                                     _params(comp=10, exp=10), self._grip()))


class TestBounceSheetLines(unittest.TestCase):
    def test_lines_render_all_scenarios_and_advice(self):
        rep = bounce_report(_veh(), _track(bumpiness='extreme', is_dirt=True, elev=145.0),
                            _params(fn_f=2.3, fn_r=2.5, comp=8, exp=8), 1.5)
        lines = _format_bounce_check_lines(rep)
        text = '\n'.join(lines)
        self.assertIn('Kangarooing', text)
        self.assertIn('Rough Road', text)
        self.assertIn('Hard Corner', text)
        self.assertIn('Crest Landing', text)
        self.assertIn('Dirt surface', text)
        self.assertIn(f"{rep['index']}/100", text)
        if rep['level'] != 'low':
            self.assertIn('soften springs', text)

    def test_flat_track_landing_line_says_skipped(self):
        rep = bounce_report(_veh(), _track(bumpiness='low'), _params(), 1.2)
        text = '\n'.join(_format_bounce_check_lines(rep))
        self.assertIn('สนามเรียบ', text)


if __name__ == '__main__':
    unittest.main()