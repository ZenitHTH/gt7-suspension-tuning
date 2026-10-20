#!/usr/bin/env python3
"""
GT7 Raw Database Engine & CLI (FGO DB / Atlas Academy style for Gran Turismo 7)
Provides instant lookup for cars, engine swaps, track telemetry, and performance specs.
(Now forwarded to modular db.interface layer)
"""

import os
import sys
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from db.interface import (
    CARS_DB,
    TRACKS_DB,
    SWAPS_DB,
    PRESETS_DB,
    PRESEEDED_SLIDER_RANGES,
    norm_str,
    search_cars,
    get_car,
    get_track,
    get_slider_ranges,
    save_car_sliders
)
from db.loader import get_data_dir, load_json

DATA_DIR = get_data_dir()

def get_swaps(car_query: str):
    """Get engine swaps for a car (both swaps it can receive and swaps it can donate)."""
    car = get_car(car_query)
    if not car:
        return {'found': False, 'query': car_query, 'swaps_available': [], 'is_donor_for': []}
    return {
        'found': True,
        'car_id': car.get('id'),
        'car_name': car.get('name'),
        'swaps_available': car.get('swaps_available', []),
        'is_donor_for': car.get('is_donor_for', [])
    }

def search_tracks(query: Optional[str] = None, rain_only: bool = False) -> List[Dict]:
    """Search GT7 circuits and layouts with full unicode/accent normalization."""
    results = []
    q_norm = norm_str(query) if query else None

    for t in TRACKS_DB:
        if rain_only and not t.get('rain_supported'):
            continue
        if q_norm:
            t_text = f"{t.get('id','')} {t.get('name','')} {t.get('base_circuit','')} {t.get('category','')}"
            t_norm = norm_str(t_text)
            if q_norm not in t_norm:
                # Check token match
                q_tokens = set(q_norm.split())
                if not all(tok in t_norm for tok in q_tokens):
                    continue
        results.append(t)
    return results

def format_car_sheet(car: Dict) -> str:
    """Format car specifications into a readable GT7 telemetry block."""
    lines = []
    lines.append('=' * 75)
    lines.append(f"🏎️  {car.get('name', 'Unknown Car')} [{car.get('group', 'Road Car')}]")
    lines.append('=' * 75)
    lines.append(f"• ID: {car.get('id')}  |  Maker: {car.get('manufacturer')}  |  Origin: {car.get('country')}")
    lines.append(f"• Drivetrain: {car.get('drivetrain')}  |  Body Style: {car.get('body_style')}  |  Stock PP: {car.get('stock_pp')}")
    
    eng = car.get('engine', {})
    lines.append(f"• Engine Code: {eng.get('code') or 'N/A'}  |  Type: {eng.get('type') or 'N/A'}  |  Aspiration: {eng.get('aspiration') or 'N/A'}")
    lines.append(f"• Displacement: {eng.get('displacement_cc', 'N/A')} cc  |  Power: {eng.get('power_hp', 'N/A')} HP  |  Torque: {eng.get('torque_nm', 'N/A')} N·m")
    
    bal = car.get('balance', {})
    dim = car.get('dimensions_mm', {})
    lines.append(f"• Mass: {car.get('mass_kg', 'N/A')} kg  |  F:R Balance: {bal.get('ratio_str', 'N/A')} ({bal.get('front_pct')}% : {bal.get('rear_pct')}%)  |  L/W/H: {dim.get('length')}x{dim.get('width')}x{dim.get('height')} mm")

    # Swaps
    swaps = car.get('swaps_available', [])
    if swaps:
        lines.append('─' * 75)
        lines.append('🔧 Compatible Engine Swaps (สามารถวางเครื่อง):')
        for s in swaps:
            lines.append(f"   ➔ [{s.get('engine')}] from {s.get('donor_car')} (Donor ID: {s.get('donor_id')})")

    donor = car.get('is_donor_for', [])
    if donor:
        lines.append('─' * 75)
        lines.append('🎁 Donates Engine To (เป็นเครื่องบริจาคให้คันอื่น):')
        for d in donor:
            lines.append(f"   ➔ [{d.get('engine')}] into {d.get('target_car')}")

    # Tire PP
    tires = car.get('performance_by_tire', {})
    if tires:
        lines.append('─' * 75)
        lines.append('🏁 Stock Performance Points (PP by Tire Compound):')
        tire_str = ' | '.join([f'{t}: {pp:.2f}' for t, pp in sorted(tires.items())])
        lines.append(f"   {tire_str}")

    lines.append('=' * 75)
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description='Gran Turismo 7 Raw Database CLI')
    parser.add_argument('-s', '--search', type=str, help='Search cars by name, keyword, or car ID')
    parser.add_argument('-m', '--maker', type=str, help='Filter by manufacturer')
    parser.add_argument('-d', '--drivetrain', type=str, choices=['FF', 'FR', 'MR', 'RR', 'AWD', '4WD'], help='Filter by drivetrain')
    parser.add_argument('-g', '--group', type=str, help='Filter by group (Gr.1, Gr.2, Gr.3, Gr.4, Gr.B)')
    parser.add_argument('--swaps', type=str, help='Lookup engine swaps for a car')
    parser.add_argument('--tracks', type=str, nargs='?', const='', help='List or search tracks')
    parser.add_argument('--rain', action='store_true', help='Filter tracks that support wet/rain conditions')
    parser.add_argument('--json', action='store_true', help='Output in raw JSON format')
    parser.add_argument('--swaps-only', action='store_true', help='Filter only cars with available engine swaps')

    args = parser.parse_args()

    if args.swaps:
        data = get_swaps(args.swaps)
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            if not data['found']:
                print(f"❌ Car not found: '{args.swaps}'")
            else:
                print(f"\n🔧 Engine Swap Matrix for: {data['car_name']} (ID: {data['car_id']})")
                print('=' * 70)
                if data['swaps_available']:
                    print('Available Swaps for this car:')
                    for s in data['swaps_available']:
                        print(f"  • Engine: {s['engine']:<20} | Donor: {s['donor_car']}")
                else:
                    print('No engine swaps available for this car.')
                if data['is_donor_for']:
                    print('\nThis car donates its engine to:')
                    for d in data['is_donor_for']:
                        print(f"  • Engine: {d['engine']:<20} | Recipient: {d['target_car']}")
                print('=' * 70)
        return

    if args.tracks is not None:
        t_res = search_tracks(query=args.tracks if args.tracks != '' else None, rain_only=args.rain)
        if args.json:
            print(json.dumps(t_res, indent=2, ensure_ascii=False))
        else:
            print(f"\n🏁 GT7 Tracks Database ({len(t_res)} layouts found):")
            print('=' * 95)
            print(f"{'ID':<5} {'Track Name':<42} {'Length':<10} {'Rain':<6} {'Bumpiness':<10} {'Downforce':<10}")
            print('─' * 95)
            for t in t_res:
                rain_str = '🌧️ Yes' if t['rain_supported'] else '☀️ No'
                print(f"{t['id']:<5} {t['name']:<42} {t['length_km']:>5.2f} km  {rain_str:<6} {t['bumpiness']:<10} {t['downforce_demand']:<10}")
            print('=' * 95)
        return

    cars = search_cars(
        query=args.search,
        maker=args.maker,
        drivetrain=args.drivetrain,
        group=args.group,
        has_swaps_only=args.swaps_only
    )

    if args.json:
        print(json.dumps(cars, indent=2, ensure_ascii=False))
    else:
        if not cars:
            print('❌ No cars matched your search criteria.')
        elif len(cars) == 1:
            print(format_car_sheet(cars[0]))
        else:
            print(f"\n🏎️  GT7 Database Search Results ({len(cars)} cars found):")
            print('=' * 95)
            print(f"{'ID':<5} {'Car Name':<48} {'Drive':<6} {'Mass':<8} {'Power':<8} {'PP':<7} {'Swaps':<6}")
            print('─' * 95)
            for c in cars:
                swaps_cnt = len(c.get('swaps_available', []))
                sw_str = f'🔧 {swaps_cnt}' if swaps_cnt > 0 else '-'
                mass_str = f"{c.get('mass_kg')} kg" if c.get('mass_kg') else 'N/A'
                pwr_str = f"{c.get('engine',{}).get('power_hp')} HP" if c.get('engine',{}).get('power_hp') else 'N/A'
                pp_str = f"{c.get('stock_pp'):.1f}" if c.get('stock_pp') else 'N/A'
                print(f"{c.get('id', 'N/A'):<5} {c.get('name', 'N/A'):<48} {c.get('drivetrain', 'N/A'):<6} {mass_str:<8} {pwr_str:<8} {pp_str:<7} {sw_str:<6}")
            print('=' * 95)
            print("Tip: Query a specific car with: python3 scripts/gt7_db.py -s <Exact Name or ID> for full telemetry!")

if __name__ == '__main__':
    main()
