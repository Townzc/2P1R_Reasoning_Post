import json
from pathlib import Path
import tempfile
import unittest

from experiments.public_math_pilot_v1.infrastructure_retry import GsmOomRetryLedger, FAILED_SOURCE, SUFFIX
from experiments.public_math_pilot_v1.runtime_common import PhysicalLedger
from experiments.public_math_pilot_v1.preflight import json_hash, sha


class InfrastructureRetryTest(unittest.TestCase):
    def fixture(self, root):
        archive=root/'failed_attempts/gsm128_oom_20260917'
        (archive/'Base-GSM8K').mkdir(parents=True)
        rows=[dict(id=str(i),prompt_ids=[i,2]) for i in range(128)]
        identity={'model_sha256':'a'*64}
        ids=['Base-GSM8K/'+r['id'] for r in rows]
        ledger=root/'ledger.jsonl';PhysicalLedger(ledger).reserve('generation',ids)
        (archive/'physical_ledger_before_retry.jsonl').write_bytes(ledger.read_bytes())
        files={
            'evaluate.log':'torch.OutOfMemoryError: CUDA out of memory\n',
            'process_receipt.json':json.dumps(dict(exit_code=1,source_commit=FAILED_SOURCE)),
            'EVALUATION_CONTRACT.json':'{}',
            'Base-GSM8K/identity.json':'{}',
            'Base-GSM8K/batch_00000.reservation.json':json.dumps(dict(logical_name='Base-GSM8K',
                row_ids=[r['id'] for r in rows],prompt_sha256=[json_hash(r['prompt_ids']) for r in rows],
                model=identity,decoding=dict(batch_size=128,do_sample=False,max_new_tokens=2048))),
        }
        for name,value in files.items():(archive/name).write_text(value)
        evidence=dict(schema=1,incident='first_gsm128_concurrent_cuda_oom',failed_source_commit=FAILED_SOURCE,
            eligible_logical_ids=ids,maximum_extra_physical_generations=128,maximum_retries_per_id=1,
            replacement_gsm_batch_size=64,saved_public_outputs_before_repair=0,
            files_sha256={str(p.relative_to(archive)):sha(p) for p in archive.rglob('*') if p.is_file()})
        evidence_path=root/'retry.json';evidence_path.write_text(json.dumps(evidence))
        return ledger,evidence_path,rows,identity,archive

    def test_exact_failed_ids_retry_once_without_erasing_physical_attempts(self):
        with tempfile.TemporaryDirectory() as d:
            path,evidence,rows,identity,archive=self.fixture(Path(d))
            ledger=GsmOomRetryLedger(path,evidence,rows,identity)
            ids=['Base-GSM8K/'+r['id'] for r in rows]
            ledger.reserve('generation',ids[:64]);ledger.reserve('generation',ids[64:])
            events=[json.loads(s) for s in path.read_text().splitlines()]
            self.assertEqual([e['logical_id'] for e in events],ids+[s+SUFFIX for s in ids])
            self.assertEqual(ledger.caps['generation'],31331)
            with self.assertRaises(RuntimeError):ledger.reserve('generation',ids[:1])
            with self.assertRaises(ValueError):ledger.reserve('generation',[ids[0]+SUFFIX])
            restarted=GsmOomRetryLedger(path,evidence,rows,identity)
            with self.assertRaises(RuntimeError):restarted.reserve('generation',ids[64:])

    def test_completed_generation_and_changed_evidence_refuse_retry(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));path,evidence,rows,identity,archive=args
            completed=archive/'Base-GSM8K/batch_00000.json';completed.write_text('{}')
            with self.assertRaises(ValueError):GsmOomRetryLedger(path,evidence,rows,identity)
            completed.unlink();(archive/'evaluate.log').write_text('a different failure')
            with self.assertRaises(ValueError):GsmOomRetryLedger(path,evidence,rows,identity)

    def test_roster_and_original_ledger_cannot_change(self):
        with tempfile.TemporaryDirectory() as d:
            path,evidence,rows,identity,archive=self.fixture(Path(d))
            with self.assertRaises(ValueError):GsmOomRetryLedger(path,evidence,rows[::-1],identity)
            changed=[dict(r) for r in rows];changed[0]['prompt_ids']=[999]
            with self.assertRaises(ValueError):GsmOomRetryLedger(path,evidence,changed,identity)
            path.write_text('')
            with self.assertRaises(ValueError):GsmOomRetryLedger(path,evidence,rows,identity)


if __name__=='__main__':unittest.main()
