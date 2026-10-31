#!/usr/bin/env python3
"""
GT7 Database Query Interface
Provides high-level querying, fuzzy matching, and pre-seeded slider boundaries for GT7 vehicles and circuits.
"""

import os
import json
import re
import unicodedata
from typing import List, Dict, Optional, Any, Set
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


def _populate_car_sliders(car: Dict[str, Any], preseeded: Dict[str, Any]) -> None:
    """Populate slider ranges for a single car record."""
    cid = str(car.get('id'))
    if cid not in preseeded:
        return
    sr = car.setdefault('slider_ranges', {})
    if not sr:
        car['slider_ranges'] = dict(preseeded[cid])
        return
    for k, v in preseeded[cid].items():
        sr.setdefault(k, v)


def _init_preseeded_sliders(cars: List[Dict[str, Any]], preseeded: Dict[str, Any]) -> None:
    """Pre-populate tested slider ranges into in-memory car records."""
    for car in cars:
        _populate_car_sliders(car, preseeded)


_init_preseeded_sliders(CARS_DB, PRESEEDED_SLIDER_RANGES)


def norm_str(s: Any) -> str:
    """Normalize unicode strings (strip accents, umlauts, symbols)."""
    if s is None:
        return ''
    s_norm = unicodedata.normalize('NFKD', str(s)).encode('ASCII', 'ignore').decode('utf-8').lower()
    return re.sub(r'[^a-z0-9]', ' ', s_norm)


def get_slider_ranges(car_id: str) -> Dict[str, Any]:
    """Retrieve pre-seeded or configured slider ranges for a car ID."""
    return PRESEEDED_SLIDER_RANGES.get(str(car_id), {})


def _matches_car_attributes(
    car: Dict[str, Any],
    maker: Optional[str],
    drivetrain: Optional[str],
    group: Optional[str],
    has_swaps_only: bool
) -> bool:
    """Check whether car record matches filter attributes."""
    if maker and norm_str(maker) not in norm_str(car.get('manufacturer', '')):
        return False
    if drivetrain and car.get('drivetrain', '').upper() != drivetrain.upper():
        return False
    if group and norm_str(group) not in norm_str(car.get('group', '')):
        return False
    if has_swaps_only and not car.get('swaps_available'):
        return False
    return True


def _matches_query_tokens(car: Dict[str, Any], q_tokens: Optional[Set[str]]) -> bool:
    """Check whether car matches tokenized fulltext query."""
    if not q_tokens:
        return True
    c_text = f"{car.get('id','')} {car.get('name','')} {car.get('short_name','')} {car.get('manufacturer','')} {car.get('engine',{}).get('code','')} {car.get('group','')}"
    c_norm = norm_str(c_text)
    return all(tok in c_norm for tok in q_tokens)


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
        if not _matches_car_attributes(car, maker, drivetrain, group, has_swaps_only):
            continue
        if not _matches_query_tokens(car, q_tokens):
            continue
        results.append(car)
    return results


def _match_car_by_id_or_name(ident_str: str, ident_norm: str) -> Optional[Dict[str, Any]]:
    """Match car by exact ID or exact normalized name."""
    for c in CARS_DB:
        if str(c.get('id')) == ident_str:
            return c
    for c in CARS_DB:
        if norm_str(c.get('name')) == ident_norm or norm_str(c.get('short_name')) == ident_norm:
            return c
    return None


def get_car(identifier: str) -> Optional[Dict[str, Any]]:
    """Get a single car by exact ID or best matching name."""
    if not identifier:
        return None
    ident_str = str(identifier).strip()
    ident_norm = norm_str(ident_str)

    direct_match = _match_car_by_id_or_name(ident_str, ident_norm)
    if direct_match:
        return direct_match

    matches = search_cars(query=ident_str)
    return matches[0] if matches else None


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


def _update_car_slider_dict(target_car: Dict[str, Any], sliders: Dict[str, Any]) -> Dict[str, Any]:
    """Update in-place slider ranges on target car record."""
    ranges = target_car.setdefault('slider_ranges', {})
    for k, v in sliders.items():
        if v is not None:
            ranges[k] = list(v) if isinstance(v, (list, tuple)) else v
    return ranges


def _persist_cars_file(target_path: str, cars: List[Dict[str, Any]]) -> None:
    """Write updated cars collection to json file."""
    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(cars, f, ensure_ascii=False, indent=2)


def save_car_sliders(car_id: str, sliders: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    """Persist user-provided min/max slider ranges for a car into cars_master.json."""
    target_path = db_path or os.path.join(get_data_dir(), 'cars_master.json')
    if not os.path.exists(target_path):
        return {}

    with open(target_path, 'r', encoding='utf-8') as f:
        cars = json.load(f)

    target_car = next((c for c in cars if str(c.get('id')) == str(car_id)), None)
    if not target_car:
        return {}

    ranges = _update_car_slider_dict(target_car, sliders)
    _persist_cars_file(target_path, cars)

    if not db_path:
        memory_car = next((c for c in CARS_DB if str(c.get('id')) == str(car_id)), None)
        if memory_car:
            memory_car['slider_ranges'] = ranges

    return ranges
