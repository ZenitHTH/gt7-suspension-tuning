"""Unit tests for track country metadata and db.catalog."""
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


class TestTrackCountryData(unittest.TestCase):
    def test_all_tracks_have_non_empty_country_and_preserve_sugo(self):
        from db.interface import TRACKS_DB
        ids = {str(t.get('id')): t for t in TRACKS_DB}
        self.assertEqual(len(ids), 123)
        self.assertIn('2005', ids)
        self.assertEqual(ids['2005'].get('country'), 'Japan')
        self.assertEqual(ids['2005'].get('bumpiness'), 'high')
        self.assertEqual(ids['4'].get('country'), 'United States')
        self.assertEqual(ids['10'].get('country'), 'Japan')
        missing = [t['id'] for t in TRACKS_DB if not t.get('country')]
        self.assertEqual(missing, [])


class TestBrandCentralCatalog(unittest.TestCase):
    def test_complete_590_car_coverage(self):
        from db.catalog import (
            CAR_CONTINENTS, brand_central_continent_counts,
            list_brands_by_country, list_cars_in_brand,
        )
        from db.interface import CARS_DB
        counts = brand_central_continent_counts()
        self.assertEqual(tuple(counts.keys()), CAR_CONTINENTS)
        self.assertEqual(sum(car_n for _, car_n in counts.values()), len(CARS_DB))
        self.assertEqual(sum(car_n for _, car_n in counts.values()), 590)
        collected = [c.id for cont in CAR_CONTINENTS for cb in list_brands_by_country(cont)
                     for b in cb.brands for c in list_cars_in_brand(cont, b.name)]
        self.assertEqual(len(collected), 590)
        self.assertEqual(len(set(collected)), 590)

    def test_citroen_merge_and_bugatti_france(self):
        from db.catalog import list_brands_by_country, list_cars_in_brand
        europe = {cb.country: {b.name: b.car_count for b in cb.brands}
                  for cb in list_brands_by_country('Europe')}
        self.assertEqual(europe['France']['Citroën'], 6)
        self.assertNotIn('Citroen', europe['France'])
        citroen_ids = {c.id for c in list_cars_in_brand('Europe', 'Citroën')}
        self.assertIn('3613', citroen_ids)
        self.assertEqual({c.id for c in list_cars_in_brand('Europe', 'Citroen')}, citroen_ids)
        self.assertEqual(europe['France']['Bugatti'], 5)
        self.assertNotIn('Bugatti', europe['Germany'])

    def test_gran_turismo_japan_and_no_others_bucket(self):
        from db.catalog import CAR_CONTINENTS, list_brands_by_country
        asia = {cb.country: {b.name: b.car_count for b in cb.brands}
                for cb in list_brands_by_country('Asia-Pacific')}
        self.assertEqual(asia['Japan']['Gran Turismo'], 8)
        self.assertIn('Super Formula (Dallara)', asia['Japan'])
        countries = [cb.country for cont in CAR_CONTINENTS for cb in list_brands_by_country(cont)]
        self.assertNotIn('Others', countries)

    def test_zero_car_partners_omitted_and_stock_pp_none_preserved(self):
        from db.catalog import CAR_CONTINENTS, brand_central_continent_counts, list_brands_by_country, list_cars_in_brand
        brands = {b.name for cont in CAR_CONTINENTS
                  for cb in list_brands_by_country(cont) for b in cb.brands}
        for omitted in ('Fanatec', 'Brembo', 'BBS', 'Sony AI',
                        'SRT', 'Willys', 'Fittipaldi Motors', 'Renault Sport'):
            self.assertNotIn(omitted, brands)
        empty_counts = brand_central_continent_counts(cars=[{'id': 'x', 'manufacturer': '', 'country': 'Japan'}])
        self.assertEqual(empty_counts, {'Americas': (0, 0), 'Europe': (0, 0), 'Asia-Pacific': (0, 0)})
        citroen_3613 = [c for c in list_cars_in_brand('Europe', 'Citroën') if c.id == '3613'][0]
        self.assertIsNone(citroen_3613.stock_pp)


class TestWorldCircuitsCatalog(unittest.TestCase):
    def test_complete_42_circuits_and_123_layouts(self):
        from db.catalog import (
            TRACK_CONTINENTS, list_circuits_in_continent,
            list_layouts_for_circuit, world_circuit_continent_counts,
        )
        from db.interface import TRACKS_DB
        counts = world_circuit_continent_counts()
        self.assertEqual(tuple(counts.keys()), TRACK_CONTINENTS)
        self.assertEqual(sum(c_n for c_n, _ in counts.values()), 42)
        self.assertEqual(sum(l_n for _, l_n in counts.values()), len(TRACKS_DB))
        self.assertEqual(sum(l_n for _, l_n in counts.values()), 123)
        circuits = [cs for cont in TRACK_CONTINENTS for cs in list_circuits_in_continent(cont)]
        layouts = [lo for cont in TRACK_CONTINENTS for cs in list_circuits_in_continent(cont)
                   for lo in list_layouts_for_circuit(cont, cs.base_circuit)]
        self.assertEqual(len(circuits), 42)
        self.assertEqual(len(layouts), 123)

    def test_sugo_fallback_without_country_field(self):
        from db.catalog import list_circuits_in_continent
        synthetic_tracks = [
            {'id': '2005', 'name': 'SUGO International Racing Course', 'base_circuit': 'SUGO International Racing Course'},
            {'id': '199', 'name': 'Mount Panorama Motor Racing Circuit', 'base_circuit': 'Mount Panorama Circuit'},
            {'id': '2003', 'name': 'Yas Marina Circuit', 'base_circuit': 'Yas Marina Circuit'},
        ]
        asia = {c.base_circuit: c.country
                for c in list_circuits_in_continent('Asia-Oceania', tracks=synthetic_tracks)}
        self.assertEqual(asia, {
            'SUGO International Racing Course': 'Japan',
            'Mount Panorama Circuit': 'Australia',
            'Yas Marina Circuit': 'UAE',
        })


class TestCatalogSearchAndService(unittest.TestCase):
    def test_search_and_service_delegation(self):
        from db.catalog import CarEntry, TrackLayoutEntry
        from gui.service import TuningService
        svc = TuningService()
        cars = svc.search_catalog_cars('mr2 gt-s')
        self.assertTrue(any(isinstance(c, CarEntry) and c.id == '207' and c.short_name == "MR2 GT-S '97" for c in cars))
        self.assertEqual(len(svc.search_catalog_cars('citroen')), 6)
        tracks = svc.search_catalog_tracks('suzuka')
        self.assertEqual(len(tracks), 2)
        self.assertTrue(all(isinstance(t, TrackLayoutEntry) for t in tracks))
        self.assertEqual({t.id for t in tracks}, {'10', '442'})
        self.assertEqual(sum(n for _, n in svc.brand_central_continents().values()), 590)
        self.assertTrue(svc.brands_by_country('Americas'))
        self.assertTrue(svc.cars_in_brand('Asia-Pacific', 'Toyota'))
        self.assertEqual(sum(n for _, n in svc.world_circuit_continents().values()), 123)
        self.assertTrue(svc.circuits_in_continent('Europe'))
        self.assertEqual(len(svc.layouts_for_circuit('Asia-Oceania', 'Suzuka Circuit')), 2)


if __name__ == '__main__':
    unittest.main()
