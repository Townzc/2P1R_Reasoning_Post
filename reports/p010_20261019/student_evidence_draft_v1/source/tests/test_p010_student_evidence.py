import copy
from pathlib import Path
import tempfile
import unittest
from experiments.p010.common import read, dump, digest
from experiments.p010.student_contract import evaluation_jobs, sampling, forecast
from experiments.p010.student_evidence import decode_record, expected_record_keys, verify_endpoint


class Tokenizer:
    all_special_ids = [151643, 151645]
    def get_vocab(self):
        return {'answer': 1, 'eos': 151643, 'special': 151645}
    def decode(self, ids, **kwargs):
        return r'\boxed{1}' if ids else ''


def fixture(root):
    endpoint = [dict(candidate_id=f'S1::q{i}', problem_id=f'q{i}', source_row_sha256=str(i), input_ids=[1]) for i in range(500)]
    spec = dict(model={'vocab_size': 151936}, timing={'training_seconds': [1.], 'endpoint_seconds': [1.]})
    train = dict(train_seconds=[1.]*64)
    gold = {r['problem_id']: {'answer': '1'} for r in endpoint}
    engine = dict(max_model_len=2048, enforce_eager=False, dtype='torch.bfloat16',
        max_num_seqs=256, max_num_batched_tokens=8192, enable_chunked_prefill=True,
        enable_prefix_caching=False, gpu_memory_utilization=.8, compilation_level=3,
        cudagraph_mode='FULL_AND_PIECEWISE', cudagraph_capture_sizes=[1,2,4,8,16,32,64,128,256])
    dump(root/'ENGINE.json', engine)
    dump(root/'RESULT.json', dict(raw_endpoint_count=2500, unique_questions=500,
        evaluations=[j[0] for j in evaluation_jobs()], eval_batch_seconds=[1.]*10))
    ledger = {}; idx = 0
    for job in evaluation_jobs():
        for offset in (0, 256):
            unit = job[0]+f'/{offset:04d}'; part = endpoint[offset:offset+256]
            raw = [dict(**{k:r[k] for k in ('candidate_id','problem_id','source_row_sha256')},
                prompt_token_ids=r['input_ids'], sampling=sampling(job), output_count=1,
                backend_text=r'\boxed{1}', token_ids=[1,151643], finish_reason='stop', stop_reason=151643) for r in part]
            intent = dict(rows=part, sampling=[sampling(job) for _ in part], evaluation=job[0], epoch=10+idx)
            ack = dict(count=len(part), seconds=1., raw_sha256=digest(raw), evaluation=job[0])
            f = forecast(0, 0, 10-idx, [1.]+train['train_seconds'], [1.]+[1.]*idx, '0')
            for folder, value in [('raw',raw),('eval_intents',intent),('eval_acks',ack),('eval_forecasts',f)]:
                dump(root/folder/(unit+'.json'), value)
            ledger['student/run/eval/'+unit] = intent; ledger['student/run/eval_done/'+unit] = ack
            idx += 1
    return endpoint, spec, ledger, train, gold


class EvidenceChecks(unittest.TestCase):
    def test_all_five_endpoints_keep_distinct_sample_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); rows, spec, ledger, train, gold = fixture(root)
            proof = verify_endpoint(root, rows, spec, 'run', ledger, train, Tokenizer(), gold, '0')
            self.assertEqual(proof['outputs_decoded'], 2500)
            self.assertEqual(len({r['id'] for r in proof['scoring_rows']}), 2500)
            self.assertEqual(proof['logical_stops']['sample3']['native_eos'], 500)
            self.assertFalse(proof['symbolic_scoring_performed'])

    def test_sample_seed_mutation_rejected_even_if_raw_ack_rehashed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); rows, spec, ledger, train, gold = fixture(root)
            p = root/'raw/sample0/0000.json'; raw = read(p); raw[0]['sampling']['seed'] = 3
            p.unlink(); dump(p, raw)
            p = root/'eval_acks/sample0/0000.json'; ack = read(p); ack['raw_sha256'] = digest(raw)
            p.unlink(); dump(p, ack); ledger['student/run/eval_done/sample0/0000'] = ack
            with self.assertRaisesRegex(ValueError, 'identity differs'):
                verify_endpoint(root, rows, spec, 'run', ledger, train, Tokenizer(), gold, '0')

    def test_missing_entire_sample_cannot_be_reported_complete(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); rows, spec, ledger, train, gold = fixture(root)
            (root/'raw/sample3/0256.json').unlink()
            with self.assertRaisesRegex(ValueError, 'Missing or extra'):
                verify_endpoint(root, rows, spec, 'run', ledger, train, Tokenizer(), gold, '0')

    def test_native_eos_at_cap_and_unmapped_length_keep_frozen_stops(self):
        row = dict(candidate_id='S1::q', problem_id='q', source_row_sha256='x', input_ids=[1])
        raw = dict(**{k:row[k] for k in ('candidate_id','problem_id','source_row_sha256')},
            prompt_token_ids=[1], sampling=sampling(evaluation_jobs()[0]), output_count=1,
            backend_text='x', token_ids=[1]*1023+[151643], finish_reason='length', stop_reason=None)
        args = (evaluation_jobs()[0], Tokenizer(), {1,151643,151645}, [151643,151645], 151936)
        self.assertEqual(decode_record(row,raw,*args)[0]['stop_reason'], 'native_eos')
        raw['token_ids'] = [151800]*1024
        stop, unmapped = decode_record(row,raw,*args)
        self.assertEqual(stop['stop_reason'], 'length_cap'); self.assertEqual(unmapped,[151800])
        raw['token_ids'] = [151936]*1024
        with self.assertRaises(ValueError): decode_record(row,raw,*args)
        raw['token_ids'] = [151800,151643]
        with self.assertRaises(ValueError): decode_record(row,raw,*args)

    def test_named_ledger_roster_has_no_per_update_remote_fabrication(self):
        keys = expected_record_keys('run')
        self.assertEqual(len(keys), 152); self.assertEqual(len(set(keys)),152)
        self.assertNotIn('student/run/unit/update_0001',keys)
        self.assertIn('student/run/unit/training_block_1009_1024',keys)
        self.assertIn('student/run/eval_done/sample3/0256',keys)


if __name__ == '__main__':
    unittest.main()
