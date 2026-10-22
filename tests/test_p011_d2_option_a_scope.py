"""New synthetic boundaries for owner D2(a); no production artifacts or models."""
import ast
import tempfile
import unittest
from pathlib import Path
from experiments.p011 import long_d2_scope as scope,long_d2_scope_scoring as scoring
from experiments.sft_allocation_midpoint.common import read,dump


def requests():
    values=[{'id':k} for k in sorted(scope.complete_ids())]
    values += [{'id':f'amc23:{i:04d}:sample:{seed}'} for i in range(40) for seed in range(8)]
    return values


def rows():
    return [dict(id=k,gold='1',answer_segment='\\boxed{1}',stop_reason='native_eos',
                 request_sha256='a'*64,raw_text_sha256='b'*64,region_sha256='c'*64,
                 last_think_boundary_present=False) for k in sorted(scope.complete_ids())]


class ScopeTests(unittest.TestCase):
    def test_exact_roster_and_amc_exclusion(self):
        selected=scope.scoped_requests(requests())
        self.assertEqual(len(selected),2980)
        self.assertFalse(any(r['id'].startswith('amc23:') for r in selected))

    def test_missing_or_duplicate_complete_endpoint_rejected(self):
        for mode in ('duplicate','incomplete'):
            value=requests()
            if mode=='duplicate':value[0]=value[1]
            else:value[0],value[-1]=value[-1],value[0]
            with self.assertRaises(ValueError):scope.scoped_requests(value)

    def test_scoring_scope_and_nonzero_final_chunk(self):
        value=rows();scoring.checked_rows(value)
        result=scoring.checked_summary(value,[{'id':r['id'],'score':{'correct':True}} for r in value])
        self.assertEqual(result['outputs'],2980)
        self.assertEqual(set(result['endpoints']),{'math500_sample','math500_greedy','aime24_sample','aime25_sample'})
        self.assertEqual(len(value[2900:3000]),80)
        with self.assertRaises(ValueError):scoring.checked_rows(value+[dict(value[0],id='amc23:0000:sample:0')])
        tree=ast.parse(Path(scoring.__file__).read_text())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertTrue(any(n.func.id=='min' for n in calls))

    def test_training_view_preserves_failed_original(self):
        with tempfile.TemporaryDirectory() as temp:
            payload=Path(temp)/'original';payload.mkdir()
            dump(payload/'TRAINING_PROCESS_RESULT.json',{'result':{'U':64},'update_seconds':[1.0]*64})
            view=scope.training_view(payload,Path(temp)/'view')
            self.assertFalse((payload/'RESULT.json').exists())
            self.assertTrue(read(view/'RESULT.json')['not_original_worker_result'])
            self.assertTrue((view/'TRAINING_PROCESS_RESULT.json').is_symlink())
            with self.assertRaises(FileExistsError):scope.training_view(payload,view)

    def test_exact_missing_journal_pair_only(self):
        with tempfile.TemporaryDirectory() as temp:
            payload=Path(temp);key='synthetic'
            ledger={k:None for k in scope.original.expected_record_keys(key,'student',64)}
            ledger[key+'/claim']={'id':1}
            for name in scope.original.expected_units('student',64):
                value={'name':name};dump(payload/'intents'/(name+'.json'),value);ledger[key+'/unit/'+name]=value
                if name!='eval_0006':dump(payload/'completed'/(name+'.json'),value);ledger[key+'/done/'+name]=value
            attempts,done=scope.journals(payload,key,ledger)
            self.assertEqual((len(attempts),len(done)),(73,72))
            ledger[key+'/done/update_00001']=None
            with self.assertRaises(ValueError):scope.journals(payload,key,ledger)

    def test_greedy_bridge_uses_original_question_bootstrap(self):
        left={str(i):[False] for i in range(500)};right={str(i):[True] for i in range(500)}
        value=scope.greedy_interval(left,right)
        self.assertEqual(value['actual_model_samples_per_question'],1)
        self.assertEqual(value['additional_model_samples'],0)
        self.assertEqual(value['difference_pp'],100.0)

if __name__=='__main__':unittest.main()
