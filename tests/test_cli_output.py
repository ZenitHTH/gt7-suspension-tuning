import unittest
from cli import format_setup_sheet
from setup import build_setup

class TestCLIOutput(unittest.TestCase):
    def test_format_setup_sheet_contains_proofs(self):
        car = {'name': 'Porsche 911 GT3 RS', 'mass_kg': 1430, 'drivetrain': 'RR', 'power_hp': 520, 'torque_nm': 470}
        setup_dict = build_setup(car, tire='RS')
        sheet = format_setup_sheet(setup_dict)
        self.assertIn('Trail-Braking', sheet)
        self.assertIn('Squat', sheet)
        self.assertIn('Tire Wear', sheet)

if __name__ == '__main__':
    unittest.main()
