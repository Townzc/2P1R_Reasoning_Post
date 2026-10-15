"""New S1 evidence mutations only; no model, state or symbolic execution."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from experiments.sft_allocation_midpoint.common import digest, dump, read, sha
from experiments.learning_regime_p009 import stage1_s1_evidence as e
from experiments.learning_regime_p009.stage1_s1_contract import cents, forecast
from experiments.learning_regime_p009.stage1_endpoint_engine import checked_endpoint
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs


class Tokenizer:
    all_special_ids = [151643]

    def __init__(self):
        self.vocab_reads = 0

    def get_vocab(self):
        self.vocab_reads += 1
        return {'answer': 42, 'EOS': 151643}

    def decode(self, ids, **kwargs):
        return r'answer \boxed{2}'


def fixture(root):
    endpoint = []
    for i in range(500):
        base = dict(problem_id=f'synthetic/{i:04d}', input_ids=[42])
        endpoint.append(dict(base, candidate_id='S1::'+base['problem_id'], source_row_sha256=digest(base)))
    gold = {r['problem_id']: dict(problem_id=r['problem_id'], answer='2') for r in endpoint}
    # This is a synthetic payload limit, never an actual runtime candidate.
    cap = dict(worker_seconds=4000, platform_seconds=4060, startup_seconds=600,
               full_window_seconds=4700, reserved_cents=cents(4700))
    run = 's1_s17_n400'
    spec = dict(slots={run: cap}, stage_remaining_before_cents={run: 3690},
                timing=dict(training_block_seconds=[1.], endpoint_batch_seconds=[1.]))
    training = dict(result=dict(endpoint=dict(full_batch_intervals_seconds=[2., 2.])),
        joined=dict(exitcode=0, joined_before_endpoint=True, observed_exited_epoch=10.),
        train_seconds=[1.]*64, attempts={}, done={})
    actual = dict(max_model_len=2048, enforce_eager=False, dtype='torch.bfloat16',
        max_num_seqs=256, max_num_batched_tokens=8192, enable_chunked_prefill=True,
        enable_prefix_caching=False, gpu_memory_utilization=.80, compilation_level=3,
        cudagraph_mode='FULL_AND_PIECEWISE', cudagraph_capture_sizes=[1, 2, 4, 8, 16, 32, 64, 128, 256])
    dump(root/'endpoint/environment.json', dict(actual_engine=actual, requested_engine=engine_kwargs(),
        training_process_exit=training['joined'], endpoint_rows_sha256=digest(endpoint)))
    sampling = checked_endpoint('S1', endpoint)
    for i, offset in enumerate((0, 256)):
        part = endpoint[offset:offset+256]; key = f'endpoint_{offset:05d}'
        raw = [dict(candidate_id=x['candidate_id'], problem_id=x['problem_id'],
            source_row_sha256=x['source_row_sha256'], sampling=sampling,
            prompt_token_ids=x['input_ids'], token_ids=[42, 151643], output_count=1,
            backend_text='synthetic', finish_reason='stop', stop_reason=151643) for x in part]
        p = root/'endpoint/raw'/f'{offset:05d}.json'; dump(p, raw)
        ids = [x['candidate_id'] for x in part]
        a = dict(request_sha256=digest(part), offset=offset, count=len(part), candidate_ids=ids,
            measurement_exception=False, preceding_full_batch_seconds=[2.]*i, started_epoch=11.+i*3)
        d = dict(raw_sha256=sha(p), request_sha256=a['request_sha256'], count=len(part),
            candidate_ids=ids, finished_epoch=13.+i*3)
        training['attempts'][key] = a; training['done'][key] = d
        dump(root/'endpoint_forecasts'/f'{i:03d}.json',
             forecast(20.+i*3, 0, 2-i, [1.]*65, [1.]+[2.]*i, 3690, cap))
        dump(root/'endpoint_timings'/f'{i:03d}.json', dict(through_done_ack_seconds=1.5))
    return endpoint, spec, run, dict(finished_epoch=30.), training, Tokenizer(), gold


class S1Evidence(unittest.TestCase):
    def audit(self, root, args):
        return e.verify_endpoint_payload(root, *args)

    def test_complete_payload_decodes_once_without_scoring_or_admission(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); args = fixture(root); value = self.audit(root, args)
            self.assertEqual(value['outputs_decoded'], 500)
            self.assertEqual(len(value['scoring_rows']), 500)
            self.assertEqual(args[-2].vocab_reads, 1)
            self.assertEqual(value['logical_stops'], {'native_eos': 500})
            self.assertFalse(value['symbolic_scoring_performed'])
            self.assertFalse(value['full_runtime_lineage_admission_checked'])
            self.assertFalse(value['scientific_G1_admitted'])
            self.assertNotIn('correct', value)

    def test_changed_raw_file_hash_fails_before_a_score(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); args = fixture(root)
            p = root/'endpoint/raw/00000.json'; p.write_bytes(p.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'attempt/ack'): self.audit(root, args)

    def test_ack_must_be_after_training_process_exit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); args = fixture(root)
            args[4]['attempts']['endpoint_00000']['started_epoch'] = 9.
            with self.assertRaisesRegex(ValueError, 'attempt/ack'): self.audit(root, args)

    def test_all_future_observed_durations_must_be_finite(self):
        for bad in ([1., float('nan')], [1., float('inf')], [1., 0.], [1., True], [1.]):
            with self.assertRaises(ValueError): e.positive_intervals(bad, 2)

    def test_unknown_token_is_not_a_zero(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); args = fixture(root)
            p = root/'endpoint/raw/00000.json'; raw = read(p); raw[0]['token_ids'] = [43, 151643]
            p.write_text(__import__('json').dumps(raw))
            args[4]['done']['endpoint_00000']['raw_sha256'] = sha(p)
            with self.assertRaisesRegex(ValueError, 'Unknown token'): self.audit(root, args)

    def test_endpoint_order_and_complete_gold_denominator_remain_binding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); args = fixture(root); value = self.audit(root, args)
            endpoint, gold, decoded = args[0], args[-1], value['decoded']
            for changed in (decoded[:-1], list(reversed(decoded))):
                with self.assertRaises(ValueError): e.assemble_math_rows(endpoint, changed, gold)
            short = deepcopy(gold); short.pop(next(iter(short)))
            with self.assertRaises(ValueError): e.assemble_math_rows(endpoint, decoded, short)
            invalid = deepcopy(gold); invalid[next(iter(invalid))]['answer'] = ''
            with self.assertRaises(ValueError): e.assemble_math_rows(endpoint, decoded, invalid)

    def test_exact_native_eos_and_true_caps_keep_original_stop_and_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); args = fixture(root)
            p = root/'endpoint/raw/00000.json'; raw = read(p)
            raw[0].update(token_ids=[42]*1023+[151643], finish_reason='length', stop_reason=None)
            raw[1].update(token_ids=[42]*1024, finish_reason='length', stop_reason=None)
            p.write_text(__import__('json').dumps(raw))
            args[4]['done']['endpoint_00000']['raw_sha256'] = sha(p)
            original = p.read_bytes(); value = self.audit(root, args)
            self.assertEqual(value['logical_stops'], {'native_eos': 499, 'length_cap': 1})
            self.assertEqual(value['decoded'][0]['backend_finish_reason'], 'length')
            self.assertEqual(value['scoring_rows'][1]['stop_reason'], 'length_cap')
            self.assertEqual(p.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
