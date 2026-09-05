import unittest
from src.metrics import pass_at_k, macro_pass_at_k, training_gpu_hours

class MetricsTests(unittest.TestCase):
    def test_zero(self): self.assertEqual(pass_at_k(16, 0, 8), 0.0)
    def test_all(self): self.assertEqual(pass_at_k(16, 16, 1), 1.0)
    def test_one(self): self.assertAlmostEqual(pass_at_k(10, 3, 1), 0.3)
    def test_formula(self): self.assertAlmostEqual(pass_at_k(10, 3, 2), 1-21/45)
    def test_invalid(self):
        with self.assertRaises(ValueError): pass_at_k(2, 3, 1)
    def test_macro(self): self.assertAlmostEqual(macro_pass_at_k([(10,0),(10,10)], 1), 0.5)
    def test_hours(self): self.assertAlmostEqual(training_gpu_hours(3600000, 1000, 2), 2)
    def test_bool(self):
        with self.assertRaises(TypeError): pass_at_k(True, 0, 1)

if __name__ == '__main__': unittest.main()
