"""New S1 journal failure fixtures; no real symbolic, model or old-data scoring."""
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest

from experiments.learning_regime_p009 import stage1_s1_scoring as s
from tests.test_p009_math_scoring_journal import FakePool, row


def rows():
    return [dict(row('S1::synthetic/'+str(i)), problem_id='synthetic/'+str(i),
        original_gold_row_sha256='a'*64, original_decoded_record_sha256='b'*64)
        for i in range(500)]


class Pool(FakePool):
    def __init__(self, root, deadline):
        super().__init__()


class S1Scoring(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)/'endpoint'
        FakePool.calls = 0

    def tearDown(self):
        self.temp.cleanup()

    def run_once(self, value, factory=Pool):
        return s.score_endpoint_once(self.root, value,
            {'synthetic_fixture_only': True}, 1200, pool_factory=factory)

    def test_complete_roster_reuses_pair_and_never_grants_admission(self):
        out = self.run_once(rows())
        self.assertEqual(out['row_count'], 500)
        self.assertEqual(FakePool.calls, 1)
        self.assertEqual(len(list((self.root/'chunks').glob('*/COMPLETED.json'))), 5)
        self.assertFalse(out['full_runtime_lineage_admission_checked'])
        self.assertFalse(out['scientific_G1_admitted'])
        calls = FakePool.calls
        with self.assertRaises(FileExistsError): self.run_once(rows())
        self.assertEqual(FakePool.calls, calls)

    def test_partial_crash_preserves_known_pairs_and_refuses_any_replay(self):
        value = rows(); value[1]['gold'] = 'crash'
        with self.assertRaises(RuntimeError): self.run_once(value)
        failure = s.read(self.root/'chunks/00000/FAILED.json')
        self.assertEqual(len(failure['unconfirmed_pair_intents']), 1)
        self.assertEqual(len(list((self.root/'pairs').glob('*.json'))), 1)
        calls = FakePool.calls
        with self.assertRaises(FileExistsError): self.run_once(value)
        self.assertEqual(FakePool.calls, calls)

    def test_timeout_failure_is_cached_without_label_repair(self):
        value = rows()
        for r in value: r.update(gold='timeout', answer_segment=r'\boxed{timeout}')
        out = self.run_once(value)
        self.assertEqual(FakePool.calls, 1)
        self.assertEqual(out['correct'], 500)  # Frozen string fallback, not a repair.
        sample = s.read(self.root/'AUDIT_SAMPLES.json')
        self.assertTrue(sample['outer_timeout_over_half_percent'])
        self.assertTrue(sample['fallback_over_two_percent'])
        self.assertFalse(sample['independent_adjudication_complete'])
        self.assertTrue(all(x['adjudication'] is None for x in sample['fallback_sample']))

    def test_wrong_order_cannot_produce_completed_endpoint(self):
        class Reordered(Pool):
            def score_rows(self, value):
                result = super().score_rows(value)
                result['rows'].reverse()
                return result
        with self.assertRaises(ValueError): self.run_once(rows(), Reordered)
        self.assertFalse((self.root/'COMPLETED.json').exists())
        self.assertTrue((self.root/'FAILED.json').exists())

    def test_partial_or_unknown_input_fails_before_a_job_is_created(self):
        bad = rows(); bad[0]['stop_reason'] = 'unknown'
        for value in (rows()[:-1], rows()+[rows()[0]], bad):
            with self.assertRaises(ValueError): self.run_once(value)
        self.assertFalse(self.root.exists())
        self.assertEqual(FakePool.calls, 0)

    def test_source_identity_and_explicit_window_are_required(self):
        bad = rows(); bad[0]['original_decoded_record_sha256'] = 'unknown'
        with self.assertRaises(ValueError): self.run_once(bad)
        for duration in (0, True, 129601):
            with self.assertRaises(ValueError):
                s.score_endpoint_once(self.root, rows(), {'fixture':True}, duration, pool_factory=Pool)
        self.assertFalse(self.root.exists())

    def test_real_persistence_hook_saves_returned_pair_before_deadline_failure(self):
        self.root.mkdir()
        pool = s.DurableEndpointPool(self.root, time.monotonic()-1)
        pair = ('1', '1'); key = s.pair_digest(pair)
        worker = {'task':(key, pair, time.monotonic()), 'process':SimpleNamespace(pid=1)}
        with self.assertRaises(TimeoutError):
            pool._finish(worker, {'status':'compared', 'equivalent':True})
        saved = s.read(self.root/'pairs'/(key+'.json'))
        self.assertEqual(saved['observation'], pool.cache[pair])
        self.assertTrue(saved['observation']['symbolic']['equivalent'])
        self.assertEqual(len(pool.attempts), 1)
        pool.close()


if __name__ == '__main__':
    unittest.main()
