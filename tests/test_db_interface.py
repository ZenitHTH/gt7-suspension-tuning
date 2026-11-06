import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from db.interface import get_car, get_track, search_cars, get_slider_ranges

class TestDBInterface(unittest.TestCase):
    def test_get_car_by_name(self):
        car = get_car("Ferrari F355")
        self.assertIsNotNone(car)
        self.assertIn("F355", car.get("name", ""))
        self.assertEqual(car.get("drivetrain"), "MR")

    def test_get_track_by_name(self):
        track = get_track("Lago Maggiore")
        self.assertIsNotNone(track)
        self.assertIn("Maggiore", track.get("name", ""))

    def test_get_slider_ranges_preseeded(self):
        # 3342 is Red Bull X2019
        ranges = get_slider_ranges("3342")
        self.assertIn("height_front", ranges)
        self.assertEqual(ranges["height_front"], [45, 60])

class TestDataDirOverride(unittest.TestCase):
    def test_gt7_data_dir_env_override(self):
        """GT7_DATA_DIR env var takes precedence for loader resolution."""
        import json as _json
        import tempfile
        import db.loader as loader
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, 'env_probe.json'), 'w', encoding='utf-8') as f:
                _json.dump([{'id': 1, 'name': 'Env Car'}], f)
            old = os.environ.get('GT7_DATA_DIR')
            os.environ['GT7_DATA_DIR'] = tmp
            try:
                self.assertEqual(loader.get_data_dir(), os.path.abspath(tmp))
                self.assertEqual(loader.load_json('env_probe.json')[0]['name'], 'Env Car')
            finally:
                if old is None:
                    del os.environ['GT7_DATA_DIR']
                else:
                    os.environ['GT7_DATA_DIR'] = old


if __name__ == '__main__':
    unittest.main()
