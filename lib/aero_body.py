#!/usr/bin/env python3
"""
GT7 Aerodynamics & Body Clearance Module (Facade)
Re-exports calculations from modular components:
- lib.ride_height (ride height & ground clearance)
- lib.aerodynamics (downforce & Center of Pressure)
- lib.equilibrium (trail-braking simulation & suspension equilibrium solver)
"""

from lib.ride_height import calculate_ride_height
from lib.aerodynamics import calculate_aerodynamics
from lib.equilibrium import (
    simulate_high_speed_trail_braking,
    solve_suspension_equilibrium
)

__all__ = [
    'calculate_ride_height',
    'calculate_aerodynamics',
    'simulate_high_speed_trail_braking',
    'solve_suspension_equilibrium'
]
