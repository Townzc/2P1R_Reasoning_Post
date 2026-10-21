import unittest
from scripts import analyze_p011_long_owner_cross_attempt as a
from experiments.p011 import long_owner_path,long_owner_retry_path
class CrossAttemptLocator(unittest.TestCase):
    def test_exact_once_retry_gets_its_own_spec(self):
        self.assertIs(a.spec_path_for(long_owner_retry_path.RETRY),long_owner_retry_path)
        self.assertIs(a.spec_path_for('long_A7_S-F15_s17_owner_r1'),long_owner_path)
    def test_unapproved_retry_identity_rejected(self):
        for name in ('long_A1_S-F15_s17_owner_r3','long_A5_S-F15_s17_owner_r2','other'):
            with self.assertRaises(ValueError):a.spec_path_for(name)
if __name__=='__main__':unittest.main()
