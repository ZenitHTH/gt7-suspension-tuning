#!/usr/bin/env python3
"""
GT7 Database Query Interface
Provides high-level querying, fuzzy matching, and pre-seeded slider boundaries for GT7 vehicles and circuits.
"""

import os
import json
import re
import unicodedata
from typing import List, Dict, Optional, Any
from db.loader import load_json, get_data_dir

# 1. Pre-seeded Tested Slider Ranges (Update 1.72+ Spec IV)
PRESEEDED_SLIDER_RANGES: Dict[str, Dict[str, Any]] = {
    '3342': {'height_front': [45, 60], 'height_rear': [45, 60], 'fn_front': [4.0, 6.0], 'fn_rear': [4.0, 6.0], 'df_front': [700, 900], 'df_rear': [1300, 1700]},
    '3374': {'height_front': [45, 55], 'height_rear': [50, 65], 'fn_front': [4.0, 6.0], 'fn_rear': [4.0, 6.0], 'df_front': [800, 1200], 'df_rear': [1200, 1600]},
    '3517': {'height_front': [45, 55], 'height_rear': [50, 65], 'fn_front': [4.0, 6.0], 'fn_rear': [4.0, 6.0], 'df_front': [800, 1200], 'df_rear': [1200, 1600]},
    '3440': {'df_front': [50, 200], 'df_rear': [140, 290]},
    '3385': {'df_front': [50, 200], 'df_rear': [100, 250]},
    '3387': {'df_front': [200, 250], 'df_rear': [300, 350]},
    '3596': {'height_front': [65, 105], 'height_rear': [65, 105], 'fn_front': [1.5, 3.5], 'fn_rear': [1.5, 3.5], 'df_front': [200, 200], 'df_rear': [400, 500]},
    '3614': {'df_front': [50, 200], 'df_rear': [100, 250]},
}

# 2. In-Memory Master Datasets
CARS_DB: List[Dict[str, Any]] = load_json('cars_master.json', default=[])
SWAPS_DB: List[Dict[str, Any]] = load_json('engine_swaps_master.json', default=[])
TRACKS_DB: List[Dict[str, Any]] = load_json('tracks_master.json', default=[])
PRESETS_DB: Dict[str, Any] = load_json('tuning_presets.json', default={})

# Pre-populate tested slider ranges into in-memory car records
for _c in CARS_DB:
    _cid = str(_c.get('id'))
    if _cid in PRESEEDED_SLIDER_RANGES:
        _sr = _c.setdefault('slider_ranges', {})
        if not _sr:
            _c['slider_ranges'] = dict(PRESEEDED_SLIDER_RANGES[_cid])
        else:
            for _k, _v in PRESEEDED_SLIDER_RANGES[_cid].items():
                _sr.setdefault(_k, _v)

def norm_str(s: Any) -> str:
    """Normalize unicode strings (strip accents, umlauts, symbols)."""
    if s is None:
        return ''
    s_norm = unicodedata.normalize('NFKD', str(s)).encode('ASCII', 'ignore').decode('utf-8').lower()
    return re.sub(r'[^a-z0-9]', ' ', s_norm)

def get_slider_ranges(car_id: str) -> Dict[str, Any]:
    """Retrieve pre-seeded or configured slider ranges for a car ID."""
    return PRESEEDED_SLIDER_RANGES.get(str(car_id), {})

def search_cars(
    query: Optional[str] = None,
    maker: Optional[str] = None,
    drivetrain: Optional[str] = None,
    group: Optional[str] = None,
    has_swaps_only: bool = False
) -> List[Dict[str, Any]]:
    """Filter and search cars from the GT7 master database."""
    results = []
    q_tokens = set(norm_str(query).split()) if query else None

    for car in CARS_DB:
        if maker and norm_str(maker) not in norm_str(car.get('manufacturer', '')):
            continue
        if drivetrain and car.get('drivetrain', '').upper() != drivetrain.upper():
            continue
        if group and norm_str(group) not in norm_str(car.get('group', '')):
            continue
        if has_swaps_only and not car.get('swaps_available'):
            continue
        if q_tokens:
            c_text = f"{car.get('id','')} {car.get('name','')} {car.get('short_name','')} {car.get('manufacturer','')} {car.get('engine',{}).get('code','')} {car.get('group','')}"
            c_norm = norm_str(c_text)
            if not all(tok in c_norm for tok in q_tokens):
                continue
        results.append(car)
    return results

def get_car(identifier: str) -> Optional[Dict[str, Any]]:
    """Get a single car by exact ID or best matching name."""
    if not identifier:
        return None
    ident_str = str(identifier).strip()

    # 1. Exact ID match
    for c in CARS_DB:
        if str(c.get('id')) == ident_str:
            return c

    # 2. Exact full name match (normalized)
    ident_norm = norm_str(ident_str)
    for c in CARS_DB:
        if norm_str(c.get('name')) == ident_norm or norm_str(c.get('short_name')) == ident_norm:
            return c

    # 3. Best query search match
    matches = search_cars(query=ident_str)
    if matches:
        return matches[0]
    return None

def get_track(identifier: str) -> Optional[Dict[str, Any]]:
    """Get a track by ID or matching name."""
    if not identifier:
        return None
    ident_str = str(identifier).strip()
    ident_norm = norm_str(ident_str)

    for t in TRACKS_DB:
        if str(t.get('id')) == ident_str:
            return t
        if norm_str(t.get('name')) == ident_norm or norm_str(t.get('short_name', '')) == ident_norm:
            return t

    q_tokens = set(ident_norm.split())
    for t in TRACKS_DB:
        t_text = f"{t.get('id','')} {t.get('name','')} {t.get('short_name','')} {t.get('country','')}"
        if all(tok in norm_str(t_text) for tok in q_tokens):
            return t
    return None

def save_car_sliders(car_id: str, sliders: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    """Persist user-provided min/max slider ranges for a car into cars_master.json."""
    data_dir = get_data_dir()
    target_path = db_path or os.path.join(data_dir, 'cars_master.json')
    if not os.path.exists(target_path):
        return {}

    with open(target_path, 'r', encoding='utf-8') as f:
        cars = json.load(f)

    target_car = None
    for c in cars:
        if str(c.get('id')) == str(car_id):
            target_car = c
            break

    if not target_car:
        return {}

    ranges = target_car.setdefault('slider_ranges', {})
    for k, v in sliders.items():
        if v is not None:
            ranges[k] = list(v) if isinstance(v, (list, tuple)) else v

    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(cars, f, ensure_ascii=False, indent=2)

    if not db_path:
        for c in CARS_DB:
            if str(c.get('id')) == str(car_id):
                c['slider_ranges'] = ranges
                break

    return ranges
