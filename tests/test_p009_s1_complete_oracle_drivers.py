"""New outer-driver wiring checks with synthetic files and mocked payload work.

No real answer, binary state, tokenizer or symbolic implementation is executed.
The old payload suites are not repeated. Partial output permanently blocks replay.
"""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from experiments.sft_allocation_midpoint.common import dump, read, sha, digest
from scripts import audit_p009_stage1_s1 as raw
from scripts import score_p009_stage1_s1 as score
from tests.test_p009_s1_complete_admission import fixture


class OuterRawOracle(unittest.TestCase):
    def exercise(self, failed=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); out=root/'new_oracle'; spec,plan,release=fixture()
            evidence=root/'evidence'; inputs=root/'inputs'; inputs.mkdir(); evidence.mkdir()
            dump(evidence/'intent.json',dict(release=release)); dump(root/'receipt.json',{})
            dump(root/'ledger.json',{}); dump(root/'provider.json',{})
            dump(inputs/'S1_ENDPOINT.json',[]); (root/'gold.jsonl').write_text('')
            spec['gold_file_sha256']=sha(root/'gold.jsonl'); spec['base']['files']={}
            args=SimpleNamespace(root=str(evidence), inputs=str(inputs),admission='synthetic',
                run='s1_s17_n400',receipt=str(root/'receipt.json'),ledger=str(root/'ledger.json'),
                provider=str(root/'provider.json'),app_id='ap-synthetic',tokenizer='synthetic',
                gold=str(root/'gold.jsonl'),out=str(out))
            env={'artifact_manifest':{}}; sent={'release':release}
            training=Mock(return_value={'state_sha256':'1'*64})
            endpoint=Mock(side_effect=ValueError('synthetic incomplete raw') if failed else None,
                return_value={'decoded':[],'scoring_rows':[],'logical_stops':{'native_eos':500}})
            tokenizer=SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=Mock(return_value=object())))
            with patch.object(raw,'lineage',return_value=(spec,sent,env,{},{})),patch.object(raw,'verify_training_payload',training),patch.object(raw,'verify_endpoint_payload',endpoint),patch.dict('sys.modules',{'transformers':tokenizer}):
                if failed:
                    with self.assertRaises(ValueError):raw.audit(args)
                    self.assertTrue((out/'FAILED.json').exists())
                    self.assertFalse((out/'COMPLETED.json').exists())
                else:
                    result=raw.audit(args)
                    self.assertFalse(result['symbolic_scoring_performed'])
                    self.assertFalse(result['scientific_G1_admitted'])
                training.assert_called_once();endpoint.assert_called_once()
                with self.assertRaises(FileExistsError):raw.audit(args)
                training.assert_called_once();endpoint.assert_called_once()

    def test_actual_outer_raw_driver_once_then_no_replay(self):self.exercise()
    def test_raw_failure_keeps_partial_and_blocks_second_decode(self):self.exercise(failed=True)


class OuterScoreDriver(unittest.TestCase):
    def exercise(self, corrupted=False, fail_worker=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); generated=root/'generation'; original=root/'evidence'
            generated.mkdir();original.mkdir();spec,plan,release=fixture()
            report=root/'synthetic_runtime_report.md';report.write_text('TEST ONLY - not an acceptance')
            release['runtime_review']['local_report_path']=str(report)
            release['runtime_review']['report_sha256']=sha(report)
            # These objects are intentionally synthetic. Actual validate is tested
            # separately with the complete source/input/NC/proxy/futility binding.
            spec['source_files']={};dump(root/'spec.json',spec)
            dump(original/'intent.json',dict(plan=plan,release=release))
            env=dict(artifact_manifest={'checkpoint_1024/state.pt':{'sha256':'1'*64,'bytes':1}},receipt={'status':'completed'})
            dump(root/'receipt.json',env)
            rows=[dict(id='S1::p'+str(i),problem_id='p'+str(i),gold='1',answer_segment='1',
                stop_reason='native_eos',original_gold_row_sha256='2'*64,
                original_decoded_record_sha256='3'*64) for i in range(500)]
            dump(generated/'SCORING_ROWS.json',rows);dump(generated/'DECODED_ROWS.json',[])
            proof=dict(passed=True,run_id='s1_s17_n400',outputs_decoded=500,technical_unknown=0,
                updates_verified=1024,targets_verified=2097148,spec_sha256=digest(spec),
                source_files=spec['source_files'],artifact_digest=digest(env['artifact_manifest']),
                state_sha256='1'*64,original_intent_file_sha256=sha(original/'intent.json'),
                original_receipt_file_sha256=sha(root/'receipt.json'),
                scoring_rows_file_sha256=sha(generated/'SCORING_ROWS.json'),
                decoded_file_sha256=sha(generated/'DECODED_ROWS.json'),
                full_runtime_lineage_admission_checked=True,symbolic_scoring_performed=False,
                logical_stops={'native_eos':500})
            if corrupted:proof['scoring_rows_file_sha256']='0'*64
            dump(generated/'COMPLETED.json',proof)
            args=SimpleNamespace(admission=str(root/'spec.json'),run='s1_s17_n400',
                generation_oracle=str(generated),evidence=str(original),receipt=str(root/'receipt.json'),out=str(root/'scored'))
            def supervisor(path,values,binding,seconds):
                self.assertEqual(values,rows);self.assertLessEqual(seconds,6000)
                path.mkdir();dump(path/'COMPLETED.json',{'child_exit_code':0})
                if fail_worker:raise RuntimeError('synthetic unconfirmed child')
                dump(path/'payload/COMPLETED.json',{})
                dump(path/'payload/AUDIT_SAMPLES.json',{'outer_timeout_over_half_percent':False,'fallback_over_two_percent':False})
                return {'child_exit_code':0}
            worker=Mock(side_effect=supervisor)
            verified=Mock(return_value=dict(passed=True,correct=1,total=500,
                question_correct={'p'+str(i):i==0 for i in range(500)},unique_symbolic_pairs=1))
            with patch.object(score,'validate',return_value={}),patch.object(score,'supervise_endpoint_once',worker),patch.object(score,'verify_score_payload',verified),patch.object(score.importlib.metadata,'version',side_effect=lambda name:spec['local_scoring_versions'][name]):
                if corrupted or fail_worker:
                    with self.assertRaises((ValueError,RuntimeError)):score.execute(args)
                    if corrupted:
                        worker.assert_not_called();self.assertFalse(Path(args.out).exists())
                    else:
                        self.assertTrue((Path(args.out)/'FAILED.json').exists())
                        with self.assertRaises(FileExistsError):score.execute(args)
                        worker.assert_called_once();verified.assert_not_called()
                else:
                    result=score.execute(args);self.assertEqual(result['correct'],1)
                    self.assertFalse(result['independent_adjudication_complete'])
                    self.assertFalse(result['scientific_G1_admitted'])
                    with self.assertRaises(FileExistsError):score.execute(args)
                    worker.assert_called_once();verified.assert_called_once()

    def test_actual_score_outer_driver_writes_unadjudicated_full_result_once(self):self.exercise()
    def test_corrupt_original_row_binding_blocks_before_scoring(self):self.exercise(corrupted=True)
    def test_partial_scoring_is_preserved_and_cannot_replay(self):self.exercise(fail_worker=True)


if __name__=='__main__':unittest.main()
