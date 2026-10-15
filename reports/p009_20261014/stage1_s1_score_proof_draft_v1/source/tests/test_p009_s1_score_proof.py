"""Synthetic stored-proof corruption checks; no model, raw or symbolic scoring."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.learning_regime_p009 import stage1_s1_score_proof as p


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n')


def fixture(root):
    rows = [dict(id='S1::fixture/'+str(i), problem_id='fixture/'+str(i), gold='1',
        answer_segment='synthetic boxed text, never extracted', stop_reason='native_eos',
        original_gold_row_sha256='a'*64, original_decoded_record_sha256='b'*64) for i in range(500)]
    binding = {'synthetic_only':True}
    pair = ['1','1']; key = hashlib.sha256(json.dumps(pair,separators=(',', ':')).encode()).hexdigest()
    obs = dict(pair_id=key, symbolic={'status':'compared','equivalent':True},
               worker_pid=1, elapsed_seconds=.1, attempt_index=0)
    score = dict(correct=True, parsed=True, fallback_used=False, teacher_label_eligible=True,
        reasoning_validated=False, extracted_answer='1', symbolic=obs['symbolic'])
    scored = [dict(id=r['id'], score=deepcopy(score), pair_id=key,
                   symbolic_attempt=deepcopy(obs)) for r in rows]
    write(root/'ROWS.json',rows)
    write(root/'INTENT.json',dict(ordered_rows_sha256=p.digest(rows),row_count=500,
        binding=binding,local_seconds=1200,automatic_retry=False,payload_only=True,
        outer_hard_process_cap_required=True))
    write(root/'pairs'/(key+'.json'),dict(pair=pair,observation=obs))
    for i in range(5):
        folder=root/'chunks'/f'{i:05d}'; part=rows[i*100:(i+1)*100]
        write(folder/'INTENT.json',dict(start=i*100,end=(i+1)*100,rows_sha256=p.digest(part),
            row_ids=[r['id'] for r in part], cached_pairs_before=bool(i)*1,
            new_pair_intents={} if i else {key:pair}))
        write(folder/'RESULT.json',dict(rows=scored[i*100:(i+1)*100],new_symbolic_attempts=int(i==0),
            unique_pairs_in_session=1,rows_in_session=(i+1)*100))
        write(folder/'COMPLETED.json',dict(intent_sha256=p.sha(folder/'INTENT.json'),
            result_sha256=p.sha(folder/'RESULT.json'),confirmed_rows=100,technical_unknown=0))
        write(folder/'TIMING.json',dict(elapsed_through_completed_proof_seconds=.2,
                                       final_timing_record_write_excluded=True))
    samples=dict(sample_domain='p009-p1-fixed-audit-sample-v1',independent_adjudication_complete=False,
        eligibility_admitted=False,primary_labels_changed=False,structurally_unsupported_gold_rows=0,
        unsupported_gold_is_not_scored_zero=True,boxed_rows=500,unbraced_boxed_rows=0,
        disagreement_count=0,fallback_rows=0,fallback_over_two_percent=False,
        disagreement_sample=[],fallback_sample=[],unique_pairs=1,outer_timeout_unique_pairs=0,
        outer_timeout_over_half_percent=False)
    write(root/'ALL_SCORED_ROWS.json',scored);write(root/'AUDIT_SAMPLES.json',samples)
    write(root/'COMPLETED.json',dict(row_count=500,question_correct={r['problem_id']:True for r in rows},
        correct=500,unique_symbolic_pairs=1,technical_unknown=0,original_rows_sha256=p.sha(root/'ROWS.json'),
        scored_rows_sha256=p.sha(root/'ALL_SCORED_ROWS.json'),audit_samples_sha256=p.sha(root/'AUDIT_SAMPLES.json'),
        elapsed_before_final_proof_seconds=1.2,payload_only=True,full_runtime_lineage_admission_checked=False,
        external_outcome_review_pending=True,scientific_G1_admitted=False,original_parser_unchanged=True,
        automatic_retry=False,new_model_calls=0))
    return rows,binding


class ScoreProof(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'proof'
        self.rows,self.binding=fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def check(self):
        return p.verify_score_payload(self.root,self.rows,self.binding,1200)

    def test_complete_payload_is_readonly_and_not_scientific_admission(self):
        before={str(f.relative_to(self.root)):p.sha(f) for f in self.root.rglob('*') if f.is_file()}
        value=self.check()
        self.assertEqual(value['complete_rows'],500);self.assertEqual(value['symbolic_calls'],0)
        self.assertFalse(value['full_runtime_lineage_admission_checked'])
        self.assertFalse(value['scientific_G1_admitted'])
        self.assertEqual(before,{str(f.relative_to(self.root)):p.sha(f) for f in self.root.rglob('*') if f.is_file()})

    def test_changed_chunk_is_not_hidden_by_final_table(self):
        f=self.root/'chunks/00001/RESULT.json';v=p.read(f);v['rows'][0]['score']['correct']=False;write(f,v)
        with self.assertRaises(ValueError):self.check()

    def test_duplicate_attempt_or_torn_pair_is_rejected(self):
        f=next((self.root/'pairs').iterdir());v=p.read(f);v['observation']['attempt_index']=1;write(f,v)
        with self.assertRaises(ValueError):self.check()

    def test_resealed_chunk_cannot_forge_cache_history(self):
        folder=self.root/'chunks/00001';v=p.read(folder/'INTENT.json');v['new_pair_intents']={'unknown':['1','1']}
        write(folder/'INTENT.json',v);done=p.read(folder/'COMPLETED.json');done['intent_sha256']=p.sha(folder/'INTENT.json')
        write(folder/'COMPLETED.json',done)
        with self.assertRaises(ValueError):self.check()

    def test_unknown_or_failed_evidence_is_not_complete(self):
        write(self.root/'FAILED.json',{'partial':True})
        with self.assertRaises(ValueError):self.check()

    def test_source_and_window_cannot_be_substituted(self):
        with self.assertRaises(ValueError):p.verify_score_payload(self.root,self.rows,{'other':True},1200)
        with self.assertRaises(ValueError):p.verify_score_payload(self.root,self.rows,self.binding,1201)

    def test_adjudication_must_remain_external_and_actual(self):
        f=self.root/'AUDIT_SAMPLES.json';v=p.read(f);v['independent_adjudication_complete']=True;write(f,v)
        with self.assertRaises(ValueError):self.check()

    def test_helper_has_only_standard_library_imports(self):
        tree=ast.parse(Path(p.__file__).read_text())
        imported={n.name for node in ast.walk(tree) if isinstance(node,ast.Import) for n in node.names}
        imported|={node.module for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)}
        self.assertEqual(imported,{'hashlib','json','math','pathlib'})


if __name__=='__main__':
    unittest.main()
