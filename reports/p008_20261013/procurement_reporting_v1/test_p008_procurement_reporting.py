import copy
import unittest
from fractions import Fraction

from scripts.p008_procurement_reporting import encoded, wallet_row, overlap_row


class ReportingChecks(unittest.TestCase):
    def fixture(self):
        rows = [dict(candidate_id=str(i), problem_id='p'+str(i//2), usable=i==0,
                     clean_correct=i<2, usable_duplicate_of='0' if i==1 else None,
                     duplicate_of='0' if i==1 else None, truncated=i==2,
                     prompt_tokens=10, completion_tokens=20+i) for i in range(3)]
        fee = 8*Fraction(191151,512); charge = fee+93; cap = Fraction(4000)
        summary = dict(wallet='d1_b8_p4_depth',consumed_candidate_ids=['0','1','2'],
                       attempted_candidates=3,accepted_candidate_ids=['0'],acquired_problems=2,
                       covered_parents=1,zero_usable_parents=1,charge=encoded(charge),cap=encoded(cap),
                       unused_fraction=encoded((cap-charge)/cap),usable_answers=1,unknown=0,
                       unresolved_batch=False,pool_exhausted=False,stop_reason='cannot_reserve_full16_action')
        events=[dict(intent=dict(action=dict(new_problem_ids=['p0','p1'])),
                     done=dict(candidate_ids=['0','1','2'],charged_units=encoded(charge)))]
        return summary, events, {r['candidate_id']:r for r in rows}

    def test_failed_and_duplicate_attempts_are_fully_charged(self):
        s,e,c=self.fixture();r=wallet_row(s,e,c)
        self.assertEqual(r['charged_prompt_tokens'],30)
        self.assertEqual(r['charged_returned_tokens_including_eos'],63)
        self.assertEqual(r['unusable_attempts'],2)
        self.assertEqual(r['of_which_rejected_valid_duplicates'],1)
        self.assertEqual(r['other_frozen_primary_unusable'],1)
        self.assertEqual(r['unused_units'],encoded(Fraction(4000)-8*Fraction(191151,512)-93))

    def test_overlap_distinguishes_purchased_from_usable(self):
        s,e,c=self.fixture();a=wallet_row(s,e,c);b=copy.deepcopy(a);b['draw']=2
        b['purchased_problem_ids']=['p1','p2'];b['usable_problem_ids']=['p1']
        self.assertEqual(overlap_row(a,b,'purchased_problem_ids')['intersection_count'],1)
        self.assertEqual(overlap_row(a,b,'purchased_problem_ids')['jaccard'],1/3)
        self.assertEqual(overlap_row(a,b,'usable_problem_ids')['intersection_count'],0)

    def test_reject_inconsistent_charge_and_missing_candidate(self):
        s,e,c=self.fixture();s['charge']['numerator']+=1
        with self.assertRaises(AssertionError):wallet_row(s,e,c)
        s,e,c=self.fixture();del c['2']
        with self.assertRaises(KeyError):wallet_row(s,e,c)


if __name__=='__main__':unittest.main()
