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

    def test_dynamic_g_force_at_downforce_and_solver_in_sheet(self):
        car = {
            'id': '3466', 'name': "Ford Sierra RS 500 Cosworth '87",
            'drivetrain': 'FR', 'mass_kg': 989, 'power_hp': 359, 'torque_nm': 368.9,
            'balance': {'front_pct': 56, 'rear_pct': 44}
        }
        res = build_setup(
            car=car, tire='RM', mode='endurance',
            df_front_range=(50, 200), df_rear_range=(100, 250),
            height_front_range=(100, 200), height_rear_range=(120, 220),
            fn_front_range=(1.50, 3.50), fn_rear_range=(1.50, 3.50),
            g_forces=(1.46, 1.59, 1.75), g_ref_df=(110, 100),
            solve_objective='balanced', is_widebody=True, speed_kmh=240.0
        )
        sheet = format_setup_sheet(res)
        df_f = res['parameters']['downforce']['front']
        df_r = res['parameters']['downforce']['rear']
        self.assertIn(f"@ DF {df_f}/{df_r}", sheet)
        self.assertIn("Min DF", sheet)
        self.assertIn("Max DF", sheet)
        self.assertFalse(res['telemetry']['high_speed_simulation']['bottoming_or_fender_hit'])

if __name__ == '__main__':
    unittest.main()
