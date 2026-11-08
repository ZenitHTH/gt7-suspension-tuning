#!/usr/bin/env python3
"""
GT7 Kangarooing Simulator (wheel hop / sustained body bounce)
Quarter-car 2-DOF model per corner (sprung body + unsprung wheel), RK4.
Three in-game scenarios:
  1. Rough road   — track `bumpiness` amplitude at corner speed (Baku-type)
  2. Hard corner  — sustained lateral G, inside wheels lose load
  3. Crest landing— elevation-driven landing impact (mountain/dirt circuits,
                    e.g. Fishermans Ranch 145 m, Sardegna Windmills dirt)
Dirt circuits (`trk.is_dirt`) halve effective tire stiffness (soft surface
compliance) in all scenarios.
Calibration constant: ZETA_AT_FULL_DAMPING maps the GT7 damper % (100) to a
damping ratio; calibrate once vs in-game body-bounce feel, same method as
the G calibration.
"""

import math
from typing import Any, Dict, Optional

G = 9.81
ZETA_AT_FULL_DAMPING = 0.60   # GT7 100% damper % -> damping ratio (calibrate)
BUMPINESS_AMPLITUDE_M = {'low': 0.002, 'medium': 0.006,
                         'high': 0.010, 'extreme': 0.015}
DIRT_TIRE_STIFFNESS_FACTOR = 0.5
UNSPRUNGED_MASS_RATIO = 8.0   # m_u = m_s / 8 (~12% unsprung, lower bound 15 kg)
TIRE_STIFFNESS_N_PER_M = 2.5e5  # per tire at 1500 kg reference
DT = 0.001
SETTLE_S = 0.30               # ignore transients at scenario start


def _damping_zeta(params: Dict[str, Any], ax: str) -> float:
    """Effective damping ratio from GT7 compression/expansion damper %."""
    comp = params.get('damping_compression_pct', {}).get(ax, 50)
    exp = params.get('damping_expansion_pct', {}).get(ax, 50)
    return ZETA_AT_FULL_DAMPING * ((float(comp) + float(exp)) / 200.0)


def _quarter_car(veh: Any, ax: str, params: Dict[str, Any],
                 fz_static: float, is_dirt: bool) -> Dict[str, float]:
    """Per-corner model constants. fz_static: static tire load (N)."""
    wf = veh.front_weight_ratio if ax == 'front' else (1.0 - veh.front_weight_ratio)
    m_s = veh.mass_kg * wf / 2.0                      # per-corner sprung mass
    m_u = max(15.0, m_s / UNSPRUNGED_MASS_RATIO)
    f = float(params['natural_frequency_hz'][ax])
    k_s = (2.0 * math.pi * f) ** 2 * m_s
    k_t = TIRE_STIFFNESS_N_PER_M * (veh.mass_kg / 1500.0)
    if is_dirt:
        k_t *= DIRT_TIRE_STIFFNESS_FACTOR
    c_s = _damping_zeta(params, ax) * 2.0 * math.sqrt(k_s * m_s)
    return {'m_s': m_s, 'm_u': m_u, 'k_s': k_s, 'k_t': k_t, 'c_s': c_s,
            'zeta': _damping_zeta(params, ax), 'fz_static': fz_static}


def _accel(z_s: float, v_s: float, z_u: float, v_u: float,
           y_road: float, q: Dict[str, float]):
    f_spring = q['k_s'] * (z_s - z_u)
    f_damp = q['c_s'] * (v_s - v_u)
    # One-way tire: total tire force cannot go below zero (no pulling).
    # In the deviation frame that means f_tire >= -fz_static.
    f_tire = max(-q['fz_static'], q['k_t'] * (z_u - y_road))
    return ((-f_spring - f_damp) / q['m_s'],
            (f_spring + f_damp - f_tire) / q['m_u'])


def _integrate(qc: Dict[str, float], avail_m: float, y_road_fn,
               duration: float) -> Dict[str, float]:
    """RK4 over the quarter-car; road displacement via y_road_fn(t).
    Tires are one-way (they cannot pull): when the road rises past the
    wheel (landing impact), the wheel is clamped onto the road surface."""
    n = int(round(duration / DT))
    z_s = v_s = z_u = v_u = 0.0
    hop_s = 0.0
    peak_comp = 0.0
    zmin, zmax = 0.0, 0.0
    for i in range(n):
        t = i * DT
        y = y_road_fn(t)
        if t > SETTLE_S:
            f_tire_now = qc['k_t'] * (z_u - y)
            if qc['fz_static'] + f_tire_now <= 0.0:
                hop_s += DT
        comp = z_u - z_s
        if comp > peak_comp:
            peak_comp = comp
        zmin, zmax = min(zmin, z_s), max(zmax, z_s)

        def deriv(zs, vs, zu, vu, t_eval):
            as_, au = _accel(zs, vs, zu, vu, y_road_fn(t_eval), qc)
            return vs, as_, vu, au

        a1s, a1u = _accel(z_s, v_s, z_u, v_u, y_road_fn(t), qc)
        k1 = (v_s, a1s, v_u, a1u)
        k2 = deriv(z_s + DT / 2 * k1[0], v_s + DT / 2 * k1[1],
                   z_u + DT / 2 * k1[2], v_u + DT / 2 * k1[3], t + DT / 2.0)
        k3 = deriv(z_s + DT / 2 * k2[0], v_s + DT / 2 * k2[1],
                   z_u + DT / 2 * k2[2], v_u + DT / 2 * k2[3], t + DT / 2.0)
        k4 = deriv(z_s + DT * k3[0], v_s + DT * k3[1],
                   z_u + DT * k3[2], v_u + DT * k3[3], t + DT)
        z_s += DT / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        v_s += DT / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        z_u += DT / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        v_u += DT / 6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3])
    bottom_pct = max(0.0, (peak_comp - avail_m) / max(0.01, avail_m)) * 100.0
    return {'hop_ms': round(hop_s * 1000.0), 'bottom_pct': round(bottom_pct, 1),
            'bounce_amp_mm': round((zmax - zmin) / 2.0 * 1000.0, 1)}


def _rough_road(v_mps: float, amp_m: float, t: float, is_dirt: bool = False) -> float:
    """Two-scale road input: 4/9 m rumble (wheel-rate band, where wheel hop
    happens) plus, on dirt, 40/70 m gravel rumble at body rate — this is
    what makes a bumpy dirt track pump the body (surface compliance also
    filters the high-frequency rumble, reducing pure wheel hop)."""
    y = amp_m * (0.6 * math.sin(2 * math.pi * v_mps / 4.0 * t)
                 + 0.4 * math.sin(2 * math.pi * v_mps / 9.0 * t + 1.7))
    if is_dirt:
        y += amp_m * (0.5 * math.sin(2 * math.pi * v_mps / 40.0 * t + 0.6)
                      + 0.35 * math.sin(2 * math.pi * v_mps / 70.0 * t + 2.1))
    return y


def bounce_risk(veh: Any, trk: Any, params: Dict[str, Any],
                grip_check: Optional[Dict[str, Any]]) -> bool:
    """Cheap per-candidate gate (no time integration): underdamped + a
    cornering inside wheel carrying < 25% of its static load on a bumpy
    track = kangaroo-prone candidate."""
    if grip_check is None or (getattr(trk, 'bumpiness', 'low') or 'low') == 'low':
        return False
    if min(_damping_zeta(params, 'front'), _damping_zeta(params, 'rear')) >= 0.35:
        return False
    static = grip_check.get('static_load_n')
    fz = grip_check.get('corner_fz_n')
    if not static or not fz:
        return False  # load data unavailable: gate off, not an error
    return (fz['front_inside'] < 0.25 * static['front'] / 2.0
            or fz['rear_inside'] < 0.25 * static['rear'] / 2.0)


def bounce_report(veh: Any, trk: Any, params: Dict[str, Any], ay_g: float,
                  lltd_frac: float = 0.5) -> Dict[str, Any]:
    """Full kangaroo simulation of one setup on one track. All three
    scenarios, per corner, plus a 0-100 kangaroo index."""
    ay_g = max(0.05, float(ay_g))
    lltd_frac = min(1.0, max(0.0, float(lltd_frac)))
    is_dirt = bool(getattr(trk, 'is_dirt', False))
    bumpiness = getattr(trk, 'bumpiness', 'medium') or 'medium'
    elev = float(getattr(trk, 'elevation_diff_m', 0.0) or 0.0)
    speed_kmh = 180.0
    v_mps = speed_kmh / 3.6
    amp_m = BUMPINESS_AMPLITUDE_M.get(bumpiness, 0.006)

    m = veh.mass_kg
    wf = veh.front_weight_ratio
    fz_f = m * G * wf / 2.0
    fz_r = m * G * (1.0 - wf) / 2.0
    ay = ay_g * G
    total_transfer = m * ay * veh.hcg_m / max(1.0, veh.track_width_m)
    d_f = total_transfer * lltd_frac
    d_r = total_transfer - d_f

    def avail_m(ax: str) -> float:
        rh = params.get('ride_height_mm', {}).get(ax, 100)
        return max(0.04, rh / 1000.0)

    def road_fn(t: float) -> float:
        return _rough_road(v_mps, amp_m, t, is_dirt)

    # Scenario 1: rough road, per axle at static loads.
    s1 = {ax: _integrate(_quarter_car(veh, ax, params, fz_f if ax == 'front' else fz_r, is_dirt),
                         avail_m(ax), road_fn, 4.0) for ax in ('front', 'rear')}
    s1_hop = s1['front']['hop_ms'] + s1['rear']['hop_ms']
    s1_amp = max(s1['front']['bounce_amp_mm'], s1['rear']['bounce_amp_mm'])

    # Scenario 2: sustained corner — same road input, inside wheels unload.
    s2_f = _integrate(_quarter_car(veh, 'front', params, max(0.0, fz_f - d_f / 2.0), is_dirt),
                      avail_m('front'), road_fn, 4.0)
    s2_r = _integrate(_quarter_car(veh, 'rear', params, max(0.0, fz_r - d_r / 2.0), is_dirt),
                      avail_m('rear'), road_fn, 4.0)
    s2_hop = s2_f['hop_ms'] + s2_r['hop_ms']
    s2_bottom = max(s2_f['bottom_pct'], s2_r['bottom_pct'])
    inside_fz_pct = {
        'front': round(max(0.0, fz_f - d_f / 2.0) / max(1.0, fz_f) * 100.0),
        'rear': round(max(0.0, fz_r - d_r / 2.0) / max(1.0, fz_r) * 100.0)
    }

    # Scenario 3: crest-to-valley landing. Elevation-driven landing speed;
    # skipped on flat tracks (elev < 5 m).
    s3 = None
    if elev >= 5.0:
        h_eff = min(0.5, max(0.1, elev / 300.0))
        v_down = math.sqrt(2.0 * G * h_eff)

        def landing_road(t: float, v=v_down) -> float:
            # z is down-positive: the ground rising toward the wheel is a
            # negative displacement. Rise capped at 1 m (car lands, then
            # keeps driving on the flat).
            if t < 0.8:
                return 0.0
            return -min(v * (t - 0.8), 1.0)

        lf = _integrate(_quarter_car(veh, 'front', params, fz_f, is_dirt),
                        avail_m('front'), landing_road, 3.0)
        lr = _integrate(_quarter_car(veh, 'rear', params, fz_r, is_dirt),
                        avail_m('rear'), landing_road, 3.0)
        s3 = {'impact_v_ms': round(v_down, 2),
              'bottom_pct': round(max(lf['bottom_pct'], lr['bottom_pct']), 1)}

    # Log-scaled index: 0 = no bounce signature, 100 = constant wheel hop.
    # Base 10 for any warning scenario; each hop term saturates via log10.
    raw = 0.0
    if s1_hop > 0.0 or s2_hop > 0.0 or (s3 is not None and s3['bottom_pct'] > 10.0):
        raw = 10.0
    raw += 30.0 * min(1.0, math.log10(1.0 + s1_hop / 50.0) / 1.5)
    raw += 25.0 * min(1.0, math.log10(1.0 + s2_hop / 100.0) / 1.7)
    if s2_bottom > 10.0:
        raw += 10.0
    if s3 is not None:
        raw += 25.0 * min(1.0, s3['bottom_pct'] / 50.0)
    index = int(round(min(100.0, raw)))
    level = 'low' if index < 30 else ('moderate' if index < 60 else 'high')

    return {
        'speed_kmh': speed_kmh,
        'is_dirt': is_dirt,
        'bumpiness': bumpiness,
        'zeta': {'front': round(_damping_zeta(params, 'front'), 2),
                 'rear': round(_damping_zeta(params, 'rear'), 2)},
        'scenarios': {
            'rough_road': {'status': 'warn' if s1_hop > 0.0 else 'pass',
                           'hop_ms': s1_hop, 'bounce_amp_mm': s1_amp},
            'cornering': {'status': 'warn' if (s2_hop > 50.0 or s2_bottom > 10.0) else 'pass',
                          'ay_g': round(ay_g, 2), 'hop_ms': s2_hop,
                          'bottom_pct': s2_bottom, 'inside_fz_pct': inside_fz_pct},
            'landing': (None if s3 is None
                        else {'status': 'warn' if s3['bottom_pct'] > 10.0 else 'pass',
                              **s3})
        },
        'index': index,
        'level': level
    }