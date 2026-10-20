import unittest
from unittest.mock import patch
from experiments.p010.common import budget_check, require_published


class AdmissionTests(unittest.TestCase):
    def test_boundary_and_no_category_transfer(self):
        self.assertEqual(budget_check('G', 40, 8, 8)['remaining_before_usd'], '10')
        for args in [('G',40,9,8.01),('G',49,2,0),('I',14,1,1),('T',0,5,6)]:
            with self.assertRaises(ValueError): budget_check(*args)

    def test_nonfinite_or_negative_cannot_admit(self):
        for value in ('NaN','Infinity','-1'):
            with self.assertRaises(ValueError): budget_check('G',0,1,value)

    def test_remote_mismatch_and_unpublished_code(self):
        with patch('subprocess.check_output',side_effect=['abc\n','def refs/heads/x\n']):
            with self.assertRaises(ValueError): require_published('.')
        with patch('subprocess.check_output',side_effect=['abc\n','abc refs/heads/x\n','?? experiments/p010/x.py\n']):
            with self.assertRaises(ValueError): require_published('.')
        with patch('subprocess.check_output',side_effect=['abc\n','abc refs/heads/x\n','']):
            self.assertEqual(require_published('.'),'abc')


if __name__ == '__main__': unittest.main()
