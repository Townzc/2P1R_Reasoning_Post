"""New transport/persistence fixtures only; no real model, scoring or old tests."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from experiments.sft_allocation_midpoint.common import digest, read
from experiments.learning_regime_p009 import stage0_generation_contract as c
from experiments.learning_regime_p009 import stage0_generation_runtime as rt
from experiments.learning_regime_p009.stage0_generation_engine import returned_records

TMP = Path('.local/p009_20261014/r1')


def endpoint(name):
    ds = c.DATASETS[name]
    return dict(n=ds['n'], max_context=2048, max_new_tokens=ds['max_new_tokens'],
        eos_token_id=c.MODELS[ds['model']]['eos_token_ids'][0],
        prompts=[dict(problem_id=f'fixture/{i}', input_ids=[12, 13]) for i in range(ds['n'])])


def rows(name):
    return c.normalize_rows(name, endpoint(name))


def response(name, row, ids=None, finish='stop', reason=None):
    if ids is None:
        ids = [20, c.MODELS[c.DATASETS[name]['model']]['eos_token_ids'][0]]
    return dict(candidate_id=row['candidate_id'], problem_id=row['problem_id'],
        source_row_sha256=row['source_row_sha256'], sampling=c.sampling(name, row),
        prompt_token_ids=row['input_ids'], token_ids=ids, backend_text='fixture',
        output_count=1, finish_reason=finish, stop_reason=reason)


class Store(dict):
    def put(self, key, value, skip_if_exists=False):
        if skip_if_exists and key in self:
            return False
        self[key] = deepcopy(value)
        return True


class GenerationTests(unittest.TestCase):
    def test_separate_full_window_reserves_keep_all_old_allowances(self):
        self.assertEqual([c.slot_checked(n)['reserved_cents'] for n in c.SLOTS], [399, 216, 252])
        self.assertEqual(c.PRIOR_RESERVED_CENTS+sum(s['reserved_cents'] for s in c.SLOTS.values()), 1871)
        self.assertEqual(c.STAGE0_CAP_CENTS-1871, 129)
        self.assertFalse(any('gsm' in n for n in c.SLOTS['qwen_p3']['datasets']))

    def test_complete_roster_and_context_before_generation(self):
        d = endpoint('qwen_math_zero'); d['prompts'][0]['input_ids'] = [12]*1025
        with self.assertRaises(ValueError): c.normalize_rows('qwen_math_zero', d)
        d = endpoint('qwen_math_zero'); d['prompts'].pop()
        with self.assertRaises(ValueError): c.normalize_rows('qwen_math_zero', d)

    def test_duplicate_ids_cannot_receive_another_attempt(self):
        d = endpoint('olmo_gsm_zero'); d['prompts'][1] = deepcopy(d['prompts'][0])
        with self.assertRaises(ValueError): c.normalize_rows('olmo_gsm_zero', d)

    def test_teacher_request_seeds_and_sampling_are_not_greedy_endpoint(self):
        fixture = [dict(candidate_id=f'math/fixture/{i}::attempt01', problem_id=f'math/fixture/{i}',
                        attempt=1, seed=100+i, prompt_token_ids=[12]) for i in range(8993)]
        rr = c.normalize_rows('math_procurement', fixture)
        self.assertEqual([r['seed'] for r in rr[:2]], [100, 101])
        self.assertEqual(rr[0]['source_row_sha256'], digest(fixture[0]))
        p = c.sampling('math_procurement', rr[0])
        self.assertEqual((p['temperature'], p['top_p'], p['max_tokens'], p['stop_token_ids']),
                         (.8, .95, 1024, [151645, 151643]))
        e = c.sampling('teacher_gsm_zero', rows('teacher_gsm_zero')[0])
        self.assertEqual((e['temperature'], e['top_p'], e['max_tokens'], e['seed']), (0, 1, 512, 17))

    def test_teacher_native_eos_at_exact_cap_preserved(self):
        row = dict(candidate_id='x::attempt01', problem_id='x', seed=29,
                   attempt=1, input_ids=[12], source_row_sha256='a'*64)
        for eos in (151643, 151645):
            raw = response('math_procurement', row, [12]*1023+[eos], 'length')
            before = deepcopy(raw)
            self.assertEqual(c.transport_checked('math_procurement', [row], [raw]), 1)
            self.assertEqual(raw, before)
            raw['token_ids'] = [12]*1022+[eos]
            with self.assertRaises(ValueError): c.transport_checked('math_procurement', [row], [raw])

    def test_interior_eos_and_wrong_stop_reason_rejected(self):
        row = rows('teacher_math_zero')[0]
        for ids, reason in [([151645, 12, 151643], None), ([12, 151645], 151643)]:
            raw = response('teacher_math_zero', row, ids, reason=reason)
            with self.assertRaises(ValueError): c.transport_checked('teacher_math_zero', [row], [raw])

    def test_olmo_own_vocab_and_native_eos_at_cap(self):
        row = rows('olmo_gsm_zero')[0]
        raw = response('olmo_gsm_zero', row, [20]*511+[100257], 'length')
        c.transport_checked('olmo_gsm_zero', [row], [raw])
        raw['token_ids'][-1] = 151643
        with self.assertRaises(ValueError): c.transport_checked('olmo_gsm_zero', [row], [raw])

    def test_short_unknown_stop_and_boolean_token_never_zero_filled(self):
        row = rows('qwen_math_zero')[0]
        for ids, finish in [([20], 'length'), ([True, 151643], 'stop'), ([], 'stop')]:
            raw = response('qwen_math_zero', row, ids, finish)
            with self.assertRaises(ValueError): c.transport_checked('qwen_math_zero', [row], [raw])

    def test_changed_prompt_or_seed_rejected(self):
        row = rows('qwen_math_zero')[0]
        raw = response('qwen_math_zero', row); raw['sampling']['seed'] = 18
        with self.assertRaises(ValueError): c.transport_checked('qwen_math_zero', [row], [raw])
        raw = response('qwen_math_zero', row); raw['prompt_token_ids'] = [14]
        with self.assertRaises(ValueError): c.transport_checked('qwen_math_zero', [row], [raw])

    def test_backend_invalid_shapes_retained_before_rejection(self):
        row = rows('qwen_math_zero')[0]
        answer = NS(token_ids=[20, 151643], text='fixture', finish_reason='stop', stop_reason=None)
        output = NS(prompt_token_ids=row['input_ids'], outputs=[answer, answer])
        raw = returned_records([row], [c.sampling('qwen_math_zero', row)], [output, output])
        self.assertEqual(len(raw), 2)
        self.assertEqual(len(raw[0]['invalid_shape_original_answers']), 2)
        self.assertIsNone(raw[1]['candidate_id'])
        with self.assertRaises(ValueError): c.transport_checked('qwen_math_zero', [row], raw[:1])

    def test_slowest_batch_actual_setup_and_invalid_times(self):
        self.assertTrue(c.remaining_forecast('qwen_p3', 10, [1], 3)['admitted'])
        self.assertFalse(c.remaining_forecast('qwen_p3', 600, [1], 3)['admitted'])
        result = c.remaining_forecast('teacher_p2_p3', 100, [1, 60, 2], 41)
        self.assertEqual(result['full_batch_max_seconds'], 60)
        self.assertFalse(result['admitted'])
        for bad in (float('nan'), float('inf'), -1):
            with self.assertRaises(ValueError): c.remaining_forecast('qwen_p3', bad, [1], 3)

    def flow(self, *, lost=False, invalid=False, deny=False, prior=False):
        with tempfile.TemporaryDirectory(dir=TMP, prefix='stage0_mock_') as d:
            out = Path(d); data = {n:rows(n) for n in c.SLOTS['qwen_p3']['datasets']}
            store = Store(); prefix = 'midpoint/mock/'; generated = []; pending = []
            key = prefix+'qwen_p3'
            if prior:
                store[key+'/unit/qwen_math_zero_00000'] = {'uncertain': True}
            class Conn:
                def send(self, message):
                    _, payload = message; pending[:] = [payload]
                    generated.append((payload['dataset'], [r['candidate_id'] for r in payload['rows']]))
            def recv(*args):
                if lost: raise ConnectionError('Response lost; no retry')
                p = pending.pop(); raw = [response(p['dataset'], r) for r in p['rows']]
                if invalid: raw[0]['token_ids'] = []
                return 'outputs', raw
            guard = NS(prefix=prefix, check_active=lambda *a, **k: None)
            claim = NS(run_id='qwen_p3'); started = time.time()
            error = None; result = None
            forecast = rt.remaining_forecast
            def gate(*args):
                value = forecast(*args)
                if deny: value['admitted'] = False
                return value
            with patch.object(rt, 'receive', recv), patch.object(rt, 'remaining_forecast', gate), redirect_stdout(io.StringIO()):
                try:
                    result = rt.generate_batches('qwen_p3', data, out, store, guard, claim,
                                                 lambda: None, started, started+900, Conn(), NS())
                except (ValueError, ConnectionError, TimeoutError) as exc:
                    error = type(exc).__name__
            files = {str(p.relative_to(out)): read(p) for p in out.rglob('*.json')}
            return result, error, generated, store, files

    def test_full_mock_pair_one_bootstrap_not_per_endpoint(self):
        result, error, generated, store, files = self.flow()
        self.assertIsNone(error); self.assertEqual(result['new_outputs'], 1000)
        self.assertEqual([len(ids) for _, ids in generated], [256, 244, 256, 244])
        self.assertEqual(len({i for _, ids in generated for i in ids}), 1000)
        self.assertEqual(result['first_measurement_exceptions'], 1)
        self.assertEqual(result['forecasts'], 3)
        self.assertEqual(sum(v['first_measurement_exception'] for k, v in files.items()
                             if k.startswith('intents/')), 1)

    def test_existing_unit_blocks_before_model(self):
        result, error, generated, store, files = self.flow(prior=True)
        self.assertEqual(error, 'ValueError'); self.assertEqual(generated, [])
        self.assertFalse(files)

    def test_lost_response_fences_attempt_no_retry(self):
        result, error, generated, store, files = self.flow(lost=True)
        self.assertEqual(error, 'ConnectionError'); self.assertEqual(len(generated), 1)
        self.assertEqual(len([k for k in store if '/unit/' in k]), 1)
        self.assertFalse(any('/done/' in k for k in store))
        self.assertEqual(len(files), 1)

    def test_bad_raw_saved_before_validation_and_no_done_ack(self):
        result, error, generated, store, files = self.flow(invalid=True)
        self.assertEqual(error, 'ValueError'); self.assertEqual(len(generated), 1)
        self.assertEqual(files['qwen_math_zero/raw/00000.json'][0]['token_ids'], [])
        self.assertFalse(any('/done/' in k for k in store))

    def test_timing_stop_retains_first_batch_and_never_attempts_second(self):
        result, error, generated, store, files = self.flow(deny=True)
        self.assertEqual(error, 'TimeoutError'); self.assertEqual(len(generated), 1)
        self.assertEqual(len([k for k in store if '/done/' in k]), 1)
        self.assertFalse(files['forecasts/001.json']['admitted'])


if __name__ == '__main__':
    unittest.main()
