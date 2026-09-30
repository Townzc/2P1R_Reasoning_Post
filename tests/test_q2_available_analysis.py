import unittest

from experiments.q2_supervision_migration.analyze_available import empirical_bounds,descriptive_difference
from experiments.q2_supervision_migration.contracts import ContractError


def rows(base='pass',extra='pass'):
    return [{'sample_id':str(i),'task_id':'a','base':{'status':base},'extra':{'status':extra}}
            for i in range(8)]


class AvailableAnalysisTests(unittest.TestCase):
    def test_complete_labels_collapse_bounds(self):
        r=empirical_bounds(rows(),['a'])
        self.assertEqual(r['metrics']['union']['percent_bounds'],[100,100])
        self.assertEqual(r['metrics']['pass_at_8']['percent_bounds'],[100,100])

    def test_unknown_is_not_imputed_or_dropped(self):
        data=rows('fail','fail');data[0]['base']['status']='pass';data[0]['extra']['status']='timeout'
        r=empirical_bounds(data,['a'])
        self.assertEqual(r['metrics']['union']['percent_bounds'],[0,12.5])
        self.assertEqual(r['metrics']['pass_at_8']['percent_bounds'],[0,100])
        self.assertEqual(r['recorded_dual_unknown'],1)

    def test_known_union_failure_despite_other_unknown(self):
        r=empirical_bounds(rows('fail','timeout'),['a'])
        self.assertEqual(r['metrics']['union']['percent_bounds'],[0,0])
        self.assertEqual(r['metrics']['extra']['percent_bounds'],[0,100])
        self.assertEqual(r['recorded_dual_unknown'],8)

    def test_unobserved_tasks_keep_original_denominator(self):
        r=empirical_bounds(rows(),['a','b'])
        self.assertEqual(r['metrics']['union']['percent_bounds'],[50,100])
        self.assertEqual(r['metrics']['pass_at_8']['percent_bounds'],[50,100])
        self.assertEqual(r['metrics']['union']['counts']['unobserved'],8)

    def test_duplicate_or_foreign_rows_are_rejected(self):
        data=rows();data[-1]['sample_id']='0'
        with self.assertRaises(ContractError):empirical_bounds(data,['a'])
        with self.assertRaises(ContractError):empirical_bounds(rows(),['b'])

    def test_difference_is_logical_bound_not_confidence_interval(self):
        left=empirical_bounds(rows(),['a']);right=empirical_bounds(rows('pass','timeout'),['a'])
        self.assertEqual(descriptive_difference(left,right)['difference_pp_bounds'],[0,100])


if __name__=='__main__':unittest.main()
