"""New B-only owner-amendment fixtures; no original successful test replay."""
import unittest
from experiments.p011 import short_generation as short
from tests.test_p011_c1_short_drafts import saved


class B16Rule(unittest.TestCase):
    @staticmethod
    def fixture(failed=0):
        ids=[f'p{i}' for i in range(400)]
        rows={f'{p}::attempt{a:02d}':saved(p,a,i>=failed)
              for i,p in enumerate(ids) for a in range(1,17)}
        return ids,rows

    def test_attempt16_is_eligible_and_unique_nested(self):
        ids,rows=self.fixture()
        for a in range(1,16):rows[f'p0::attempt{a:02d}']=saved('p0',a,False)
        result=short.b_selection(ids,rows)
        self.assertEqual(result['selected_ids']['1'][0],'p0::attempt16')
        self.assertEqual(result['selected_ids']['4'][0],'p0::attempt16')
        self.assertEqual(result['unverified_fallback_questions'],[])

    def test_exact10percent_retains_fallback_without_extra_disposition(self):
        ids,rows=self.fixture(40);result=short.b_selection(ids,rows)
        self.assertEqual(result['nesting_conflicts'],ids[:40])
        self.assertEqual(result['unverified_fallback_questions'],ids[:40])
        self.assertFalse(result['requires_owner_disposition'])
        self.assertEqual(result['selected_ids']['1'][0],'p0::attempt01')
        self.assertFalse(any(cid.startswith('p0::') for cid in result['selected_ids']['4']))

    def test_over10percent_requires_report_before_training(self):
        ids,rows=self.fixture(41);result=short.b_selection(ids,rows)
        self.assertTrue(result['report_fallback_above_10pct'])
        self.assertTrue(result['requires_owner_disposition'])
        self.assertFalse(result['training_admitted'])
        self.assertNotIn('report_fallback_above_3pct',result)

    def test_missing_attempt16_is_unknown_not_fallback(self):
        ids,rows=self.fixture();del rows['p0::attempt16']
        with self.assertRaisesRegex(ValueError,'All16'):short.b_selection(ids,rows)

    def test_C2_still_stops_at_four_even_if_fifth_usable(self):
        rows={f'p::attempt{a:02d}':saved('p',a,a==5) for a in range(1,6)}
        self.assertEqual(short.confirmed_first_four('p',rows),{'state':'exhausted'})


if __name__=='__main__':unittest.main()
