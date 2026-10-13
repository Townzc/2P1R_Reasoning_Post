import unittest
from copy import deepcopy
from experiments.sft_allocation_p008.procurement import Wallet,pending_union,replay

IDS=[f'p{i}' for i in range(80)];L={p:20 for p in IDS}
def returned(item,draw=1,usable=True,tokens=10):
 return dict(**item,candidate_id=f"d{draw}::{item['problem_id']}::{item['attempt']}",usable=usable,prompt_tokens=20,completion_tokens=tokens)

class WalletTest(unittest.TestCase):
 def test_no_output_consumption_without_intent(self):
  w=Wallet(IDS,L,1,1,0,'breadth')
  with self.assertRaises(ValueError):w.settle([])
 def test_cache_does_not_make_policy_free(self):
  b=Wallet(IDS,L,1,1,4,'breadth');d=Wallet(IDS,L,1,1,4,'depth')
  b.begin(b.propose());d.begin(d.propose());missing=pending_union([b,d],{})
  self.assertEqual(len(missing),16)
  rows=[returned(i) for i in b.pending['action']['items']]
  bd=b.settle(rows);dd=d.settle(rows);self.assertEqual(bd['charged_units'],dd['charged_units'])
  self.assertGreater(b.spent,16*30)
 def test_failures_and_duplicates_still_charge(self):
  w=Wallet(IDS,L,1,1,0,'depth');w.begin(w.propose());rows=[returned(i,usable=False) for i in w.pending['action']['items']]
  w.settle(rows);self.assertEqual(w.spent,480);self.assertEqual(w.summary()['usable_answers'],0)
  self.assertTrue(all(i['attempt']==2 for i in w.propose()['action']['items']))
 def test_unknown_remains_unresolved(self):
  w=Wallet(IDS,L,1,1,0,'depth');w.begin(w.propose());rows=[returned(i) for i in w.pending['action']['items']];rows[0]['usable']=None
  with self.assertRaises(ValueError):w.settle(rows)
  self.assertIsNotNone(w.pending)
  with self.assertRaises(ValueError):w.propose()
 def test_no_cheap_known_completion_tail_fitting(self):
  w=Wallet(IDS,L,1,1,0,'breadth');w.spent=w.cap-1000
  self.assertIsNone(w.propose());self.assertEqual(w.stop_reason,'cannot_reserve_full16_action')
 def test_full_replay_and_tampered_payment_rejected(self):
  w=Wallet(IDS,L,1,1,0,'breadth');events=[];cache={}
  while (p:=w.propose()) is not None:
   w.begin(p);rows=[returned(i) for i in p['action']['items']];cache.update({r['candidate_id']:r for r in rows})
   events.append(dict(intent=p,done=w.settle(rows)))
  self.assertEqual(replay(IDS,L,1,1,0,'breadth',events,cache),w.summary())
  bad=deepcopy(events);bad[0]['done']['charged_units']['numerator']-=1
  with self.assertRaises(ValueError):replay(IDS,L,1,1,0,'breadth',bad,cache)
 def test_incomplete_tape_not_marked_complete(self):
  w=Wallet(IDS,L,1,1,0,'breadth');p=w.propose();w.begin(p);rows=[returned(i) for i in p['action']['items']]
  event=dict(intent=p,done=w.settle(rows))
  with self.assertRaises(ValueError):replay(IDS,L,1,1,0,'breadth',[event],{r['candidate_id']:r for r in rows})
 def test_changed_intent_and_cross_draw_rejected(self):
  w=Wallet(IDS,L,1,1,0,'breadth');p=w.propose();bad=deepcopy(p);bad['reserved_units']['numerator']-=1
  with self.assertRaises(ValueError):w.begin(bad)
  w.begin(p)
  with self.assertRaises(ValueError):w.settle([returned(i,draw=2) for i in p['action']['items']])

if __name__=='__main__':unittest.main()
