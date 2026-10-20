#!/usr/bin/env python3
"""
GT7 Race-Engineering Vehicle Dynamics Engine (Backward Compatibility Facade)
Re-exports calculations from the modular lib/ package:
- lib.formulas (primitives, wheel rate, load transfer)
- lib.springs (natural frequencies, anti-roll bars, flat ride)
- lib.shocks (dampers)
- lib.wheels (wheel alignment, tire grip, brake bias)
- lib.aero_body (ground clearance, downforce, trail-braking simulator)
- lib.drivetrain (LSD, transmission top speed)
- lib.trims (closed-loop trims, quick-trims)
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from constants import (
    TIRE_MU_MAP,
    SLIDER_BOUNDS,
    AERO_REFERENCE_SPEED_KMH,
    STROKE_CLEARANCE_FLOOR_MM,
    CHASSIS_RATIOS
)

from lib.formulas import (
    normalize_group,
    calculate_wheel_rate,
    calculate_sprung_mass,
    calculate_aerodynamic_heave,
    calculate_braking_pitch_dive,
    calculate_cornering_roll_deflection
)

from lib.springs import (
    calculate_natural_frequencies,
    calculate_anti_roll_bars
)

from lib.shocks import (
    calculate_dampers
)

from lib.wheels import (
    get_tire_mu,
    calculate_wheel_alignment,
    calculate_brake_bias
)

from lib.aero_body import (
    calculate_ride_height,
    calculate_aerodynamics,
    simulate_high_speed_trail_braking
)

from lib.drivetrain import (
    calculate_differential_lsd,
    calculate_top_speed
)

from lib.trims import (
    apply_closed_loop_trim,
    build_quick_trims
)

