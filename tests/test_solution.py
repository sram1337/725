import unittest
import sys
import os

# Add the parent directory to the path so we can import the solution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from solution import calculate_reimbursement

class TestReimbursementLogic(unittest.TestCase):

    def test_extreme_one_day_high_receipt(self):
        # This tests the case where a 1-day trip has > 800 miles
        # and receipts are over the $1800 threshold we found.
        # Expected reimbursement is 40% of receipts.
        # 2000 * 0.4 = 800
        self.assertEqual(calculate_reimbursement(1, 900, 2000), 800.00)

    def test_extreme_one_day_low_receipt(self):
        # This tests the case where a 1-day trip has > 800 miles
        # and receipts are under the $1800 threshold.
        # Expected reimbursement is (miles + receipts) * 0.6
        # (900 + 1000) * 0.6 = 1140
        self.assertEqual(calculate_reimbursement(1, 900, 1000), 1140.00)

    def test_very_long_trip_per_diem(self):
        # This tests that for a trip >= 14 days, the per diem rate drops to $50/day.
        # This case has an efficiency penalty.
        # Per Diem: 14 * 50 = 700
        # Mileage: 100 * 0.58 = 58
        # Receipts: 100 * 0.8 = 80
        # Eff Bonus: -50
        # Total: 700 + 58 + 80 - 50 = 788
        self.assertEqual(calculate_reimbursement(14, 100, 100), 788.00)

if __name__ == '__main__':
    unittest.main() 