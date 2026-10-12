import copy
import unittest

from scripts.audit_token_student import endpoint_stop_diagnostics


class TokenEndpointReporting(unittest.TestCase):
    def fixture(self):
        records=[
            {'stop':{'stop_reason':'native_eos'},'task_score':{'task_answer_correct':True}},
            {'stop':{'stop_reason':'length_cap'},'task_score':{'task_answer_correct':False}},
            {'stop':{'stop_reason':'new_problem_boundary'},'task_score':{'task_answer_correct':False}},
        ]
        summary={'n':3,'stop_reasons':{'native_eos':1,'length_cap':1,'new_problem_boundary':1}}
        return records,summary

    def test_truncation_retains_full_denominator_and_wrong_score(self):
        records,summary=self.fixture()
        result=endpoint_stop_diagnostics(records,summary)
        self.assertEqual(result['n'],3)
        self.assertEqual(result['length_cap_outputs'],1)
        self.assertEqual(result['length_cap_fraction'],1/3)
        self.assertEqual(result['length_cap_scored_incorrect'],1)

    def test_cannot_hide_cap_with_changed_summary_or_denominator(self):
        records,summary=self.fixture()
        for field,value in [('n',2),('stop_reasons',{'native_eos':2,'new_problem_boundary':1})]:
            bad=copy.deepcopy(summary);bad[field]=value
            with self.assertRaises(ValueError):endpoint_stop_diagnostics(records,bad)

    def test_correct_or_unknown_cap_is_not_silently_accepted(self):
        for score in (True,None,0):
            records,summary=self.fixture()
            records[1]['task_score']['task_answer_correct']=score
            with self.assertRaises(ValueError):endpoint_stop_diagnostics(records,summary)


if __name__=='__main__':
    unittest.main()
