import unittest

from scripts.build_token_midpoint_evidence import unused_percent


class ProcurementDisplayUnits(unittest.TestCase):
    def test_saved_four_cell_charges(self):
        # Frozen charges include fractional problem prices, not only token counts.
        cases = [(198280, '6.14'), (196716, '6.88'),
                 (185348.8828125, '12.26'), (188226.3984375, '10.90')]
        for charge, expected in cases:
            with self.subTest(charge=charge):
                p = dict(cap=211257, charge=charge, unused=(211257-charge)/211257)
                self.assertEqual(f'{unused_percent(p):.2f}', expected)

    def test_wrong_units_and_changed_accounting_rejected(self):
        p = dict(cap=211257, charge=198280, unused=12977/211257)
        for altered in (dict(p, unused=12977), dict(p, unused=p['unused']/211257),
                        dict(p, charge=198281), dict(p, cap=0)):
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                unused_percent(altered)


if __name__ == '__main__':
    unittest.main()
