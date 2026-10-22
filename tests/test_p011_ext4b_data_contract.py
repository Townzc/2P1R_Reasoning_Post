import random
import unittest
from experiments.p011 import data_contract as rules
from experiments.p011.ext4b_contract import parent_order, choose_from_cached_census


class NewExt4BDataBoundaries(unittest.TestCase):
    def test_insufficient_or_duplicate_pool_never_shrinks(self):
        with self.assertRaises(ValueError): parent_order([str(x) for x in range(16127)])
        with self.assertRaises(ValueError): parent_order(['same']*16128)

    def test_large_small_are_fixed_nested_and_input_order_independent(self):
        keys=[f'q{x:05d}' for x in range(20000)]
        result=parent_order(keys)
        self.assertEqual(result,parent_order(list(reversed(keys))))
        self.assertEqual(len(result),16128)
        self.assertEqual(len(set(result[:4032])),4032)
        self.assertTrue(set(result[:4032]) < set(result))

    def test_cached_lengths_filter_before_original_first_eligible(self):
        key='question';rows=[{'question':key,'response':r'answer \\boxed{1}','source_row':i} for i in range(4)]
        order=list(range(4));random.Random(rules.identity(key+'p011')[:16]).shuffle(order)
        lengths=[50]*4;lengths[order[0]]=16384
        rows[order[1]]['response']='unfinished'
        census={'parent_sha256':rules.identity(key),'responses':4,'answer_lengths':lengths,
                'eligible_responses':2,'fixed_first_eligible_supervised_tokens':51}
        chosen,n=choose_from_cached_census(key,rows,census,{key:20},1,False)
        self.assertEqual(chosen['source_row'],order[2]);self.assertEqual(n,51)
        with self.assertRaises(ValueError):choose_from_cached_census(key,rows,census,{key:20},1,True)

    def test_census_disagreement_stops_without_an_alternative(self):
        key='question';rows=[{'question':key,'response':r'\\boxed{1}'}]
        census={'parent_sha256':rules.identity(key),'responses':1,'answer_lengths':[50],
                'eligible_responses':1,'fixed_first_eligible_supervised_tokens':52}
        with self.assertRaises(ValueError):choose_from_cached_census(key,rows,census,{key:20},1,False)


if __name__=='__main__':unittest.main()
