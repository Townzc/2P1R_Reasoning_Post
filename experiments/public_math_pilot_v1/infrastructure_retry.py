"""One evidence-bound retry of the first GSM128 batch lost to concurrent OOM."""
from pathlib import Path

from .runtime_common import PhysicalLedger, read
from .preflight import json_hash, sha

FAILED_SOURCE = 'c9239c86bc929eea8dc40d33a3666f2d387704b9'
SUFFIX = '#infrastructure-retry-1'


class GsmOomRetryLedger(PhysicalLedger):
    """The128 failed physical attempts remain charged; no completed text is retried."""

    def __init__(self, path, evidence_path, expected_rows, base_identity):
        super().__init__(path)
        evidence_path=Path(evidence_path)
        evidence=read(evidence_path)
        ids=['Base-GSM8K/'+r['id'] for r in expected_rows]
        if (len(ids)!=128 or len(set(ids))!=128 or evidence.get('schema')!=1
                or evidence.get('incident')!='first_gsm128_concurrent_cuda_oom'
                or evidence.get('failed_source_commit')!=FAILED_SOURCE
                or evidence.get('eligible_logical_ids')!=ids
                or evidence.get('maximum_extra_physical_generations')!=128
                or evidence.get('maximum_retries_per_id')!=1
                or evidence.get('replacement_gsm_batch_size')!=64
                or evidence.get('saved_public_outputs_before_repair')!=0):
            raise ValueError('Retry evidence differs from the one frozen infrastructure incident')
        archive=evidence_path.parent/'failed_attempts'/'gsm128_oom_20260917'
        files=evidence['files_sha256']
        required={'evaluate.log','process_receipt.json','physical_ledger_before_retry.jsonl',
                  'EVALUATION_CONTRACT.json','Base-GSM8K/identity.json',
                  'Base-GSM8K/batch_00000.reservation.json'}
        if set(files)!=required or any(sha(archive/name)!=files[name] for name in required):
            raise ValueError('Failed attempt evidence changed')
        if any((archive/'Base-GSM8K').glob('batch_[0-9][0-9][0-9][0-9][0-9].json')) or (archive/'Base-GSM8K/COMPLETE.json').exists():
            raise ValueError('Completed public outputs must never be retried')
        receipt=read(archive/'process_receipt.json')
        if receipt['exit_code']!=1 or receipt['source_commit']!=FAILED_SOURCE:
            raise ValueError('No matching failed process receipt')
        if 'torch.OutOfMemoryError: CUDA out of memory' not in (archive/'evaluate.log').read_text():
            raise ValueError('The failure is not the audited CUDA OOM')
        request=read(archive/'Base-GSM8K/batch_00000.reservation.json')
        if (request['logical_name']!='Base-GSM8K' or request['row_ids']!=[r['id'] for r in expected_rows]
                or request['prompt_sha256']!=[json_hash(r['prompt_ids']) for r in expected_rows]
                or request['model']!=base_identity or request['decoding']['batch_size']!=128
                or request['decoding']['do_sample'] is not False
                or request['decoding']['max_new_tokens']!=2048):
            raise ValueError('Failed request identity differs')
        snapshot=(archive/'physical_ledger_before_retry.jsonl').read_bytes()
        if not self.path.read_bytes().startswith(snapshot):
            raise ValueError('Original physical reservations were altered')
        import json
        events=[json.loads(s) for s in snapshot.splitlines() if s.strip()]
        public=[e['logical_id'] for e in events if e['kind']=='generation' and e['logical_id'].startswith('Base-GSM8K/')]
        if public!=ids:
            raise ValueError('Missing or excess failed reservations')
        self.retry_ids=set(ids)
        self.evidence_sha256=sha(evidence_path)
        self.caps=dict(PhysicalLedger.caps,generation=31203+128)

    def reserve(self, kind, logical_ids):
        mapped=[key+SUFFIX if kind=='generation' and key in self.retry_ids else key for key in logical_ids]
        # Generated names cannot smuggle a second retry namespace past the cap.
        if any(SUFFIX in key for key in logical_ids):
            raise ValueError('Caller supplied a physical retry namespace')
        return super().reserve(kind,mapped)
