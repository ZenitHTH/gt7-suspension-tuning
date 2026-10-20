#!/usr/bin/env python3
"""
GT7 Master Database Builder & Synchronization Tool
Extracts, normalizes, joins, and enriches GT7 telemetry and database records
from upstream open datasets (ddm999/gt7info, GT7-Tuning, TelemetryIQ).
"""

import os
import sys
import json
import csv
import re
import io
import urllib.request
import unicodedata
import argparse
from difflib import SequenceMatcher
from typing import Dict, List, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CSV_DIR = os.path.join(DATA_DIR, 'csv')

UPSTREAM_CSVS = [
    'cars.csv', 'engineswaps.csv', 'stockperf.csv', 'cargrp.csv',
    'maker.csv', 'country.csv', 'course.csv', 'crsbase.csv',
    'lotterycars.csv', 'trophy.csv'
]

UPSTREAM_JSONS = {
    'enriched_cars.json': 'https://raw.githubusercontent.com/EricHarkat/GT7-Tuning/main/gt7_cars_enriched.json',
    'tracks.json': 'https://raw.githubusercontent.com/EricHarkat/GT7-Tuning/main/gt7_tracks.json'
}

# Known manual specs for newly added cars and special chassis
MANUAL_SPECS = {
    '3612': {  # Toyota Chaser Tourer V '97
        'weight_kg': 1470, 'front_pct': 55, 'rear_pct': 45,
        'power_hp': 280, 'torque_nm': 377.6, 'disp_cc': 2491,
        'drivetrain': 'FR', 'body_style': 'Sedan',
        'engine_code': '1JZ-GTE', 'engine_type': 'Inline-6', 'aspiration': 'Turbocharged',
        'length_mm': 4715, 'width_mm': 1755, 'height_mm': 1400
    },
    '3611': {  # Toyota Mark II Tourer V '97
        'weight_kg': 1480, 'front_pct': 55, 'rear_pct': 45,
        'power_hp': 280, 'torque_nm': 377.6, 'disp_cc': 2491,
        'drivetrain': 'FR', 'body_style': 'Sedan',
        'engine_code': '1JZ-GTE', 'engine_type': 'Inline-6', 'aspiration': 'Turbocharged',
        'length_mm': 4760, 'width_mm': 1755, 'height_mm': 1400
    },
    '3607': {  # Porsche 963 '24
        'weight_kg': 1030, 'front_pct': 48, 'rear_pct': 52,
        'power_hp': 671, 'torque_nm': 650.0, 'disp_cc': 4593,
        'drivetrain': 'MR', 'body_style': 'Gr.1 Racecar',
        'engine_code': '9RD', 'engine_type': 'V8', 'aspiration': 'Twin-Turbocharged Hybrid',
        'length_mm': 5100, 'width_mm': 2000, 'height_mm': 1060
    },
    '3604': {  # BMW M Hybrid V8 '25
        'weight_kg': 1030, 'front_pct': 48, 'rear_pct': 52,
        'power_hp': 671, 'torque_nm': 650.0, 'disp_cc': 3999,
        'drivetrain': 'MR', 'body_style': 'Gr.1 Racecar',
        'engine_code': 'P66/3', 'engine_type': 'V8', 'aspiration': 'Twin-Turbocharged Hybrid',
        'length_mm': 5100, 'width_mm': 2000, 'height_mm': 1060
    },
    '3606': {  # Peugeot 9X8 '25
        'weight_kg': 1030, 'front_pct': 48, 'rear_pct': 52,
        'power_hp': 671, 'torque_nm': 650.0, 'disp_cc': 2600,
        'drivetrain': 'AWD', 'body_style': 'Gr.1 Racecar',
        'engine_code': 'X6H', 'engine_type': 'V6', 'aspiration': 'Twin-Turbocharged Hybrid',
        'length_mm': 4995, 'width_mm': 2000, 'height_mm': 1145
    },
    '3395': {  # Caterham Seven Superlight R500 '08
        'weight_kg': 506, 'front_pct': 48, 'rear_pct': 52,
        'power_hp': 263, 'torque_nm': 240.0, 'disp_cc': 1999,
        'drivetrain': 'FR', 'body_style': 'Roadster',
        'engine_code': 'Duratec 2.0', 'engine_type': 'Inline-4', 'aspiration': 'Naturally-Aspirated',
        'length_mm': 3100, 'width_mm': 1575, 'height_mm': 1115
    },
    '3521': {  # Mazda Mazda3 '19
        'weight_kg': 1380, 'front_pct': 60, 'rear_pct': 40,
        'power_hp': 186, 'torque_nm': 252.0, 'disp_cc': 2488,
        'drivetrain': 'FF', 'body_style': 'Hatchback',
        'engine_code': 'SKYACTIV-G 2.5', 'engine_type': 'Inline-4', 'aspiration': 'Naturally-Aspirated',
        'length_mm': 4460, 'width_mm': 1795, 'height_mm': 1435
    }
}

def norm_str(s: str) -> str:
    """Normalize unicode strings (strip diacritics, umlauts, symbols)."""
    if not s:
        return ''
    s_norm = unicodedata.normalize('NFKD', str(s)).encode('ASCII', 'ignore').decode('utf-8').lower()
    return re.sub(r'[^a-z0-9]', ' ', s_norm)

def fetch_upstream():
    """Download fresh upstream raw files."""
    os.makedirs(CSV_DIR, exist_ok=True)
    print('📥 Fetching upstream CSVs from ddm999/gt7info...')
    for f in UPSTREAM_CSVS:
        url = f'https://raw.githubusercontent.com/ddm999/gt7info/web-new/_data/db/{f}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req) as resp:
                content = resp.read()
                with open(os.path.join(CSV_DIR, f), 'wb') as out_f:
                    out_f.write(content)
                print(f'  ✓ Saved {f} ({len(content)} bytes)')
        except Exception as e:
            print(f'  ✗ Failed {f}: {e}')

    print('📥 Fetching upstream JSONs from EricHarkat/GT7-Tuning...')
    for fname, url in UPSTREAM_JSONS.items():
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req) as resp:
                content = resp.read()
                with open(os.path.join(DATA_DIR, fname), 'wb') as out_f:
                    out_f.write(content)
                print(f'  ✓ Saved {fname} ({len(content)} bytes)')
        except Exception as e:
            print(f'  ✗ Failed {fname}: {e}')

def build_database():
    """Process, link, and build master JSON databases."""
    print('🔨 Building GT7 Master Databases...')

    def load_csv(filename):
        with open(os.path.join(CSV_DIR, filename), 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    cars_csv = load_csv('cars.csv')
    makers_csv = {r['ID']: r for r in load_csv('maker.csv')}
    country_csv = {r['ID']: r['Name'] for r in load_csv('country.csv')}
    cargrp_csv = {r['ID']: r['Group'] for r in load_csv('cargrp.csv')}
    swaps_csv = load_csv('engineswaps.csv')
    stockperf_csv = load_csv('stockperf.csv')
    course_csv = load_csv('course.csv')
    crsbase_csv = {r['ID']: r for r in load_csv('crsbase.csv')}

    # Performance points
    stockperf_map = {}
    for r in stockperf_csv:
        cid = r['ID']
        if cid not in stockperf_map:
            stockperf_map[cid] = {}
        stockperf_map[cid][r['Tyre']] = float(r['PP'])

    # Engine swaps
    target_to_swaps = {}
    donor_to_recipients = {}
    all_swaps = []
    cars_csv_dict = {r['ID']: r for r in cars_csv}

    for r in swaps_csv:
        target_id = r['NewCar']
        donor_id = r['OriginalCar']
        engine = r['EngineName']

        target_info = cars_csv_dict.get(target_id, {})
        donor_info = cars_csv_dict.get(donor_id, {})

        target_maker = makers_csv.get(target_info.get('Maker', ''), {}).get('Name', '')
        donor_maker = makers_csv.get(donor_info.get('Maker', ''), {}).get('Name', '')

        target_full = f"{target_maker} {target_info.get('ShortName', '')}".strip()
        donor_full = f"{donor_maker} {donor_info.get('ShortName', '')}".strip()

        swap_obj = {
            'engine': engine,
            'target_id': target_id,
            'target_car': target_full,
            'donor_id': donor_id,
            'donor_car': donor_full
        }
        all_swaps.append(swap_obj)

        if target_id not in target_to_swaps:
            target_to_swaps[target_id] = []
        target_to_swaps[target_id].append({
            'engine': engine,
            'donor_id': donor_id,
            'donor_car': donor_full
        })

        if donor_id not in donor_to_recipients:
            donor_to_recipients[donor_id] = []
        donor_to_recipients[donor_id].append({
            'engine': engine,
            'target_id': target_id,
            'target_car': target_full
        })

    # Enriched data
    with open(os.path.join(DATA_DIR, 'enriched_cars.json'), 'r', encoding='utf-8') as f:
        enriched_cars = json.load(f)

    # Normalize VGT and alias names
    def clean_name_for_match(s: str) -> str:
        s_clean = norm_str(s)
        s_clean = s_clean.replace(' vgt', ' vision gran turismo')
        s_clean = s_clean.replace('gtr', 'gt r').replace('gt-r', 'gt r')
        s_clean = s_clean.replace('skyline', '').replace('coupe', '')
        return ' '.join(s_clean.split())

    def find_best_match(car_name: str, short_name: str) -> Optional[Dict]:
        c_norm = clean_name_for_match(car_name)
        s_norm = clean_name_for_match(short_name)

        for e in enriched_cars:
            e_norm = clean_name_for_match(e.get('name', ''))
            if c_norm == e_norm or s_norm == e_norm:
                return e

        best_score = 0.0
        best_e = None
        c_tokens = set(c_norm.split())

        for e in enriched_cars:
            e_norm = clean_name_for_match(e.get('name', ''))
            e_tokens = set(e_norm.split())
            inter = c_tokens.intersection(e_tokens)
            if not inter:
                continue
            jaccard = len(inter) / len(c_tokens.union(e_tokens))
            seq = SequenceMatcher(None, c_norm, e_norm).ratio()
            score = (jaccard * 0.4) + (seq * 0.6)
            if score > best_score:
                best_score = score
                best_e = e

        if best_score > 0.45:
            return best_e
        return None

    master_cars = []
    for c_csv in cars_csv:
        cid = c_csv['ID']
        sname = c_csv['ShortName']
        maker_id = c_csv['Maker']
        maker_obj = makers_csv.get(maker_id, {})
        maker_name = maker_obj.get('Name', 'Unknown')
        country_id = maker_obj.get('Country', '')
        country_name = country_csv.get(country_id, 'Unknown')
        full_name = f"{maker_name} {sname}".strip()

        e = find_best_match(full_name, sname)
        specs = e.get('specs', {}) if e else {}

        # Manual specs override
        man = MANUAL_SPECS.get(cid, {})

        # Weight
        weight_raw = specs.get('weight', '')
        m_w = re.search(r'([\d,]+)\s*kg', weight_raw)
        weight_kg = man.get('weight_kg') or (int(m_w.group(1).replace(',', '')) if m_w else None)

        # Balance
        balance_raw = specs.get('balance', '')
        m_bal = re.search(r'(\d+)\s*:\s*(\d+)', balance_raw)
        bal_f = man.get('front_pct') or (int(m_bal.group(1)) if m_bal else None)
        bal_r = man.get('rear_pct') or (int(m_bal.group(2)) if m_bal else None)

        # Power
        power_raw = specs.get('power', '')
        m_hp = re.search(r'([\d,]+)\s*(?:PS|bhp|HP|hp)', power_raw)
        power_hp = man.get('power_hp') or (int(m_hp.group(1).replace(',', '')) if m_hp else None)

        # Torque
        torque_raw = specs.get('torque', '')
        torque_nm = man.get('torque_nm')
        if not torque_nm:
            m_kgf = re.search(r'([\d\.]+)\s*kgf·m', torque_raw)
            m_nm = re.search(r'([\d\.]+)\s*N·m', torque_raw)
            m_lbft = re.search(r'([\d\.]+)\s*lb·ft', torque_raw)
            if m_nm:
                torque_nm = round(float(m_nm.group(1)), 1)
            elif m_kgf:
                torque_nm = round(float(m_kgf.group(1)) * 9.80665, 1)
            elif m_lbft:
                torque_nm = round(float(m_lbft.group(1)) * 1.35582, 1)

        # Displacement
        disp_raw = specs.get('displacement', '')
        m_disp = re.search(r'([\d,]+)\s*cc', disp_raw)
        disp_cc = man.get('disp_cc') or (int(m_disp.group(1).replace(',', '')) if m_disp else None)

        # Dimensions
        len_raw = specs.get('length', '')
        w_raw = specs.get('width', '')
        h_raw = specs.get('height', '')
        m_len = re.search(r'([\d,]+)\s*mm', len_raw)
        m_w_dim = re.search(r'([\d,]+)\s*mm', w_raw)
        m_h_dim = re.search(r'([\d,]+)\s*mm', h_raw)

        # Drivetrain
        layout = specs.get('layout', '')
        dt = specs.get('drivetrain', '')
        drivetrain = man.get('drivetrain') or 'FR'
        if not man.get('drivetrain'):
            if 'All' in dt or 'Four' in dt or '4WD' in dt or 'AWD' in dt:
                drivetrain = 'AWD'
            elif 'Front-Wheel' in dt:
                drivetrain = 'FF'
            elif 'Mid-Engined' in layout and 'Rear-Wheel' in dt:
                drivetrain = 'MR'
            elif 'Rear-Engined' in layout and 'Rear-Wheel' in dt:
                drivetrain = 'RR'
            elif 'Front-Engined' in layout and 'Rear-Wheel' in dt:
                drivetrain = 'FR'
            elif 'Rear-Wheel' in dt:
                drivetrain = 'FR'

        # Group
        grp_id = cargrp_csv.get(cid)
        if grp_id:
            group_str = f'Gr.{grp_id}' if str(grp_id).isdigit() else str(grp_id)
        elif e and e.get('group'):
            group_str = e.get('group')
        else:
            group_str = 'Road Car'

        # Body Style
        name_l = full_name.lower()
        body_style = man.get('body_style') or 'Coupe'
        if not man.get('body_style'):
            if any(k in name_l for k in ['sedan', 'saloon', 'chaser', 'mark ii', 'crown', 'evolution', 'wrx', 'm3 sedan', 'm5', 'amg e', 'giulia']):
                body_style = 'Sedan'
            elif any(k in name_l for k in ['hatch', 'gti', 'clio', 'megane', 'swift', 'civic', 'yaris', 'fit', 'demio', 'polo', 'golf', 'focus', 'a 45']):
                body_style = 'Hatchback'
            elif any(k in name_l for k in ['roadster', 'spider', 'spyder', 'cabrio', 'convertible', 'miata', 's2000', 'z4', 'slk', 'seven']):
                body_style = 'Roadster'
            elif any(k in name_l for k in ['suv', 'urush', 'urus', 'dbx', 'f-150', 'tundra', 'cayenne', 'macan', 'jimny']):
                body_style = 'SUV'
            elif any(k in name_l for k in ['copen', 'beat', 's660', 'cappuccino', 'alto', 'kei']):
                body_style = 'Kei'
            elif any(k in name_l for k in ['f-150', 'tundra', 'hilux', 'tacoma', 'pickup']):
                body_style = 'Pickup'
            elif 'vgt' in name_l or 'vision gran turismo' in name_l:
                body_style = 'Vision GT'
            elif group_str in ['Gr.1', 'Gr.2', 'Gr.3', 'Gr.4', 'Gr.B']:
                body_style = f'{group_str} Racecar'

        # Fallback balance if still None
        if not bal_f:
            if drivetrain == 'FF':
                bal_f, bal_r = 60, 40
            elif drivetrain in ['AWD', '4WD']:
                bal_f, bal_r = 54, 46
            elif drivetrain == 'MR':
                bal_f, bal_r = 43, 57
            elif drivetrain == 'RR':
                bal_f, bal_r = 38, 62
            else:
                bal_f, bal_r = 52, 48

        # Fallback weight if still None
        if not weight_kg:
            weight_kg = 1350 if body_style != 'Kei' else 750

        # Stock PP
        perf_by_tire = stockperf_map.get(cid, {})
        default_pp = perf_by_tire.get('CS') or perf_by_tire.get('SH') or perf_by_tire.get('RH') or (float(specs.get('pp_in_gt7')) if specs.get('pp_in_gt7') and specs.get('pp_in_gt7').replace('.','').isdigit() else None)

        master_cars.append({
            'id': cid,
            'name': full_name,
            'short_name': sname,
            'manufacturer': maker_name,
            'country': country_name,
            'group': group_str,
            'body_style': body_style,
            'drivetrain': drivetrain,
            'mass_kg': weight_kg,
            'balance': {
                'front_pct': bal_f,
                'rear_pct': bal_r,
                'ratio_str': f'{bal_f}:{bal_r}'
            },
            'dimensions_mm': {
                'length': man.get('length_mm') or (int(m_len.group(1).replace(',', '')) if m_len else None),
                'width': man.get('width_mm') or (int(m_w_dim.group(1).replace(',', '')) if m_w_dim else None),
                'height': man.get('height_mm') or (int(m_h_dim.group(1).replace(',', '')) if m_h_dim else None)
            },
            'engine': {
                'code': man.get('engine_code') or specs.get('engine_code'),
                'type': man.get('engine_type') or specs.get('engine_type'),
                'aspiration': man.get('aspiration') or specs.get('aspiration'),
                'displacement_cc': disp_cc,
                'power_hp': power_hp,
                'torque_nm': torque_nm,
                'gearbox': specs.get('gearbox')
            },
            'stock_pp': default_pp,
            'performance_by_tire': perf_by_tire,
            'swaps_available': target_to_swaps.get(cid, []),
            'is_donor_for': donor_to_recipients.get(cid, [])
        })

    # Tracks Master
    master_tracks = []
    for crs in course_csv:
        base_id = crs.get('Base', '')
        base_info = crsbase_csv.get(base_id, {})
        crs_name = crs.get('Name', '')
        length_m = int(float(crs.get('Length', '0') or '0'))
        longest_straight = int(float(crs.get('LongestStraight', '0') or '0'))
        elevation_diff = float(crs.get('ElevationDiff', '0') or '0')
        num_corners = int(float(crs.get('NumCorners', '0') or '0'))
        no_rain = crs.get('NoRain') == '1'
        is_oval = crs.get('IsOval') == '1'
        category = crs.get('Category', 'circuit')

        bumpiness = 'medium'
        downforce_demand = 'medium'
        name_l = crs_name.lower()
        if 'nurburgring' in name_l or 'nordschleife' in name_l:
            bumpiness = 'high'
            downforce_demand = 'high'
        elif 'spa' in name_l or 'suzuka' in name_l or 'silverstone' in name_l or 'fuji' in name_l:
            bumpiness = 'low'
            downforce_demand = 'high'
        elif 'tokyo' in name_l:
            bumpiness = 'medium'
            downforce_demand = 'low'
        elif 'daytona' in name_l or 'route x' in name_l or 'monza' in name_l:
            bumpiness = 'low'
            downforce_demand = 'low'
        elif category == 'dirt' or 'dirt' in name_l or 'colorado' in name_l or 'sardegna - windmills' in name_l:
            bumpiness = 'extreme'
            downforce_demand = 'none'

        master_tracks.append({
            'id': crs.get('ID'),
            'name': crs_name,
            'base_circuit': base_info.get('Name', crs_name),
            'category': category,
            'length_meters': length_m,
            'length_km': round(length_m / 1000.0, 2),
            'length_miles': round(length_m / 1609.34, 2),
            'longest_straight_m': longest_straight,
            'elevation_diff_m': elevation_diff,
            'num_corners': num_corners,
            'rain_supported': not no_rain,
            'is_oval': is_oval,
            'bumpiness': bumpiness,
            'downforce_demand': downforce_demand
        })

    # Write output
    with open(os.path.join(DATA_DIR, 'cars_master.json'), 'w', encoding='utf-8') as f:
        json.dump(master_cars, f, indent=2, ensure_ascii=False)

    with open(os.path.join(DATA_DIR, 'engine_swaps_master.json'), 'w', encoding='utf-8') as f:
        json.dump(all_swaps, f, indent=2, ensure_ascii=False)

    with open(os.path.join(DATA_DIR, 'tracks_master.json'), 'w', encoding='utf-8') as f:
        json.dump(master_tracks, f, indent=2, ensure_ascii=False)

    complete_cars = sum(1 for c in master_cars if c['mass_kg'] is not None and c['balance']['front_pct'] is not None)
    print('=' * 60)
    print(f'✅ Database Build Complete!')
    print(f'  • Cars: {len(master_cars)} total ({complete_cars}/{len(master_cars)} with 100% complete specs)')
    print(f'  • Engine Swaps: {len(all_swaps)} swaps')
    print(f'  • Tracks: {len(master_tracks)} track layouts')
    print('=' * 60)

def main():
    parser = argparse.ArgumentParser(description='GT7 Master Database Builder & Sync Tool')
    parser.add_argument('--fetch', action='store_true', help='Download fresh raw files from upstream GitHub repos')
    parser.add_argument('--build', action='store_true', help='Process and generate master JSON databases')
    args = parser.parse_args()

    if args.fetch:
        fetch_upstream()
    
    # Default is build if neither or if --build is specified
    build_database()

if __name__ == '__main__':
    main()
