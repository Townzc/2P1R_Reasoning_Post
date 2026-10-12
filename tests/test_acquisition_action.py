import unittest
from experiments.sft_allocation_acquisition.policy_runtime import choose_action
from experiments.sft_allocation_acquisition.policy_contract import Policy
from experiments.sft_allocation_acquisition.wallet import Wallet,NS_PER_HOUR

class ActionTests(unittest.TestCase):
    def test_largest_affordable_partial_batch_keeps_order(self):
        p=Policy([str(i) for i in range(40)],1)
        w=Wallet(37,10,9,0)
        prop,reserve=choose_action(p,w,'b',0,NS_PER_HOUR)
        self.assertEqual(prop['new_problem_ids'],['0','1','2'])
        self.assertEqual(reserve['purchase_nanodollars'],27)
        self.assertEqual(p.cursor,3)
    def test_cannot_spend_remaining_credit_on_unbounded_call(self):
        p=Policy(['a'],1);w=Wallet(9,10,0,0)
        self.assertIsNone(choose_action(p,w,'b',0,NS_PER_HOUR))
        self.assertEqual(p.cursor,0)
        self.assertFalse(w.acquired)
    def test_active_parent_requires_no_second_problem_charge(self):
        p=Policy(['a','b'],4);w=Wallet(30,10,20,0)
        prop,_=choose_action(p,w,'a',0,NS_PER_HOUR)
        p.complete('a',[dict(**r,usable=False) for r in prop['items']]);w.settle('a',0)
        prop,res=choose_action(p,w,'b',0,NS_PER_HOUR)
        self.assertEqual(prop['new_problem_ids'],[])
        self.assertEqual(prop['items'],[dict(problem_id='a',attempt=2)])
        self.assertEqual(res['purchase_nanodollars'],0)
    def test_pending_state_is_not_recoverable_permission(self):
        p=Policy(['a'],1);w=Wallet(30,10,0,0)
        choose_action(p,w,'a',0,NS_PER_HOUR)
        with self.assertRaises(ValueError):choose_action(p,w,'b',1,NS_PER_HOUR)

if __name__=='__main__':unittest.main()
