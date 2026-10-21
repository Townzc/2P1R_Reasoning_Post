import copy,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from experiments.p011.b_remaining import current_path as path
from experiments.sft_allocation_midpoint.common import digest,sha

SPEC=Path('reports/p011_20261020/b_remaining_current_runtime_v1/SPEC.json')
class TestCurrentAccounting(unittest.TestCase):
 def setUp(self):self.spec=json.loads(SPEC.read_text())
 def test_current_zero_floor_and_stale48_rejection(self):
  self.assertIs(path.validate(self.spec),self.spec)
  self.spec['prospective_students_and_score_window']['B_protected_floor_usd']='48'
  with self.assertRaises(ValueError):path.validate(self.spec)
 def test_erratum_identity_required(self):
  self.spec['delegated_failure_erratum_sha256']='0'*64
  with self.assertRaises(ValueError):path.validate(self.spec)
 def test_fresh_budget_can_end_at_zero_and_reject_old_protection(self):
  job=next(iter(self.spec['jobs'].values()));now=time.time();totals={'A':'5.95','B':'3.01','C':'6.38','D':'0','emergency':'0'}
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'observation.json').write_text('{}\n')
   budget=dict(observed_epoch=now,all_attempted_reservations_usd=totals,category='B',cap_usd='20',overall_cap_usd='180',protected_usd='0',budget_owner_decision_sha256=path.BUDGET_OWNER_SHA,reserve_release_used=False,owner_estimate_used_as_balance=False,availability_basis='owner_current_balance_minus_retained_P011_reserves_and_meter_growth',hourly_rate_usd=job['limits']['hourly_rate_usd'],source_evidence_files={'observation.json':sha(root/'observation.json')},available_after_retained_prior_reserves_usd='3.01',observed_gross_resource_usd='1')
   with patch.object(path.shared,'accounting',return_value=(totals,0)):
    value=path.budget_check(root,self.spec,job,budget,[],{'containers':[],'states':{}},now)
    self.assertEqual(value['protected_usd'],'0');self.assertEqual(value['new_reserved_usd'],'3.01')
    budget['protected_usd']='48'
    with self.assertRaises(ValueError):path.budget_check(root,self.spec,job,budget,[],{'containers':[],'states':{}},now)
 def test_exact_current_review_must_explicitly_accept_erratum(self):
  req=json.loads(Path('reports/p011_20261020/b_remaining_runtime_v1/REVIEW_REQUIREMENTS.json').read_text())
  review=copy.deepcopy(req['binding']);review.update(source_files=self.spec['source_files'],spec_sha256=sha(SPEC),prospective_students_and_score_window_sha256=digest(self.spec['prospective_students_and_score_window']),delegated_failure_erratum_sha256=path.ERRATUM_SHA)
  review.update({k:True for k in req['all_flags_required_true']})
  with patch.object(path.shared,'fixed_report',return_value={'mock_fixed_report':True}):
   with self.assertRaises(ValueError):path.reviewed(self.spec,SPEC,review)
   review['reported_B48_clause_void_current_protected0_accepted']=True
   self.assertEqual(path.reviewed(self.spec,SPEC,review),{'mock_fixed_report':True})

if __name__=='__main__':unittest.main()
