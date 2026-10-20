"""New synthetic durable-score/provenance tests; no model or math-verify calls."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.p010 import student_scoring as s
from experiments.p010 import student_score_process as process
from experiments.learning_regime_p009.math_scoring import last_box, decide
from experiments.learning_regime_p009.math_scoring_pool import pair_digest


def rows():
    result = []
    for index, job in enumerate(s.evaluation_jobs()):
        for i in range(500):
            answer = '1' if i % (index+2) == 0 else '2'
            result.append(dict(id=job[0]+'::q'+str(i), evaluation=job[0],
                problem_id='q'+str(i), gold='1', answer_segment='\\boxed{'+answer+'}',
                stop_reason='length_cap' if i == 499 else 'native_eos',
                original_gold_row_sha256='a'*64, original_decoded_record_sha256='b'*64))
    return result


class FakePool:
    def __init__(self, root, deadline):
        self.cache = {}; self.ids = set()
    def score_rows(self, rows):
        result = []
        for row in rows:
            assert row['id'] not in self.ids
            self.ids.add(row['id']); answer = last_box(row['answer_segment']); pair = None
            if row['stop_reason'] == 'native_eos' and answer['answer']:
                pair = (row['gold'], answer['answer'])
                if pair not in self.cache:
                    self.cache[pair] = dict(pair_id=pair_digest(pair),
                        symbolic=dict(status='compared', equivalent=pair[0] == pair[1]),
                        elapsed_seconds=.001, attempt_index=len(self.cache), worker_pid=1)
            obs = self.cache[pair] if pair else None
            result.append(dict(id=row['id'], score=decide(row['gold'], answer,
                obs['symbolic'] if obs else {}, stop_reason=row['stop_reason']),
                symbolic_attempt=deepcopy(obs), pair_id=pair_digest(pair) if pair else None))
        return dict(rows=result)
    def close(self):
        pass


def replace(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True)+'\n')


class ScoringChecks(unittest.TestCase):
    def test_all_five_endpoints_mean_not_best_of_four_and_cache_shared(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'score'; original = rows(); binding = {'synthetic': True}
            done = s.score_once(root, original, binding, 60, pool_factory=FakePool)
            before = {str(p): s.sha(p) for p in root.rglob('*') if p.is_file()}
            check = s.verify_saved_scores(root, original, binding, 60)
            self.assertEqual(check['unique_symbolic_pairs'], 2)
            expected = sum(sum(i % (index+2) == 0 for i in range(499)) for index in range(1, 5))/2000
            self.assertEqual(done['sampled_mean_pass_at_1'], expected)
            self.assertEqual(done['endpoints']['greedy']['correct'], 250)
            self.assertFalse(done['independent_adjudication_complete'])
            self.assertEqual(before, {str(p): s.sha(p) for p in root.rglob('*') if p.is_file()})

    def test_resealed_boolean_corruption_cannot_override_original_pair(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'score'; original = rows(); binding = {'synthetic': True}
            s.score_once(root, original, binding, 60, pool_factory=FakePool)
            path = root/'chunks/00000/RESULT.json'; value = s.read(path)
            value['rows'][1]['score']['correct'] = True; replace(path, value)
            p = root/'chunks/00000/COMPLETED.json'; done = s.read(p)
            done['result_sha256'] = s.sha(path); replace(p, done)
            with self.assertRaisesRegex(ValueError, 'Saved frozen decision'):
                s.verify_saved_scores(root, original, binding, 60)

    def test_partial_failure_retained_and_cannot_retry_same_job(self):
        class FailingPool(FakePool):
            def score_rows(self, part):
                if self.ids:
                    raise RuntimeError('synthetic interrupted second chunk')
                return super().score_rows(part)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'score'; original = rows()
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                s.score_once(root, original, {'synthetic': True}, 60, pool_factory=FailingPool)
            self.assertEqual(s.read(root/'FAILED.json')['confirmed_chunk_rows'], 100)
            self.assertTrue((root/'chunks/00000/COMPLETED.json').exists())
            self.assertFalse((root/'COMPLETED.json').exists())
            with self.assertRaises(FileExistsError):
                s.score_once(root, original, {'synthetic': True}, 60, pool_factory=FakePool)

    def test_evaluation_reordering_and_invented_adjudication_rejected(self):
        original = rows(); original[500]['evaluation'] = 'sample3'
        with self.assertRaises(ValueError):
            s.checked_rows(original)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'score'; original = rows()
            s.score_once(root, original, {'synthetic': True}, 60, pool_factory=FakePool)
            p = root/'AUDIT_SAMPLES.json'; sample = s.read(p)
            sample['independent_adjudication_complete'] = True; replace(p, sample)
            with self.assertRaisesRegex(ValueError, 'Saved fixed samples'):
                s.verify_saved_scores(root, original, {'synthetic': True}, 60)

    def test_owned_timeout_is_terminal_no_scoring_retry(self):
        with tempfile.TemporaryDirectory() as d, patch.object(process, 'command',
                return_value=[sys.executable, '-c', 'import time; time.sleep(60)']):
            root = Path(d)/'control'
            with self.assertRaises(Exception):
                process.supervise_once(root, rows(), {'synthetic': True}, 1)
            failed = process.read(root/'FAILED.json'); child = process.read(root/'CHILD.json')
            self.assertFalse(process.group_alive(child['pgid']))
            self.assertFalse(failed['automatic_retry'])
            self.assertFalse((root/'COMPLETED.json').exists())

    def test_owned_child_completion_real_process_without_symbolic_calls(self):
        code = """import sys
from pathlib import Path
from experiments.p010.student_score_process import create,sha
p=Path(sys.argv[1]);(p/'payload').mkdir()
create(p/'payload/COMPLETED.json',{'synthetic_only':True})
create(p/'CHILD_COMPLETED.json',{'intent_sha256':sha(p/'INTENT.json'),'payload_sha256':sha(p/'payload/COMPLETED.json')})
"""
        with tempfile.TemporaryDirectory() as d, patch.object(process, 'command',
                side_effect=lambda root: [sys.executable, '-c', code, str(root)]):
            result = process.supervise_once(Path(d)/'control', rows(), {'synthetic': True}, 10)
            self.assertEqual(result['child_exit_code'], 0)
            self.assertTrue(result['independent_A3_pending'])


if __name__ == '__main__':
    unittest.main()
