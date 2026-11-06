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


class TestAtomicSliderSave(unittest.TestCase):
    def test_midwrite_failure_leaves_db_intact(self):
        # A crash/AV-lock mid-write must not truncate the database.
        import json
        import tempfile
        import db.interface as di
        payload = [{'id': '9999', 'name': 'Atomic Car'}]
        with tempfile.TemporaryDirectory() as tmp:
            db_file = os.path.join(tmp, 'cars_master.json')
            with open(db_file, 'w', encoding='utf-8') as f:
                json.dump(payload, f)
            original_dump = di.json.dump

            def boom(*_a, **_k):
                raise OSError('disk full / AV lock')

            di.json.dump = boom
            try:
                with self.assertRaises(OSError):
                    di.save_car_sliders('9999', {'df_front': (10, 20)}, db_path=db_file)
            finally:
                di.json.dump = original_dump
            with open(db_file, 'r', encoding='utf-8') as f:
                self.assertEqual(json.load(f), payload)  # original intact
            self.assertFalse(os.path.exists(db_file + '.tmp'))  # no leftover


if __name__ == '__main__':
    unittest.main()
