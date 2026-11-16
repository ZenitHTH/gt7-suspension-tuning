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


if __name__ == '__main__':
    unittest.main()
