"""New synthetic boundaries only; no original generation/scoring/test is replayed."""
import copy, importlib.util, pathlib, unittest
P=pathlib.Path(__file__).with_name('e3_contract.py')
S=importlib.util.spec_from_file_location('e3_contract_draft',P)
c=importlib.util.module_from_spec(S);S.loader.exec_module(c)

def fixture():
    ids=[f'synthetic/{i:03d}' for i in range(200)]
    roster=dict(problem_ids=ids,new_temperatures=[.6,1.],new_attempts_per_problem=8,
        reused_attempts=list(range(1,9)),reused_temperature=.8)
    groups={}
    for label,temp in c.TEMPERATURES:
        rows=[]
        for pid in ids:
            for attempt in range(1,9):
                old=f'{pid}::attempt{attempt:02d}';s=c.seed_for(old);params=c.sampling({'seed':s});params['temperature']=temp
                rows.append(dict(candidate_id='p010_e3/'+label+'/'+old,original_seed_candidate_id=old,
                    problem_id=pid,attempt=attempt,temperature=temp,model='t72',seed=s,
                    prompt_token_ids=[17,29],sampling=params))
        groups[label]=rows
    return roster,groups

class Boundaries(unittest.TestCase):
    def test_complete_original_roster_and_common_seeds(self):
        self.assertEqual(c.check_rosters(*fixture()),14)
    def test_duplicate_question_rejected(self):
        r,g=fixture();r['problem_ids'][-1]=r['problem_ids'][0]
        with self.assertRaises(ValueError):c.check_rosters(r,g)
    def test_ninth_attempt_rejected(self):
        r,g=fixture();g['t06'][0]['attempt']=9
        with self.assertRaises(ValueError):c.check_rosters(r,g)
    def test_original_temperature_not_regenerated(self):
        r,g=fixture();g['t06'][0]['sampling']['temperature']=.8
        with self.assertRaises(ValueError):c.check_rosters(r,g)
    def test_prompt_context_not_truncated(self):
        r,g=fixture();g['t10'][0]['prompt_token_ids']=list(range(1025))
        with self.assertRaises(ValueError):c.check_rosters(r,g)
    def test_no_implicit_owner_approval(self):
        with self.assertRaises(ValueError):c.validate_allocation({},'synthetic')
    def test_G_transfer_does_not_waive_T72_subcap(self):
        v=dict(scope='p010-E3-original-scope-contingency-to-generation-allocation',approved=True,
            proposal_sha256='synthetic',caps_usd={'G':57,'T':150,'I':15,'C':18},
            total_cap_usd=240,protected_usd=43,T72_selfhosting_total_cap_usd=30,
            old_reserves_retained=True,no_new_scientific_arm=True,reason='synthetic fixture only')
        with self.assertRaises(ValueError):c.validate_allocation(v,'synthetic')
    def test_setup_is_in_initial_scenario(self):
        x=c.forecast(0,0,[],[38.1],457.34,model_loaded=False)
        self.assertGreater(x['projected_total_worker_seconds'],1500)
        self.assertLess(x['projected_total_worker_seconds'],1770)
        self.assertEqual(x['first_paid_measurement_exceptions'],0)
    def test_actual_elapsed_exhaustion_stops_before_next_batch(self):
        with self.assertRaises(TimeoutError):c.forecast(1100,0,[],[38.1],457.34,model_loaded=True)
    def test_slow_new_partial_batch_is_not_ignored(self):
        with self.assertRaises(TimeoutError):c.forecast(200,1,[130],[38.1],457.34,model_loaded=True)
    def test_unacknowledged_timing_cannot_count_as_completed(self):
        with self.assertRaises(ValueError):c.forecast(1,1,[],[38.1],457.34,model_loaded=True)

if __name__=='__main__':unittest.main()
