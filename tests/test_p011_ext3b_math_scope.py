import tempfile
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from experiments.p011 import ext3b_math_scope as scope,ext3b_math_scoring as scoring
from experiments.p011.owner_0205_common import create,read
from experiments.learning_regime_p009.math_scoring import last_box,decide
from scripts.p011_ext4b_io import failed_payload_once


def roster():
    return [{'id':f'{b}:{i:04d}:{mode}:{seed}'} for b,n in [('math500',500),('aime24',30),('aime25',30),('amc23',40)] for i in range(n) for mode,seeds in ([('sample',range(4)),('greedy',[0])] if b=='math500' else [('sample',range(8))]) for seed in seeds]


def scored_rows(keys):
    return [{'id':f'math500:{i:04d}:{mode}:{seed}','gold':'1','answer_segment':r'\boxed{1}',
        'stop_reason':'length_cap','request_sha256':'a'*64,'raw_text_sha256':'b'*64,'region_sha256':'c'*64,'last_think_boundary_present':True}
        for mode,seed in keys for i in range(500)]


class NoSymbolicPool:
    def __init__(self,*args):self.cache={}
    def score_rows(self,rows):
        return {'rows':[{'id':r['id'],'score':decide(r['gold'],last_box(r['answer_segment']),{},stop_reason=r['stop_reason']),'pair_id':None,'symbolic_attempt':None} for r in rows]}
    def close(self):pass


class MathScopeTests(unittest.TestCase):
    def test_exact_2500_order_preserves_native_objects_and_rejects_roster(self):
        rows=roster();selected=scope.math_requests(rows)
        self.assertEqual(len(selected),2500);self.assertIs(selected[0],rows[4]);self.assertEqual(selected[499]['id'],'math500:0499:greedy:0');self.assertEqual(selected[500]['id'],'math500:0000:sample:0')
        with self.assertRaises(ValueError):scope.math_requests(rows[:-1])
        rows[0]={'id':rows[1]['id']}
        with self.assertRaises(ValueError):scope.math_requests(rows)
    def test_partial_batch_prefix_selects_only_whole_fixed_endpoints(self):
        ids=[r['id'] for r in scope.math_requests(roster())]
        complete,selected=scope.complete_endpoint_ids(ids[:512]);self.assertEqual(complete,[('greedy',0)]);self.assertEqual(len(selected),500)
        complete,selected=scope.complete_endpoint_ids(ids[:2048]);self.assertEqual(len(complete),4);self.assertEqual(len(selected),2000);self.assertNotIn(('sample',3),complete)
        with self.assertRaises(ValueError):scope.complete_endpoint_ids(['amc23:0000:sample:0'])
    def test_complete_group_score_summary_and_missing_primary_not_zero(self):
        rows=scored_rows([('greedy',0),('sample',0)])
        summary=scoring.checked_summary(rows,NoSymbolicPool().score_rows(rows)['rows'])
        self.assertIsNone(summary['primary_mean_pass_at_one']);self.assertEqual(summary['greedy_accuracy'],0)
        self.assertTrue(summary['endpoints']['math500_sample_seed0_descriptive']['descriptive_only'])
        with self.assertRaises(ValueError):scoring.checked_rows(rows[:-1])
        full=scored_rows(scope.ORDER);summary=scoring.checked_summary(full,NoSymbolicPool().score_rows(full)['rows']);self.assertEqual(summary['outputs'],2500);self.assertEqual(summary['endpoints']['math500_sample']['total'],2000)
    def test_new_dynamic500_chunk_journal_once_and_saved_proof(self):
        rows=scored_rows([('greedy',0)])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'score';result=scoring.score_once(p,rows,{'synthetic':True},30,pool_factory=NoSymbolicPool)
            self.assertEqual(result['row_count'],500);proof=scoring.verify_saved_scores(p,rows,{'synthetic':True},30)
            self.assertTrue(proof['passed']);self.assertEqual(proof['new_symbolic_comparisons'],0);self.assertIsNone(proof['primary_mean_pass_at_one'])
            with self.assertRaises(FileExistsError):scoring.score_once(p,rows,{'synthetic':True},30,pool_factory=NoSymbolicPool)
    def test_training_must_complete_and_endpoint_ack_hole_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);key='fixture';ledger={k:None for k in scope.expected_record_keys(key,1)}
            for unit in ['update_00001','terminal_state','terminal_model_export','eval_0000']:
                for folder,stage in [('intents','unit'),('completed','done')]:
                    create(p/folder/(unit+'.json'),{'unit':unit});ledger[key+'/'+stage+'/'+unit]={'unit':unit}
            attempts,done=scope.journals(p,key,1,ledger);self.assertIn('eval_0000',done)
            create(p/'completed/eval_0002.json',{'unit':'eval_0002'});ledger[key+'/done/eval_0002']={'unit':'eval_0002'}
            with self.assertRaises(ValueError):scope.journals(p,key,1,ledger)
            (p/'completed/eval_0002.json').unlink();ledger[key+'/done/eval_0002']=None
            (p/'completed/update_00001.json').unlink();ledger[key+'/done/update_00001']=None
            with self.assertRaises(ValueError):scope.journals(p,key,1,ledger)
    def test_failed_payload_single_stream_keeps_failed_state_without_result(self):
        files={'base/FAILURE.json':b'{"status":"failed"}','base/checkpoint_0001/state.pt':b'final','base/checkpoint_0500/state.pt':b'intermediate','base/raw/eval_0000.json':b'[]'}
        class V:
            def __init__(self):self.reads=[]
            def iterdir(self,*args,**kwargs):return [SimpleNamespace(path=n,size=len(b),type=1,mtime=3) for n,b in files.items()]
            def read_file(self,name):self.reads.append(name);yield files[name.lstrip('/')]
        with tempfile.TemporaryDirectory() as tmp:
            volume=V();out=Path(tmp);payload=failed_payload_once(volume,'/evidence/base',out,1)
            self.assertFalse((payload/'RESULT.json').exists());self.assertEqual(read(payload/'FAILURE.json')['status'],'failed');self.assertEqual(len(volume.reads),3)
            self.assertFalse((payload/'checkpoint_0500/state.pt').exists());self.assertEqual(len(read(out/'PRESERVED_FILES.json')['not_downloaded_still_remote']),1)
    def test_original_scientific_functions_called_not_replaced(self):
        import ast
        tree=ast.parse(Path('scripts/p011_ext4b_io.py').read_text());calls=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertIn('evidence.verify_training',calls);self.assertIn('training_view',calls);self.assertIn('scope.endpoint',calls)
        self.assertNotIn('evidence.verify_endpoint',calls)
        self.assertIn('original.decode_record',Path('experiments/p011/ext3b_math_scope.py').read_text())
        self.assertIn('DurableEndpointPool',scoring.score_once.__kwdefaults__['pool_factory'].__name__)

if __name__=='__main__':unittest.main()
