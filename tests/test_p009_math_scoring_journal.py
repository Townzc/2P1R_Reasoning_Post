"""New durable-journal fixtures only; no real math-verify or generated output."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from experiments.learning_regime_p009 import math_scoring_journal as j
from experiments.learning_regime_p009.math_scoring import decide, last_box
from experiments.learning_regime_p009.math_scoring_pool import pair_digest


def row(i, gold='1', answer='1', stop='native_eos'):
    return dict(id=str(i), gold=gold, answer_segment='\\boxed{'+answer+'}',stop_reason=stop,
                original_raw_sha256='a'*64)


class FakePool:
    calls = 0
    def __init__(self):
        self.cache={}; self.attempts=[]; self.row_ids=set(); self.closed=False
    def score_rows(self, rows):
        result=[]; before=len(self.attempts)
        for row in rows:
            extracted=last_box(row['answer_segment']);pair=None
            if row['stop_reason'] in ('native_eos','new_problem_boundary') and extracted['answer']:
                pair=(row['gold'],extracted['answer'])
                if pair not in self.cache:
                    FakePool.calls+=1
                    if pair[0]=='crash': raise RuntimeError('synthetic interrupted work')
                    status='outer_timeout' if pair[0]=='timeout' else 'compared'
                    symbolic=dict(status=status,equivalent=None if status=='outer_timeout' else pair[0]==pair[1])
                    obs=dict(pair_id=pair_digest(pair),symbolic=symbolic,worker_pid=1,
                             elapsed_seconds=.1,attempt_index=len(self.attempts))
                    self.cache[pair]=obs;self.attempts.append(obs)
            obs=self.cache[pair] if pair else None
            result.append(dict(id=row['id'],score=decide(row['gold'],extracted,
                obs['symbolic'] if obs else {},stop_reason=row['stop_reason']),
                symbolic_attempt=deepcopy(obs),pair_id=pair_digest(pair) if pair else None))
            self.row_ids.add(row['id'])
        return dict(rows=result,new_symbolic_attempts=len(self.attempts)-before,
                    startup_observations=[],call_elapsed_seconds=.1)
    def close(self): self.closed=True


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'job';FakePool.calls=0
    def tearDown(self): self.temp.cleanup()
    def session(self,rows): return j.JournaledPool(self.root,rows,{'exact_source':'b'*64},pool_factory=FakePool)
    def review(self, session):
        report=Path(self.temp.name)/'MOCK_REPORT.md';report.write_text('synthetic fixture, never actual acceptance')
        return dict(scope='p009-math-p1-first100-throughput',decision='PASS',
            basis_sha256=j.digest(session.basis),
            first100_result_sha256=j.file_sha(self.root/'chunks/00000/RESULT.json'),
            report_commit='c'*40,local_report_path=str(report),report_sha256=j.file_sha(report))
    def test_complete_reopen_reuses_pairs_and_does_not_repeat_rows(self):
        rows=[row(i) for i in range(102)]
        with self.session(rows) as s:
            s.score_next(100); self.assertEqual(FakePool.calls,1)
        with self.session(rows) as s:
            with self.assertRaises(ValueError):s.score_next(2)
            result=s.score_next(2,timing_review=self.review(s))
            self.assertEqual(result['new_symbolic_attempts'],0)
            self.assertEqual(FakePool.calls,1)
            with self.assertRaises(ValueError):s.score_next(1,timing_review=self.review(s))
    def test_first100_order_and_binding_are_fixed(self):
        rows=[row(i) for i in range(101)]
        with self.session(rows) as s:
            with self.assertRaises(ValueError):s.score_next(50)
            s.score_next(100)
        rows[-1]['answer_segment']='changed'
        with self.assertRaises(ValueError):self.session(rows)
    def test_failed_chunk_preserves_known_pairs_and_unknowns_blocks_reentry(self):
        rows=[row(1),row(2,gold='crash')]
        with self.assertRaises(RuntimeError):
            with self.session(rows) as s:s.score_next(2)
        failed=j.read(self.root/'chunks/00000/FAILED.json')
        self.assertEqual(len(failed['unconfirmed_pair_intents']),1)
        self.assertFalse(failed['retry_authorized'])
        attempts=FakePool.calls
        with self.assertRaises(ValueError):self.session(rows)
        self.assertEqual(FakePool.calls,attempts)
    def test_torn_pair_or_commit_never_triggers_a_new_attempt(self):
        rows=[row(1)]
        with self.session(rows) as s:s.score_next(1)
        pair=next((self.root/'pairs').glob('*.json'));pair.write_text('{')
        with self.assertRaises(ValueError):self.session(rows)
        self.assertEqual(FakePool.calls,1)
    def test_timed_out_pair_cached_with_original_failure(self):
        rows=[row(i,gold='timeout',answer='timeout') for i in range(101)]
        with self.session(rows) as s:s.score_next(100)
        with self.session(rows) as s:
            result=s.score_next(1,timing_review=self.review(s))
            self.assertEqual(result['rows'][0]['score']['status'],'outer_timeout')
            self.assertTrue(result['rows'][0]['score']['fallback_used'])
            self.assertEqual(FakePool.calls,1)
    def test_concurrent_holder_refused_and_lock_released(self):
        rows=[row(1)]
        with self.session(rows):
            with self.assertRaises(BlockingIOError):self.session(rows)
        with self.session(rows) as s:s.score_next(1)
    def test_bad_rows_rejected_before_directory_or_calls(self):
        for rows in ([row(1),row(1)], [row(1,gold='')], [row(1,stop='unknown')]):
            with self.assertRaises(ValueError):self.session(rows)
        self.assertFalse(self.root.exists());self.assertEqual(FakePool.calls,0)
    def test_real_first100_forecast_separates_cache_from_new_attempts(self):
        rows=[row(i) for i in range(100)]+[row(100,gold='2',answer='2')]
        with self.session(rows) as s:
            result=s.score_next(100)
            out=j.first100_forecast(s.basis,result,j.read(self.root/'chunks/00000/TIMING.json'),rows)
            self.assertEqual(out['unique_observed_pairs'],1)
            self.assertEqual(out['remaining_distinct_pairs'],1)
            self.assertFalse(out['runtime_admitted']);self.assertFalse(out['calibrated_bound'])
    def test_no_new_pair_measurement_cannot_forecast_future_pairs(self):
        rows=[row(i,stop='length_cap') for i in range(100)]+[row(100)]
        with self.session(rows) as s:
            result=s.score_next(100)
            with self.assertRaises(ValueError):j.first100_forecast(s.basis,result,
                j.read(self.root/'chunks/00000/TIMING.json'),rows)
    def test_audit_samples_fixed_all_rows_no_adjudication_or_label_change(self):
        rows=[row(i,gold='timeout',answer='timeout') if i<3 else row(i) for i in range(100)]
        with self.session(rows) as s:results=s.score_next(100)['rows']
        report=j.audit_samples(rows,results)
        self.assertTrue(report['fallback_over_two_percent']);self.assertEqual(len(report['fallback_sample']),3)
        self.assertTrue(report['outer_timeout_over_half_percent'])
        self.assertFalse(report['independent_adjudication_complete']);self.assertFalse(report['eligibility_admitted'])
        self.assertTrue(all(x['adjudication'] is None for x in report['fallback_sample']))
        with self.assertRaises(ValueError):j.audit_samples(rows,results[:-1])
    def test_exact_create_only_and_result_corruption_block(self):
        rows=[row(1)]
        with self.session(rows) as s:s.score_next(1)
        with self.assertRaises(FileExistsError):j.create(self.root/'BASIS.json',{})
        p=self.root/'chunks/00000/RESULT.json';p.write_text('{}')
        with self.assertRaises((KeyError,ValueError)):self.session(rows)


if __name__=='__main__':unittest.main()
