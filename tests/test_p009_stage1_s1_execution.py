"""New S1 adapter tests; synthetic inputs only, no scoring/model/provider call."""
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from experiments.sft_allocation_midpoint.common import digest, read
from experiments.learning_regime_p009 import stage1_s1_contract as c
from experiments.learning_regime_p009 import stage1_s1_runtime as runtime
from experiments.learning_regime_p009.stage1_endpoint_engine import checked_endpoint


def limits(worker=4000):
    # Synthetic fixture only; never published as a proposed actual slot cap.
    return dict(worker_seconds=worker, platform_seconds=worker+60, startup_seconds=600,
                full_window_seconds=worker+700, reserved_cents=c.cents(worker+700))


def rows():
    result = []
    for i in range(500):
        base = dict(problem_id=f'synthetic/{i:04d}', input_ids=[41, 42])
        result.append(dict(base, candidate_id='S1::'+base['problem_id'],
                           source_row_sha256=digest(base)))
    return result


def raw(part, sampling, ids=None, finish='stop', reason=151643):
    return [dict(row, sampling=sampling, prompt_token_ids=row['input_ids'],
        output_count=1, backend_text='synthetic unscored',
        token_ids=[42, 151643] if ids is None else ids,
        finish_reason=finish, stop_reason=reason) for row in part]


class S1Execution(unittest.TestCase):
    def test_exact_six_registered_recipes_and_explicit_budget(self):
        self.assertEqual(len(c.RUNS), 6)
        for name, (seed, n) in c.RUNS.items():
            recipe = c.recipe(name)
            self.assertEqual((recipe['seed'], recipe['n'], recipe['updates'], recipe['targets']),
                             (seed, n, 1024, 2097148))
        slots = {name: limits() for name in c.RUNS}
        before = c.checked_slot_budget(slots)
        self.assertEqual(before[next(iter(c.RUNS))], 3690)
        self.assertLess(before[list(c.RUNS)[-1]], 3690)
        with self.assertRaises(ValueError): c.recipe('s1_s29_n100')
        with self.assertRaises(ValueError): c.recipe('nc_s17_n400')

    def test_missing_caps_and_six_old_nc_caps_are_not_s1_admission(self):
        with self.assertRaises(ValueError): c.limits_checked({})
        with self.assertRaises(ValueError): c.checked_slot_budget({})
        with self.assertRaises(ValueError):
            c.checked_slot_budget({name: limits(4500) for name in c.RUNS})
        wrong = limits(); wrong['full_window_seconds'] -= 1
        with self.assertRaises(ValueError): c.limits_checked(wrong)

    def test_forecast_uses_slowest_all_intervals_and_no_free_first_batch(self):
        f = c.forecast(0, 64, 2, [1., 3., 2.], [1., 5.], 3690, limits())
        self.assertEqual(f['forecast_remaining_seconds'], 1.2*(3*64+5*2+600))
        self.assertFalse(f['unmeasured_paid_exception'])
        slow = c.forecast(0, 64, 2, [1., 90.], [1., 5.], 3690, limits())
        self.assertFalse(slow['admitted'])
        with self.assertRaises(ValueError): c.forecast(0, 64, 6, [1.], [1.], 3690, limits())
        with self.assertRaises(ValueError): c.forecast(0, 64, 2, [float('nan')], [1.], 3690, limits())

    def test_native_eos_at_1024_preserves_original_length_metadata(self):
        data = rows(); part = data[:1]; sampling = checked_endpoint('S1', data)
        output = raw(part, sampling, [42]*1023+[151643], 'length', None)
        original = deepcopy(output)
        self.assertEqual(c.transport_checked(data, part, output), 1)
        self.assertEqual(output, original)
        self.assertEqual(sampling['max_tokens'], 1024)

    def test_short_stop_foreign_prompt_or_interior_eos_is_rejected(self):
        data = rows(); part = data[:1]; sampling = checked_endpoint('S1', data)
        bad = [raw(part, sampling, [42]*511+[151643], 'length', None),
               raw(part, sampling, [151643, 42], 'stop', 151643),
               raw(part, sampling, [42]*17, 'length', None)]
        changed = raw(part, sampling); changed[0]['prompt_token_ids'] = [42]
        bad.append(changed)
        for output in bad:
            with self.assertRaises(ValueError): c.transport_checked(data, part, output)

    def test_true_1024_cap_without_eos_is_preserved_for_later_logical_scoring(self):
        data = rows(); part = data[:1]; sampling = checked_endpoint('S1', data)
        output = raw(part, sampling, [42]*1024, 'length', None)
        self.assertEqual(c.transport_checked(data, part, output), 1)
        self.assertNotIn(151643, output[0]['token_ids'])

    def exercise_batches(self, malformed=False):
        data = rows(); sampling = checked_endpoint('S1', data)
        responses = [('outputs', raw(data[:256], sampling)),
                     ('outputs', raw(data[256:], sampling))]
        if malformed: responses[0][1][0]['finish_reason'] = 'length'
        class Store(dict):
            def put(self, key, value, skip_if_exists=False):
                if skip_if_exists and key in self: return False
                self[key] = deepcopy(value); return True
        store = Store(); claim = SimpleNamespace(run_id='s1_s29_n3200')
        guard = SimpleNamespace(prefix='synthetic/', check_active=Mock())
        connection = Mock(); process = Mock(); commit = Mock()
        start = runtime.time.time()
        with tempfile.TemporaryDirectory() as folder, patch.object(runtime, 'receive', side_effect=responses):
            args = (data, Path(folder), store, guard, claim, commit, start, start+4000,
                    connection, process, dict(training_block_seconds=[1.], endpoint_batch_seconds=[1.]),
                    [1.]*64, 3690, limits())
            if malformed:
                with self.assertRaises(ValueError): runtime.endpoint_batches(*args)
                self.assertTrue((Path(folder)/'endpoint/raw/00000.json').is_file())
                self.assertFalse((Path(folder)/'completed/endpoint_00000.json').exists())
                self.assertEqual(connection.send.call_count, 1)
            else:
                result = runtime.endpoint_batches(*args)
                self.assertEqual((result['outputs'], result['batches']), (500, 2))
                self.assertEqual([call.args for call in connection.send.call_args_list],
                                 [(('generate', 0),), (('generate', 256),)])
                self.assertEqual(read(Path(folder)/'completed/endpoint_00256.json')['count'], 244)
                with self.assertRaises((FileExistsError, ValueError)):
                    runtime.endpoint_batches(*args)
                self.assertEqual(connection.send.call_count, 2)
            self.assertTrue(all('score' not in value for value in store.values()))

    def test_two_exact_batches_once_with_no_training_or_score_call(self):
        self.exercise_batches()

    def test_malformed_batch_is_saved_without_ack_or_retry(self):
        self.exercise_batches(malformed=True)


if __name__ == '__main__': unittest.main()
