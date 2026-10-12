import copy
import unittest
from experiments.sft_allocation_acquisition.token_contract import replay, CAP, PRICES, MAX_NEW_TOKENS
from experiments.sft_allocation_acquisition.policy_contract import Policy


class TokenTariffTests(unittest.TestCase):
    def fixture(self,usable=True):
        ids=[str(i) for i in range(1024)];p=Policy(ids,1);batches=[]
        for b in range(20):
            proposal=p.propose();name=f'batch_{b:04d}'
            rows=[dict(**x,candidate_id=f"{x['problem_id']}:{x['attempt']}",
                prompt_tokens=100,stop=dict(token_count=1024),usable=usable)
                for x in proposal['items']]
            p.begin(name,proposal);p.complete(name,rows);batches.append(rows)
        return ids,{x:100 for x in ids},batches

    def test_failed_attempts_are_charged(self):
        ids,pl,b=self.fixture(False);r=replay(ids,pl,b,1,0)
        self.assertEqual(r['charge'],r['attempts']*1124)
        self.assertEqual(r['usable'],0)
        self.assertGreater(r['attempts'],0)
        self.assertEqual(r['stop_reason'],'cannot_reserve_full16_action')
        self.assertLessEqual(r['charge'],CAP)

    def test_price_charges_all_purchased_parents(self):
        ids,pl,b=self.fixture();r=replay(ids,pl,b,1,4)
        self.assertEqual(r['charge'],float(r['attempts']*1124+PRICES[4]*r['acquired']))
        self.assertEqual(MAX_NEW_TOKENS,1024)

    def test_cannot_peek_into_unaffordable_next_action(self):
        ids,pl,b=self.fixture();r=replay(ids,pl,b,1,0)
        corrupt=copy.deepcopy(b);corrupt[r['batches']]=None
        self.assertEqual(replay(ids,pl,corrupt,1,0),r)

    def test_reordered_or_unknown_selected_batch_rejected(self):
        ids,pl,b=self.fixture();bad=copy.deepcopy(b);bad[0].reverse()
        with self.assertRaises(ValueError):replay(ids,pl,bad,1,0)
        bad=copy.deepcopy(b);bad[0][0]['usable']=None
        with self.assertRaises(ValueError):replay(ids,pl,bad,1,0)

    def test_false_token_cost_rejected(self):
        ids,pl,b=self.fixture();bad=copy.deepcopy(b);bad[0][0]['prompt_tokens']=1
        with self.assertRaises(ValueError):replay(ids,pl,bad,1,0)
        bad=copy.deepcopy(b);bad[0][0]['stop']['token_count']=1025
        with self.assertRaises(ValueError):replay(ids,pl,bad,1,0)

if __name__=='__main__':unittest.main()
