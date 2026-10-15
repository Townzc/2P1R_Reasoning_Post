"""New driver/input integrity fixtures; no actual math-verify or model output."""
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.learning_regime_p009 import p1_input_binding as b
from experiments.learning_regime_p009 import math_scoring_journal as j
from experiments.learning_regime_p009.math_scoring import decide,last_box,VERSIONS
from experiments.learning_regime_p009.math_scoring_pool import pair_digest
from experiments.sft_allocation_midpoint.common import sha
from scripts import p009_p1_driver as d


class FakeSymbolicPool:
    calls=0
    fail=False
    def __init__(self):self.cache={};self.attempts=[];self.row_ids=set()
    def close(self):pass
    def score_rows(self,rows):
        out=[];before=len(self.attempts)
        for row in rows:
            if self.fail:raise RuntimeError('synthetic first100 interruption')
            extracted=last_box(row['answer_segment']);pair=(row['gold'],extracted['answer'])
            if pair not in self.cache:
                type(self).calls+=1
                value=dict(pair_id=pair_digest(pair),symbolic=dict(status='compared',equivalent=pair[0]==pair[1]),
                    elapsed_seconds=.1,attempt_index=len(self.attempts),worker_pid=1)
                self.cache[pair]=value;self.attempts.append(value)
            obs=self.cache[pair]
            out.append(dict(id=row['id'],pair_id=pair_digest(pair),symbolic_attempt=deepcopy(obs),
                score=decide(row['gold'],extracted,obs['symbolic'],stop_reason=row['stop_reason'])))
            self.row_ids.add(row['id'])
        return dict(rows=out,new_symbolic_attempts=len(self.attempts)-before,
            startup_observations=[],call_elapsed_seconds=.1)


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        self.report=self.base/'SYNTHETIC.md';self.report.write_text('Synthetic fixture, not a real review.')
        self.review=dict(scope=d.SCOPE,decision='PASS',report_commit='f'*40,
            report_sha256=sha(self.report),local_report_path=str(self.report),
            conditional_first100_authorized=True,first100_wall_seconds=1200,
            generation_spec_sha256=b.GENERATION_SPEC_SHA,generation_target_commit=b.GENERATION_TARGET,
            source_files={n:sha(n) for n in b.SOURCE_PATHS})
        self.review_path=self.base/'review.json';j.create(self.review_path,self.review)
        self.args=SimpleNamespace(root=str(self.base/'job'),code_review=str(self.review_path),
            generation_root='unused',inputs='unused',generation_admission='unused',timing_review=None)
        FakeSymbolicPool.calls=0;FakeSymbolicPool.fail=False
    def tearDown(self):self.tmp.cleanup()
    def write_review(self,review):
        path=self.base/'altered_review.json';j.create(path,review);return path
    def small_sources(self):
        sources={};gold={}
        for name in b.DATASET_ORDER:
            pid=name+'-p';rid=name+'-r'
            original=dict(candidate_id=rid,problem_id=pid,attempt=1,seed=17,source_row_sha256='a'*64)
            decoded=dict(id=rid,problem_id=pid,attempt=1,seed=17,source_row_sha256='a'*64,
                stop=dict(answer_segment=r'\boxed{1}',stop_reason='native_eos'))
            sources[name]=dict(expected=[original],decoded=[decoded]);gold[pid]=dict(answer='1')
        return sources,gold
    def assemble(self,sources,gold):
        with patch.object(b,'DATASETS',{n:{'n':1} for n in b.DATASET_ORDER}):return b.assemble(sources,gold)
    def freeze_synthetic(self):
        rows=[dict(id=str(i),dataset=b.DATASET_ORDER[0] if i<101 else b.DATASET_ORDER[i-100],
            gold='1' if i<100 else '2',answer_segment=r'\boxed{1}' if i<100 else r'\boxed{2}',
            stop_reason='native_eos') for i in range(104)]
        value=dict(rows=rows,unsupported_gold=[],counts={},generation_proof={},
            generation_spec_sha256=b.GENERATION_SPEC_SHA,generation_runtime_review_sha256='a'*64,
            original_gold_files={})
        with patch.object(d,'bind_complete_generations',return_value=value):d.freeze(self.args)
        return Path(self.args.root)
    def score(self,first):
        with patch.object(d.importlib.metadata,'version',side_effect=lambda n:VERSIONS[n]), \
                patch.object(d,'JournaledPool',side_effect=lambda root,rows,binding:
                    j.JournaledPool(root,rows,binding,pool_factory=FakeSymbolicPool)), \
                patch.object(d,'hard_timer',return_value=SimpleNamespace(cancel=lambda:None)):
            d.score(self.args,first)
    def timing_review(self,root):
        proposal=j.read(root/'FIRST100_PROPOSAL.json')
        value=dict(scope='p009-math-p1-first100-throughput',decision='PASS',report_commit='e'*40,
            local_report_path=str(self.report),report_sha256=sha(self.report),
            proposal_sha256=sha(root/'FIRST100_PROPOSAL.json'),driver_source_files=self.review['source_files'],
            approved_total_wall_seconds=1000,basis_sha256=proposal['basis_sha256'],
            first100_result_sha256=proposal['first100_result_sha256'])
        path=self.base/'timing.json';j.create(path,value);self.args.timing_review=str(path)
    def test_exact_code_review_requires_all_sources_and_generation_release(self):
        self.assertEqual(d.accepted(self.review_path),self.review)
        bad=deepcopy(self.review);bad['source_files'].pop('experiments/learning_regime_p009/math_scoring.py')
        with self.assertRaises(ValueError):d.accepted(self.write_review(bad))
    def test_other_generation_spec_rejected_before_opening_outputs(self):
        p=self.base/'spec.json';j.create(p,{'schema':'obsolete'})
        with self.assertRaises(ValueError):b.bind_complete_generations('missing','missing',p)
    def test_first100_not_authorized_by_generic_code_pass(self):
        bad=deepcopy(self.review);bad['conditional_first100_authorized']=False
        with self.assertRaises(ValueError):d.accepted(self.write_review(bad))
    def test_fixed_order_and_complete_generation_denominators(self):
        src,gold=self.small_sources()
        with self.assertRaises(ValueError):self.assemble(dict(reversed(list(src.items()))),gold)
        src[b.DATASET_ORDER[0]]['decoded']=[]
        with self.assertRaises(ValueError):self.assemble(src,gold)
    def test_changed_seed_or_stop_is_not_silently_scored(self):
        src,gold=self.small_sources();src[b.DATASET_ORDER[0]]['decoded'][0]['seed']=29
        with self.assertRaises(ValueError):self.assemble(src,gold)
        src,gold=self.small_sources();src[b.DATASET_ORDER[0]]['decoded'][0]['stop']['stop_reason']='unknown'
        with self.assertRaises(ValueError):self.assemble(src,gold)
    def test_unsupported_train_gold_excluded_and_counted_not_zero(self):
        src,gold=self.small_sources();gold[b.DATASET_ORDER[0]+'-p']['answer']=None
        result=self.assemble(src,gold)
        self.assertEqual((result['generated_total'],result['scorable_total']), (4,3))
        self.assertEqual(len(result['unsupported_gold']),1)
        self.assertFalse(result['unsupported_test_gold_blocks_G0'])
    def test_unsupported_test_gold_keeps_g0_block_visible(self):
        src,gold=self.small_sources();gold[b.DATASET_ORDER[1]+'-p']['answer']=' '
        self.assertTrue(self.assemble(src,gold)['unsupported_test_gold_blocks_G0'])
    def test_top_level_first100_then_reviewed_suffix_reuses_committed_pairs(self):
        root=self.freeze_synthetic();self.score(True)
        self.assertEqual(FakeSymbolicPool.calls,1)
        self.assertFalse((root/'ALL_ROWS_SCORED.json').exists())
        self.timing_review(root);self.score(False)
        self.assertEqual(FakeSymbolicPool.calls,2)
        result=j.read(root/'ALL_ROWS_SCORED.json')
        self.assertEqual(result['rows'],104);self.assertFalse(result['eligibility_admitted'])
        self.assertFalse(result['G0_admitted']);self.assertFalse(result['independent_adjudication_complete'])
        self.assertEqual(set(j.read(root/'FIXED_AUDIT_SAMPLES.json')),set(b.DATASET_ORDER))
    def test_first100_reentry_stops_before_a_second_attempt(self):
        self.freeze_synthetic();self.score(True);calls=FakeSymbolicPool.calls
        with self.assertRaises(FileExistsError):self.score(True)
        self.assertEqual(FakeSymbolicPool.calls,calls)
    def test_input_mutation_refused_before_first_intent(self):
        root=self.freeze_synthetic();(root/'ROWS.json').write_text('[]')
        with self.assertRaises(ValueError):self.score(True)
        self.assertFalse((root/'FIRST100_STARTED.json').exists());self.assertEqual(FakeSymbolicPool.calls,0)
    def test_failed_first_command_preserves_marker_and_failure_without_retry(self):
        root=self.freeze_synthetic();FakeSymbolicPool.fail=True
        with self.assertRaises(RuntimeError):self.score(True)
        self.assertTrue((root/'FIRST100_STARTED.json').exists())
        self.assertTrue((root/'FIRST100_FAILURE.json').exists())
        with self.assertRaises(FileExistsError):self.score(True)
    def test_unreviewed_remainder_cannot_create_started_marker(self):
        root=self.freeze_synthetic();self.score(True);self.timing_review(root)
        altered=j.read(self.args.timing_review);altered['proposal_sha256']='0'*64
        path=self.base/'bad_timing.json';j.create(path,altered);self.args.timing_review=str(path)
        with self.assertRaises(ValueError):self.score(False)
        self.assertFalse((root/'REMAINDER_STARTED.json').exists())


if __name__=='__main__':unittest.main()
