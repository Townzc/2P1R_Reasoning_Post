"""New B-only integration fixtures; no old test methods or actual model/scorer."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.p011 import b_generation_loader as l, b_scoring as s, b_score_process as p
from experiments.p010.teacher_contract import canonical_request
from experiments.sft_allocation_midpoint.common import digest
from tests.test_p011_long_scoring import FakePool


def inputs():
    ids=[f'q{i:04d}' for i in range(400)]
    return l.original_inputs({'s1':{'400':ids}},
        [{'problem_id':pid,'problem':'p','solution':'\\boxed{2}'} for pid in ids],
        [canonical_request(pid,2,'t15',[1,2,3]) for pid in ids])


def records(pack):
    raw=[];decoded=[]
    for i,r in enumerate(pack['rows']):
        req=r['request'];x={'candidate_id':req['candidate_id'],'problem_id':req['problem_id'],
            'sampling':r['sampling'],'token_ids':[2,151645]}
        stop={'answer_segment':'\\boxed{2}', 'stop_reason':'native_eos' if i%16 else 'length_cap'}
        raw.append(x);decoded.append({'raw_record_sha256':digest(x),
            'answer_text':stop['answer_segment'],'stop':stop,'transport':{}})
    return raw,decoded


class NewBIntegration(unittest.TestCase):
    def test_input_projection_original_order_tokens_and_common_seeds(self):
        pack=inputs();self.assertEqual(len(pack['rows']),6400)
        self.assertEqual(pack['rows'][1]['request']['seed'],canonical_request('q0000',2,'t15',[1,2,3])['seed'])
        self.assertEqual(pack['rows'][1]['sampling']['temperature'],1.)
        self.assertEqual(pack['new_token_encodings'],0)
        self.assertEqual(pack['original_outputs_read_or_scored'],0)

    def test_conflicting_original_native_prompt_is_not_silently_reencoded(self):
        ids=[f'q{i}' for i in range(400)]
        src=[{'problem_id':pid,'problem':'p','solution':'\\boxed{2}'} for pid in ids]
        req=[canonical_request(pid,2,'t15',[1]) for pid in ids]
        req.append(canonical_request(ids[0],3,'t15',[2]))
        with self.assertRaisesRegex(ValueError,'prompt'):l.original_inputs({'s1':{'400':ids}},src,req)

    def test_native_prompt_mismatch_fails_before_model(self):
        class Tok:
            def apply_chat_template(self,*_,**kw):return [99]
        with self.assertRaisesRegex(ValueError,'prompt'):l.check_native_prompts(Tok(),inputs())

    def test_missing_asset_writer_rejects_before_file_or_weight_read(self):
        with self.assertRaisesRegex(ValueError,'writer'):
            l.checked_assets({'model_id':l.MODELS['t15'][0],'revision':l.MODELS['t15'][1],'files':{'x':{}},'remote_path':'absent'})

    def test_raw_hash_or_temperature_change_blocks_score_adapter(self):
        pack=inputs();raw,decoded=records(pack)
        for field in ('hash','temperature'):
            x=copy.deepcopy(raw);d=copy.deepcopy(decoded)
            if field=='hash':d[0]['raw_record_sha256']='0'*64
            else:x[0]['sampling']['temperature']=.8
            with self.assertRaises(ValueError):l.score_rows(pack,x,d)

    def test_complete64chunk_journal_saved_replay_and_no_repeat(self):
        pack=inputs();raw,decoded=records(pack);rows=l.score_rows(pack,raw,decoded)
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp)/'score';FakePool.calls=0
            result=s.score_once(root,rows,{'synthetic':True},30,pool_factory=FakePool)
            self.assertEqual(result['correct'],6000);self.assertEqual(FakePool.calls,64)
            proof=s.verify_saved_scores(root,rows,{'synthetic':True},30)
            self.assertEqual(proof['new_symbolic_comparisons'],0);self.assertEqual(FakePool.calls,64)
            with self.assertRaises(FileExistsError):s.score_once(root,rows,{'synthetic':True},30,pool_factory=FakePool)

    def test_boolean_unknown_or_attempt_reorder_is_not_false(self):
        pack=inputs();raw,decoded=records(pack);rows=l.score_rows(pack,raw,decoded)
        rows[0],rows[1]=rows[1],rows[0]
        with self.assertRaises(ValueError):s.checked_rows(rows)
        rows[0],rows[1]=rows[1],rows[0]
        results=FakePool().score_rows(rows)['rows'];results[0]['score']['correct']=None
        with self.assertRaises(ValueError):s.checked_summary(rows,results)

    def test_selection_binds_saved_order_firstusable16_without_rescoring(self):
        pack=inputs();raw,decoded=records(pack);rows=l.score_rows(pack,raw,decoded)
        scored=FakePool().score_rows(rows)['rows'];calls=FakePool.calls
        saved,selection=l.selected_records(pack,raw,decoded,scored)
        self.assertEqual(FakePool.calls,calls);self.assertEqual(len(saved),6400)
        self.assertEqual(selection['selected_ids']['1'][0],'q0000::attempt02')
        self.assertFalse(selection['training_admitted'])

    def test_supervisor_uses_B_source_and_rejects_undersized_roster_before_creation(self):
        self.assertEqual(p.MODULE,'experiments.p011.b_score_process')
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp)/'control'
            with self.assertRaises(ValueError):p.supervise_once(root,[{}]*6399,{'fixture':True},30)
            self.assertFalse(root.exists())

    def test_scoring_failure_retains_confirmed_chunks_and_blocks_retry(self):
        pack=inputs();raw,decoded=records(pack);rows=l.score_rows(pack,raw,decoded)
        class Broken(FakePool):
            def score_rows(self,rows):
                if self.cache:raise RuntimeError('new B synthetic failure')
                return super().score_rows(rows)
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp)/'score'
            with self.assertRaises(RuntimeError):s.score_once(root,rows,{'synthetic':True},30,pool_factory=Broken)
            self.assertTrue((root/'chunks/00000/COMPLETED.json').exists())
            self.assertTrue((root/'FAILED.json').exists());self.assertFalse((root/'COMPLETED.json').exists())
            with self.assertRaises(FileExistsError):s.score_once(root,rows,{'synthetic':True},30,pool_factory=Broken)

if __name__=='__main__':unittest.main()
