import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from countdown_smoke import canonical, safe_parse, verify_expression, solve_all, render_trace, value

class TestVerifier(unittest.TestCase):
    def test_fraction_exact(self):
        self.assertTrue(verify_expression('8 / (3 - 8 / 3)', [3,3,8,8], 24))
    def test_wrong_target(self):
        self.assertFalse(verify_expression('1+2+3+4', [1,2,3,4], 24))
    def test_reuse_and_omission(self):
        self.assertFalse(verify_expression('6*4', [1,2,3,4], 24))
    def test_injection(self):
        self.assertFalse(verify_expression('__import__("os").system("id")', [1,2,3,4], 24))
    def test_denominator_zero(self):
        self.assertFalse(verify_expression('(1+2)/(3-3)', [1,2,3,3], 24))
    def test_boolean_rejected(self):
        self.assertFalse(verify_expression('True+2+3+4', [1,2,3,4], 10))
    def test_ac_equivalence(self):
        self.assertEqual(canonical(safe_parse('(1+2)+3')), canonical(safe_parse('3+(2+1)')))
    def test_noncommutative(self):
        self.assertNotEqual(canonical(safe_parse('1-2')), canonical(safe_parse('2-1')))
    def test_solver(self):
        result = solve_all([1,2,3,4])
        self.assertIn(24, result)
        for tree in result[24]: self.assertEqual(value(tree), 24)
    def test_fraction_operands_unambiguous(self):
        text = render_trace(safe_parse('(1 / 2) / (3 / 4)'))
        self.assertIn('(1/2) / (3/4) = 2/3', text)
    def test_negative_operands_unambiguous(self):
        text = render_trace(safe_parse('(1-3)*(2-5)'))
        self.assertIn('(-2) * (-3) = 6', text)
    def test_render_surface_only(self):
        t = safe_parse('(1+2+3)*4')
        outputs = [render_trace(t, i) for i in range(4)]
        self.assertEqual(len(set(outputs)), 4)
        self.assertEqual(len({x.split('Answer: ')[1] for x in outputs}), 1)

if __name__ == '__main__': unittest.main()
