import copy
import unittest
from experiments.sft_allocation_p008.procurement import Wallet, pending_union
from experiments.sft_allocation_p008.pool_prefix import restore
from experiments.sft_allocation_p008.contract import stable_seed


def wallets():
    ids=[f'p{i}' for i in range(16)]
    return [Wallet(ids,dict.fromkeys(ids,10),2,b,p,policy)
            for b in (1,8) for p in (0,4) for policy in ('breadth','depth')]


def fixture():
    cache={}
    for i in range(16):
        pid=f'p{i}';cid=f'd2::{pid}::1'
        cache[cid]=dict(problem_id=pid,candidate_id=cid,draw=2,attempt=1,
            seed=stable_seed('teacher',2,pid,1),usable=True,prompt_tokens=10,
            completion_tokens=2,stop=dict(token_count=2),normalized_text_sha256=str(i))
    events={};states={}
    for w in wallets():
        proposal=w.propose();w.begin(proposal)
        done=w.settle([cache[f'd2::{x["problem_id"]}::1'] for x in proposal['action']['items']])
        events[w.name]=[dict(intent=proposal,done=done)]
        next_proposal=w.propose()
        states[w.name]=dict(summary=w.summary(),published_pending=None,next_proposal=next_proposal)
    rec=dict(passed=True,physical_raw_unknown=0,pending_wallets=[],unattempted_pending_candidate_ids=[],
        parent_terminal=dict(status='failed'),physical_attempts=16,physical_batches=1,returned_tokens=32,
        unfinished_wallets=[k for k,v in states.items() if v['next_proposal'] is not None])
    return cache,events,states,rec


class PrefixTest(unittest.TestCase):
    def test_restore_exact_prefix_and_only_future_candidates(self):
        args=fixture();w=wallets();r=restore(w,*args)
        self.assertEqual(r['attempted'],16)
        for item in w:
            p=item.propose()
            if p is not None:item.begin(p)
        missing=pending_union(w,r['cache'])
        self.assertEqual(len(missing),16)
        self.assertTrue(all(x['attempt']==2 and x['candidate_id'] not in r['cache'] for x in missing))
    def test_unknown_parent_rejected(self):
        c,e,s,r=fixture();r['physical_raw_unknown']=1
        with self.assertRaises(ValueError):restore(wallets(),c,e,s,r)
    def test_pending_parent_rejected(self):
        c,e,s,r=fixture();r['pending_wallets']=['x']
        with self.assertRaises(ValueError):restore(wallets(),c,e,s,r)
    def test_missing_return_not_regenerated(self):
        c,e,s,r=fixture();del c[next(iter(c))]
        with self.assertRaises(ValueError):restore(wallets(),c,e,s,r)
    def test_changed_seed_rejected(self):
        c,e,s,r=fixture();c[next(iter(c))]['seed']+=1
        with self.assertRaises(ValueError):restore(wallets(),c,e,s,r)
    def test_changed_charge_rejected(self):
        c,e,s,r=fixture();e[next(iter(e))][0]['done']['charged_units']['numerator']+=1
        with self.assertRaises(ValueError):restore(wallets(),c,e,s,r)
    def test_changed_state_rejected(self):
        c,e,s,r=fixture();s[next(iter(s))]['summary']['acquired_problems']+=1
        with self.assertRaises(ValueError):restore(wallets(),c,e,s,r)
    def test_no_reinitialization_of_used_wallets(self):
        args=fixture();w=wallets();restore(w,*args)
        with self.assertRaises(ValueError):restore(w,*args)


if __name__=='__main__':unittest.main()
