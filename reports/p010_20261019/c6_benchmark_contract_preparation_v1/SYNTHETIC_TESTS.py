import importlib.util,unittest
from pathlib import Path
p=Path('.local/p010_20261019/r1/cue_benchmark_contract_prepared.py')
s=importlib.util.spec_from_file_location('cue_benchmark_draft',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def selected(empty=False):
    c=[dict(candidate=i,eligible=True,token_ids=[] if i==0 else [100+i]) for i in range(21)]
    winner=0 if empty else 1
    return dict(candidates=c,selected_candidate=winner,selected_token_ids=c[winner]['token_ids'],
        gold_used=False,correctness_used=False,test_data_used=False,tie_rule='no-cue then frozen beam rank')

def inputs(task='math',student=False):
    n=500 if task=='math' else 1319;rows=[dict(problem_id=f'{task}/{i}',input_ids=[10,11]) for i in range(n)]
    es=['greedy']+(['sample'+str(i) for i in range(4)] if student else [])
    proofs={e:dict(problem_ids=[r['problem_id'] for r in rows],parameters=m.parameters(task,e),cue_token_ids=[],
        raw_proof_sha256='a'*64,score_proof_sha256='b'*64,complete=True,technical_unknown=0) for e in es}
    return rows,proofs

class BenchmarkContracts(unittest.TestCase):
    def test_original_nonempty_output_counts_and_sample_seeds(self):
        for run,task,student,expected in [('base_math','math',False,4500),('base_gsm','gsm',False,11871),('s1_n400_math','math',True,2500),('t72_n400_math','math',True,2500)]:
            rows,proofs=inputs(task,student);x=m.roster(run,rows,selected(),proofs)
            self.assertEqual(x['new_outputs'],expected)
            self.assertEqual(len({r['candidate_id'] for r in x['rows']}),expected)
            self.assertFalse(any(r['condition']=='no_cue' and r['evaluation']=='greedy' for r in x['rows']))
            for r in x['rows']:
                if r['evaluation'].startswith('sample'):self.assertEqual(r['sampling']['seed'],int(r['evaluation'][-1]))
    def test_empty_winner_reuses_identical_condition(self):
        for run,student,expected in [('base_math',False,2000),('s1_n400_math',True,0)]:
            rows,p=inputs(student=student);x=m.roster(run,rows,selected(True),p)
            self.assertEqual(x['new_outputs'],expected);self.assertEqual(len(x['aliases']),5)
            self.assertTrue(all(r['condition']=='no_cue' for r in x['rows']))
    def test_gold_and_changed_reference_rejected(self):
        rows,p=inputs();rows[0]['gold']='42'
        with self.assertRaises(ValueError):m.roster('base_math',rows,selected(),p)
        rows,p=inputs();p['greedy']['parameters']['max_tokens']=512
        with self.assertRaises(ValueError):m.roster('base_math',rows,selected(),p)
    def test_complete_prompt_never_truncated_for_cue(self):
        rows,p=inputs();rows[0]['input_ids']=[10]*1024
        with self.assertRaises(ValueError):m.roster('base_math',rows,selected(),p)
    def test_unknown_and_malformed_selected_tokens_rejected(self):
        rows,p=inputs();p['greedy']['technical_unknown']=1
        with self.assertRaises(ValueError):m.roster('base_math',rows,selected(),p)
        s=selected();s['selected_token_ids']=[151643];s['candidates'][1]['token_ids']=[151643]
        with self.assertRaises(ValueError):m.checked_selection(s)
    def test_timing_keeps_all_observations_and_actual_elapsed(self):
        x=m.observed_scenario(10,1,[2],[10,20],10,1200)
        self.assertEqual(x['maximum_completed_batch_seconds'],20)
        with self.assertRaises(TimeoutError):m.observed_scenario(500,1,[2],[10,20],10,1200)
        with self.assertRaises(ValueError):m.observed_scenario(0,1,[],[20],10,1200)

if __name__=='__main__':unittest.main()
