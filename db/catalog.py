"""Brand Central and World Circuits catalog indexing and normalization."""
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from db.interface import CARS_DB, TRACKS_DB, norm_str

CAR_CONTINENTS: Tuple[str, ...] = ('Americas', 'Europe', 'Asia-Pacific')
TRACK_CONTINENTS: Tuple[str, ...] = ('Americas', 'Europe', 'Asia-Oceania')

_MAKER_ALIASES: Dict[str, str] = {'Citroen': 'Citroën'}
_MAKER_COUNTRY_OVERRIDES: Dict[str, str] = {'Gran Turismo': 'Japan', 'Bugatti': 'France'}
_CAR_COUNTRY_ORDER: Dict[str, Tuple[str, ...]] = {
    'Americas': ('United States',),
    'Europe': ('United Kingdom', 'Germany', 'Italy', 'France', 'Sweden', 'Austria', 'Czech Republic'),
    'Asia-Pacific': ('Japan', 'Korea', 'China'),
}
_CAR_COUNTRY_CONTINENT: Dict[str, str] = {co: cont for cont, cos in _CAR_COUNTRY_ORDER.items() for co in cos}
_BASE_CIRCUIT_COUNTRY_FALLBACKS: Dict[str, str] = {
    'SUGO International Racing Course': 'Japan', 'Mount Panorama Circuit': 'Australia', 'Yas Marina Circuit': 'UAE',
}
_TRACK_COUNTRY_CONTINENT: Dict[str, str] = {
    co: cont for cont, cos in {
        'Americas': ('United States', 'Canada', 'Brazil'),
        'Europe': ('United Kingdom', 'Germany', 'Italy', 'France', 'Spain', 'Belgium', 'Austria', 'Switzerland', 'Croatia'),
        'Asia-Oceania': ('Japan', 'Australia', 'UAE'),
    }.items() for co in cos
}


@dataclass(frozen=True)
class BrandSummary:
    """Brand entry with car count inside a Brand Central country row."""
    name: str
    country: str
    car_count: int

@dataclass(frozen=True)
class CountryBrands:
    """Country row containing its sorted Brand Central manufacturers."""
    country: str
    brands: Tuple[BrandSummary, ...]

@dataclass(frozen=True)
class CarEntry:
    """Normalized vehicle metadata for Brand Central display and search."""
    id: str
    short_name: str
    name: str
    manufacturer: str
    country: str
    continent: str
    group: str
    drivetrain: str
    power_hp: Optional[int]
    mass_kg: Optional[int]
    stock_pp: Optional[float]

@dataclass(frozen=True)
class CircuitSummary:
    """Base circuit entry with layout count inside a World Circuits continent."""
    base_circuit: str
    country: str
    continent: str
    layout_count: int

@dataclass(frozen=True)
class TrackLayoutEntry:
    """Normalized track layout metadata for World Circuits display and search."""
    id: str
    name: str
    base_circuit: str
    country: str
    continent: str
    length_km: float
    num_corners: int
    rain_supported: bool
    is_oval: bool
    category: str


def _to_car_entry(car: Dict[str, Any]) -> Optional[CarEntry]:
    """Convert raw car dict to CarEntry with maker/country normalizations."""
    raw_maker = str(car.get('manufacturer') or '')
    maker = _MAKER_ALIASES.get(raw_maker, raw_maker)
    country = _MAKER_COUNTRY_OVERRIDES.get(maker, str(car.get('country') or ''))
    continent = _CAR_COUNTRY_CONTINENT.get(country)
    if not maker or not continent:
        return None
    sn = str(car.get('short_name') or car.get('name') or '')
    return CarEntry(
        str(car.get('id', '')), sn, str(car.get('name') or sn), maker, country, continent,
        str(car.get('group') or ''), str(car.get('drivetrain') or ''),
        (car.get('engine') or {}).get('power_hp'), car.get('mass_kg'), car.get('stock_pp'),
    )

def _to_track_entry(track: Dict[str, Any]) -> Optional[TrackLayoutEntry]:
    """Convert raw track dict to TrackLayoutEntry with country fallback."""
    name = str(track.get('name') or '')
    base = str(track.get('base_circuit') or name)
    country = str(track.get('country') or '').strip() or _BASE_CIRCUIT_COUNTRY_FALLBACKS.get(base, '')
    continent = _TRACK_COUNTRY_CONTINENT.get(country)
    if not continent:
        return None
    return TrackLayoutEntry(
        str(track.get('id', '')), name, base, country, continent,
        float(track.get('length_km') or 0.0), int(track.get('num_corners') or 0),
        bool(track.get('rain_supported', False)), bool(track.get('is_oval', False)),
        str(track.get('category') or 'circuit'),
    )

def _iter_entries(items: Sequence[Dict[str, Any]], builder: Callable[[Dict[str, Any]], Any]) -> List[Any]:
    return [e for e in (builder(item) for item in items) if e is not None]

def _continent_counts(entries: Iterable[Any], continents: Tuple[str, ...], group_attr: str) -> Dict[str, Tuple[int, int]]:
    groups: Dict[str, Set[str]] = {c: set() for c in continents}
    totals: Dict[str, int] = {c: 0 for c in continents}
    for entry in entries:
        groups[entry.continent].add(getattr(entry, group_attr))
        totals[entry.continent] += 1
    return {c: (len(groups[c]), totals[c]) for c in continents}

def _country_rank(continent: str, country: str) -> Tuple[int, str]:
    order = _CAR_COUNTRY_ORDER.get(continent, ())
    return (order.index(country) if country in order else len(order), country.lower())

def _matches_tokens(text: str, tokens: Sequence[str]) -> bool:
    normalized = norm_str(text)
    return all(tok in normalized for tok in tokens)


def brand_central_continent_counts(cars: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Tuple[int, int]]:
    """Return {continent: (brand_count, car_count)} across CAR_CONTINENTS."""
    return _continent_counts(_iter_entries(CARS_DB if cars is None else cars, _to_car_entry), CAR_CONTINENTS, 'manufacturer')


def list_brands_by_country(continent: str, cars: Optional[Sequence[Dict[str, Any]]] = None) -> List[CountryBrands]:
    """Return country-grouped brand counts ordered for Brand Central."""
    grouped: Dict[str, Dict[str, int]] = {}
    for entry in _iter_entries(CARS_DB if cars is None else cars, _to_car_entry):
        if entry.continent != continent:
            continue
        counts = grouped.setdefault(entry.country, {})
        counts[entry.manufacturer] = counts.get(entry.manufacturer, 0) + 1
    return [CountryBrands(c, tuple(BrandSummary(b, c, grouped[c][b]) for b in sorted(grouped[c], key=str.lower)))
            for c in sorted(grouped, key=lambda c: _country_rank(continent, c))]


def list_cars_in_brand(continent: str, brand: str, cars: Optional[Sequence[Dict[str, Any]]] = None) -> List[CarEntry]:
    """Return cars for a normalized brand within a continent."""
    target = _MAKER_ALIASES.get(brand, brand)
    entries = _iter_entries(CARS_DB if cars is None else cars, _to_car_entry)
    return sorted((e for e in entries if e.continent == continent and e.manufacturer == target),
                  key=lambda e: (e.short_name.lower(), e.id))


def search_catalog_cars(query: str, cars: Optional[Sequence[Dict[str, Any]]] = None) -> List[CarEntry]:
    """Token-search normalized catalog cars via norm_str."""
    tokens = norm_str(query).split()
    hits = [
        (e, (raw.get('engine') or {}).get('code') or '')
        for raw in (CARS_DB if cars is None else cars)
        for e in (_to_car_entry(raw),) if e is not None
    ]
    matched = [e for e, code in hits if _matches_tokens(
        f"{e.id} {e.name} {e.short_name} {e.manufacturer} {e.country} {e.continent} {e.group} {e.drivetrain} {code}", tokens)]
    return sorted(matched, key=lambda e: (e.name.lower(), e.id))


def world_circuit_continent_counts(tracks: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Tuple[int, int]]:
    """Return {continent: (circuit_count, layout_count)} across TRACK_CONTINENTS."""
    return _continent_counts(_iter_entries(TRACKS_DB if tracks is None else tracks, _to_track_entry), TRACK_CONTINENTS, 'base_circuit')


def list_circuits_in_continent(continent: str, tracks: Optional[Sequence[Dict[str, Any]]] = None) -> List[CircuitSummary]:
    """Return unique base circuits in continent sorted alphabetically."""
    counts, countries = {}, {}
    for entry in _iter_entries(TRACKS_DB if tracks is None else tracks, _to_track_entry):
        if entry.continent != continent:
            continue
        counts[entry.base_circuit] = counts.get(entry.base_circuit, 0) + 1
        countries.setdefault(entry.base_circuit, entry.country)
    return [CircuitSummary(bc, countries[bc], continent, counts[bc]) for bc in sorted(counts, key=str.lower)]


def list_layouts_for_circuit(continent: str, base_circuit: str, tracks: Optional[Sequence[Dict[str, Any]]] = None) -> List[TrackLayoutEntry]:
    """Return track layouts for a base circuit preserving source order."""
    entries = _iter_entries(TRACKS_DB if tracks is None else tracks, _to_track_entry)
    return [e for e in entries if e.continent == continent and e.base_circuit == base_circuit]


def search_catalog_tracks(query: str, tracks: Optional[Sequence[Dict[str, Any]]] = None) -> List[TrackLayoutEntry]:
    """Token-search normalized track layouts via norm_str."""
    tokens = norm_str(query).split()
    entries = _iter_entries(TRACKS_DB if tracks is None else tracks, _to_track_entry)
    return [e for e in entries if _matches_tokens(f"{e.id} {e.name} {e.base_circuit} {e.country} {e.continent} {e.category}", tokens)]
