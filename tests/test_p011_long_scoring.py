"""Only new3300 adapter and mocked supervisor tests, no math-verify processes."""
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from experiments.p011 import long_scoring as s, long_score_process as p
from experiments.p011.long_evaluation import BENCHMARK_COUNTS
from experiments.learning_regime_p009.math_scoring import last_box,decide
from experiments.learning_regime_p009.math_scoring_pool import pair_digest
from experiments.learning_regime_p009.math_scoring_journal import create,read,file_sha


class FakePool:
    calls=0
    def __init__(self,*_):self.cache={};self.attempts=[];self.closed=False
    def score_rows(self,rows):
        FakePool.calls+=1;scored=[]
        for row in rows:
            extracted=last_box(row['answer_segment']);pair=(row['gold'],extracted['answer'])
            has_pair=row['stop_reason']=='native_eos' and bool(extracted['answer'])
            if has_pair and pair not in self.cache:
                obs=dict(pair_id=pair_digest(pair),symbolic={'status':'compared','equivalent':True},
                    elapsed_seconds=.001,attempt_index=len(self.attempts))
                self.cache[pair]=obs;self.attempts.append(obs)
            observation=self.cache[pair] if has_pair else None
            scored.append(dict(id=row['id'],pair_id=pair_digest(pair) if has_pair else None,
                symbolic_attempt=observation,score=decide(row['gold'],extracted,
                    observation['symbolic'] if observation else {},stop_reason=row['stop_reason'])))
        return {'rows':scored}
    def close(self):self.closed=True


class LongScoringChecks(unittest.TestCase):
    def rows(self):
        rows=[]
        for b,n in BENCHMARK_COUNTS.items():
            for i in range(n):
                modes=[('sample',j) for j in range(4 if b=='math500' else 8)]
                if b=='math500':modes.append(('greedy',0))
                for mode,seed in modes:
                    rows.append(dict(id=f'{b}:{i:04d}:{mode}:{seed}',gold='2',answer_segment='\\boxed{2}',
                        stop_reason='length_cap' if b=='math500' and mode=='sample' and seed==3 else 'native_eos',
                        request_sha256='a'*64,raw_text_sha256='b'*64,region_sha256='c'*64,
                        last_think_boundary_present=True))
        return rows

    def test_full3300_journal_cache_and_saved_proof_without_symbolic_replay(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp)/'payload';rows=self.rows();FakePool.calls=0
            saved=s.score_once(root,rows,{'synthetic':True},30,pool_factory=FakePool)
            calls=FakePool.calls
            checked=s.verify_saved_scores(root,rows,{'synthetic':True},30)
            self.assertEqual(calls,33);self.assertEqual(FakePool.calls,calls)
            self.assertEqual(saved['primary_mean_pass_at_one'],.75)
            self.assertEqual(saved['greedy_accuracy'],1.)
            self.assertEqual(saved['unique_symbolic_pairs'],1)
            self.assertFalse(saved['bootstrap_performed']);self.assertFalse(saved['independent_adjudication_complete'])
            self.assertEqual(len(list((root/'chunks').iterdir())),33)
            self.assertEqual(checked['new_symbolic_comparisons'],0)
            with self.assertRaises(FileExistsError):s.score_once(root,rows,{'synthetic':True},30,pool_factory=FakePool)
            self.assertEqual(FakePool.calls,calls)

    def test_missing_row_unknown_stop_and_wrong_hash_rejected_before_job_creation(self):
        for mutation in ('missing','stop','hash'):
            rows=self.rows()
            if mutation=='missing':rows.pop()
            elif mutation=='stop':rows[0]['stop_reason']='new_problem_boundary'
            else:rows[0]['request_sha256']='bad'
            with self.assertRaises(ValueError):s.checked_rows(rows)

    def test_incomplete_scoring_retains_first_chunk_and_blocks_reentry(self):
        class Broken(FakePool):
            def score_rows(self,rows):
                if self.cache:raise RuntimeError('synthetic disconnect')
                return super().score_rows(rows)
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp)/'payload';rows=self.rows()
            with self.assertRaisesRegex(RuntimeError,'disconnect'):
                s.score_once(root,rows,{'synthetic':True},30,pool_factory=Broken)
            self.assertEqual(read(root/'FAILED.json')['confirmed_chunk_rows'],100)
            self.assertTrue((root/'chunks/00000/COMPLETED.json').exists())
            self.assertTrue((root/'chunks/00001/FAILED.json').exists())
            self.assertFalse((root/'COMPLETED.json').exists())
            with self.assertRaises(FileExistsError):s.score_once(root,rows,{'synthetic':True},30,pool_factory=Broken)

    def test_group_summary_is_question_mean_of_four_not_pass_at_four(self):
        rows=self.rows();results=FakePool().score_rows(rows)['rows'];summary=s.checked_summary(rows,results)
        self.assertEqual(summary['endpoints']['math500_sample']['correct'],1500)
        self.assertEqual(summary['endpoints']['math500_sample']['question_correct']['math500:0000'],[True,True,True,False])
        self.assertTrue(summary['endpoints']['aime24_sample']['descriptive_only'])
        self.assertFalse(summary['independent_smoke_selection_performed'])

    def test_unknown_result_is_not_boolean_false(self):
        rows=self.rows();results=FakePool().score_rows(rows)['rows'];results[0]['score']['correct']=None
        with self.assertRaisesRegex(ValueError,'Boolean'):s.checked_summary(rows,results)

    def test_supervisor_full3300_success_keeps_actual_source_binding(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp)/'control'
            class Process:
                pid=999999;returncode=0
                def __init__(self,command,**kw):
                    if kw.get('start_new_session') is not True:raise AssertionError('Owned process group required')
                def wait(self,timeout):
                    (root/'payload').mkdir()
                    create(root/'payload/COMPLETED.json',{'synthetic':True})
                    create(root/'CHILD_COMPLETED.json',dict(intent_sha256=file_sha(root/'INTENT.json'),
                        payload_sha256=file_sha(root/'payload/COMPLETED.json')))
                    return 0
            with patch.object(p.subprocess,'Popen',Process),patch.object(p,'group_alive',return_value=False),patch.object(p,'kill_owned_group',return_value=False):
                result=p.supervise_once(root,self.rows(),{'synthetic':True},30)
            self.assertEqual(result['child_exit_code'],0)
            self.assertEqual(set(read(root/'INTENT.json')['source_files']),set(p.SOURCES))
            with self.assertRaises(FileExistsError):p.supervise_once(root,self.rows(),{'synthetic':True},30)

    def test_supervisor_timeout_records_owned_cleanup_and_no_retry(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp)/'control'
            class Process:
                pid=999999;returncode=-9
                def __init__(self,*_,**kw):pass
                def wait(self,timeout):raise subprocess.TimeoutExpired('synthetic',timeout)
            with patch.object(p.subprocess,'Popen',Process),patch.object(p,'kill_owned_group',return_value=True):
                with self.assertRaises(subprocess.TimeoutExpired):p.supervise_once(root,self.rows(),{'synthetic':True},30)
            failed=read(root/'FAILED.json')
            self.assertTrue(failed['cleanup']['group_signalled']);self.assertFalse(failed['automatic_retry'])
            self.assertFalse((root/'COMPLETED.json').exists())


if __name__=='__main__':unittest.main()
