#!/usr/bin/env python3
"""
GT7 Race-Engineering CLI Interface & Setup Sheet Formatter (Root Runner)
"""

import sys
import os
import json
import argparse
from typing import Dict, Any, Optional

import setup
from db.interface import get_car, get_track, save_car_sliders
from sheet_formatter import format_setup_sheet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
import gt7_db


def _add_vehicle_arguments(parser: argparse.ArgumentParser) -> None:
    """Register vehicle selection and override flags."""
    parser.add_argument('car', nargs='?', help="Car name or ID from GT7 database")
    parser.add_argument('-t', '--track', help="Target track name or ID")
    parser.add_argument('--tire', default='SS', choices=['CH','CM','CS','SH','SM','SS','RH','RM','RS','Dirt','Wet'])
    parser.add_argument('--mass', type=int)
    parser.add_argument('--power', type=int)
    parser.add_argument('--torque', type=float)
    parser.add_argument('-d', '--drivetrain', choices=['FF','FR','MR','RR','AWD','4WD','4x4'])
    parser.add_argument('--balance', type=int, nargs=2, metavar=('FRONT', 'REAR'))
    parser.add_argument('--mode', default='grip', choices=['grip','time_attack','wet','dirt','drift','endurance'])


def _add_query_arguments(parser: argparse.ArgumentParser) -> None:
    """Register database query and search flags."""
    parser.add_argument('-s', '--search', type=str, help="Search cars by name, keyword, or ID")
    parser.add_argument('-m', '--maker', type=str, help="Filter cars by manufacturer")
    parser.add_argument('-g', '--group', type=str, help="Filter cars by class/group (e.g. Gr.3)")
    parser.add_argument('--swaps', type=str, help="Lookup engine swaps for a car")
    parser.add_argument('--tracks', type=str, nargs='?', const='', help="Search tracks by keyword")
    parser.add_argument('--rain', action='store_true', help="Filter tracks with rain support")


def _add_slider_range_arguments(parser: argparse.ArgumentParser) -> None:
    """Register user-provided slider range bounds flags."""
    parser.add_argument('--df-front', type=int, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--df-rear', type=int, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--height-range', type=int, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--height-front', type=int, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--height-rear', type=int, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--fn-front', type=float, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--fn-rear', type=float, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--save-sliders', action='store_true')


def _add_options_arguments(parser: argparse.ArgumentParser) -> None:
    """Register session control, handling trims, and output flags."""
    parser.add_argument('--stability', type=float, nargs=2, metavar=('LOW', 'HIGH'))
    parser.add_argument('--symptom', nargs='+', choices=['entry_push','exit_snap','bottoming','curb_hop','front_tire_wear','rear_tire_wear'])
    parser.add_argument('--widebody', action='store_true')
    parser.add_argument('--speed', type=float)
    parser.add_argument('--controller', action='store_true', help="Optimize setup for Gamepad/DualSense controller users")
    parser.add_argument('--g-forces', type=float, nargs=3, metavar=('G60', 'G120', 'G240'))
    parser.add_argument('--g-ref-df', type=int, nargs=2, metavar=('FRONT', 'REAR'))
    parser.add_argument('--solve', choices=['balanced', 'max_grip', 'min_tire_wear'])
    parser.add_argument('--json', action='store_true')


def build_argument_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for GT7 suspension tuning."""
    parser = argparse.ArgumentParser(description="GT7 First-Principles Race-Engineering Auto-Tuner")
    _add_vehicle_arguments(parser)
    _add_slider_range_arguments(parser)
    _add_options_arguments(parser)
    _add_query_arguments(parser)
    return parser


def _is_db_query(args: argparse.Namespace) -> bool:
    """Check if CLI invocation is a database query command."""
    query_flags = ['search', 'tracks', 'swaps', 'maker', 'group', 'rain']
    if any(getattr(args, flag, None) for flag in query_flags):
        return True
    return args.car is None and args.drivetrain is not None


def _save_slider_ranges_if_requested(args: argparse.Namespace, car_data: Dict[str, Any]) -> None:
    """Save provided slider range flags to the database if requested."""
    if not (args.save_sliders and car_data.get('id')):
        return
    keys = ['df_front', 'df_rear', 'height_range', 'height_front', 'height_rear', 'fn_front', 'fn_rear']
    new_sliders = {k: list(getattr(args, k)) for k in keys if getattr(args, k, None)}
    save_car_sliders(str(car_data['id']), new_sliders)


def _extract_setup_kwargs(
    args: argparse.Namespace,
    car_data: Dict[str, Any],
    track_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Map parsed CLI arguments to build_setup parameter keyword dictionary."""
    return {
        'car': car_data, 'track': track_data, 'tire': args.tire,
        'custom_mass': args.mass, 'custom_power': args.power, 'custom_torque': args.torque,
        'custom_drivetrain': args.drivetrain, 'custom_balance': args.balance,
        'mode': args.mode, 'df_front_range': args.df_front, 'df_rear_range': args.df_rear,
        'height_range': args.height_range, 'height_front_range': args.height_front,
        'height_rear_range': args.height_rear, 'fn_front_range': args.fn_front,
        'fn_rear_range': args.fn_rear, 'stability': args.stability, 'symptoms': args.symptom,
        'is_widebody': args.widebody, 'speed_kmh': args.speed, 'is_controller': args.controller,
        'g_forces': tuple(args.g_forces) if args.g_forces else None,
        'g_ref_df': tuple(args.g_ref_df) if args.g_ref_df else None,
        'solve_objective': args.solve
    }


def _resolve_car_data(args: argparse.Namespace) -> Dict[str, Any]:
    """Resolve car data dictionary from DB or fallback CLI arguments."""
    return get_car(args.car) or {
        'name': args.car, 'mass_kg': args.mass or 1350, 'drivetrain': args.drivetrain or 'FR'
    }


def main():
    """Main CLI entrypoint for running setup and printing outputs."""
    parser = build_argument_parser()
    args = parser.parse_args()
    if _is_db_query(args):
        gt7_db.main()
        return
    if not args.car:
        parser.print_help()
        return

    car_data = _resolve_car_data(args)
    _save_slider_ranges_if_requested(args, car_data)
    setup_kwargs = _extract_setup_kwargs(args, car_data, get_track(args.track) if args.track else None)
    res = setup.build_setup(**setup_kwargs)
    print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else format_setup_sheet(res))


if __name__ == '__main__':
    main()
