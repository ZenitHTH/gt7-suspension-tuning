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

if __name__ == '__main__':
    unittest.main()
