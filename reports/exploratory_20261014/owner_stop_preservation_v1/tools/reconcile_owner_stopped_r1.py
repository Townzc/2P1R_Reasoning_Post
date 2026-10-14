"""Local stopped-prefix inventory and original student-state verification.

No endpoint scoring/decoding, model calls, remote writes, resumed evaluation or
continuation admission. A saved unacknowledged batch stays unacknowledged.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import torch
from transformers import AutoTokenizer

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from experiments.sft_allocation_midpoint import checkpoint as ck
from experiments.sft_allocation_p008.block_journal import POLICY, verify_training_blocks
from experiments.sft_allocation_p008.frozen_student_plan import validate_plan
from src.sft_data import read_jsonl, encode_row

ROOT = Path('.local/exploratory_20261014/r1')
PRESERVE = ROOT / 'interrupted_preservation_r1'
OUT = ROOT / 'interrupted_reconciliation_r1'
CAMP = 'exploratory-20261014-r1'
PREFIX = 'midpoint/' + CAMP + '/'
RUNS = ('base_4shot', 'instruct_0shot', 'wrong_teacher_t1')


def finite_tensors(value):
    if isinstance(value, torch.Tensor):
        if value.is_floating_point():
            assert torch.isfinite(value).all()
        return 1
    if isinstance(value, dict):
        return sum(finite_tensors(x) for x in value.values())
    if isinstance(value, (tuple, list)):
        return sum(finite_tensors(x) for x in value)
    return 0


def main():
    preserved = read(PRESERVE / 'PRESERVED_ALL.json')
    assert preserved['preserved'] and not preserved['continuation_admitted']
    OUT.mkdir(exist_ok=False)
    dump(OUT / 'READ_INTENT.json', dict(utc=datetime.now(timezone.utc).isoformat(),
         source_sha256=sha(__file__), operation='local_saved_inventory_and_checkpoint_verification',
         raw_rescoring=False, new_model_calls=0))
    try:
        ledger = read(PRESERVE / 'ledger.json')
        assert sha(PRESERVE / 'ledger.json') == preserved['ledger_sha256']
        inputs = ROOT / 'inputs'
        spec = read('reports/exploratory_20261014/admission_v1/ADMISSION.json')
        assert sha(inputs / 'manifest.json') == spec['input_manifest_sha256']
        verify(inputs, read(inputs / 'manifest.json')['files'])
        endpoint = read_jsonl(inputs / 'gsm8k_test1319.jsonl')
        assert len(endpoint) == 1319
        inventory = {}
        for run in RUNS:
            root = PRESERVE / run / 'evidence'
            manifest = read(PRESERVE / run / 'LOCAL_MANIFEST.json')
            failure_files = read(root / 'failure_manifest.json')
            terminal = ledger[PREFIX + 'terminal/' + run]
            claim = ledger[PREFIX + 'claim/' + run]
            intent = read(root / 'intent.json')
            cfg = spec['configs'][run]
            assert terminal['status'] == 'failed'
            assert terminal['claim_sha256'] == digest(claim)
            assert terminal['evidence_sha256'] == digest(failure_files)
            assert set(manifest) == set(failure_files) | {'failure_manifest.json'}
            assert all(manifest[name] == value for name, value in failure_files.items())
            assert intent['config'] == cfg and intent['plan'] == spec['plan']
            assert intent['release']['source_files'] == spec['source_files']
            assert read(root / 'admission.json') == spec
            bound = ledger[PREFIX + 'intent/' + run]
            assert bound['config_sha256'] == digest(cfg)
            assert bound['source_sha256'] == digest(spec['source_files'])
            assert bound['data_sha256'] == cfg['input_sha256']
            assert claim['intent_sha256'] == digest(bound)
            local_intents = {p.stem: read(p) for p in (root / 'intents').glob('*.json')}
            local_done = {p.stem: read(p) for p in (root / 'completed').glob('*.json')}
            blocks = verify_training_blocks(local_intents, local_done, ledger, PREFIX + run + '/', cfg['updates'])
            attempts = sorted(k for k in local_intents if k.startswith('endpoint1319_batch_'))
            completed = sorted(k for k in local_done if k.startswith('endpoint1319_batch_'))
            assert set(completed) <= set(attempts)
            starts = [int(k.rsplit('_', 1)[1]) for k in attempts]
            assert starts == list(range(0, max(starts) + 1, 16))
            assert [int(k.rsplit('_', 1)[1]) for k in completed] == list(range(0, len(completed) * 16, 16))
            prompts = read(inputs / (run + '_prompts.json'))
            batches = []
            expected_raw = set()
            expected_scored = set()
            for unit, start in zip(attempts, starts):
                rows = endpoint[start:start + 16]
                expected_ids = [r['problem_id'] for r in rows]
                assert local_intents[unit]['problem_ids'] == expected_ids
                assert local_intents[unit]['count'] == len(rows)
                rf = root / 'endpoint1319' / f'batch_{start:04d}_raw.json'
                sf = root / 'endpoint1319' / f'batch_{start:04d}_scored.jsonl'
                raw_rows = 0
                if rf.exists():
                    expected_raw.add(rf.name)
                    raw = read(rf)
                    assert raw['problem_ids'] == expected_ids
                    assert raw['input_ids'] == [p['input_ids'] for p in prompts[start:start + 16]]
                    assert len(raw['batch_output_ids']) == len(rows) == len(raw['events'])
                    assert len({len(x) for x in raw['batch_output_ids']}) == 1
                    assert 0 < len(raw['batch_output_ids'][0]) <= 512
                    assert all(type(t) is int and t >= 0 for x in raw['batch_output_ids'] for t in x)
                    raw_rows = len(rows)
                scored_rows = 0
                if sf.exists():
                    expected_scored.add(sf.name)
                    saved = read_jsonl(sf)
                    assert [r['problem_id'] for r in saved] == expected_ids
                    assert rf.exists()
                    assert [r['batch_output_ids'] for r in saved] == raw['batch_output_ids']
                    assert [r['stop'] for r in saved] == raw['events']
                    scored_rows = len(saved)
                if unit in local_done:
                    ack = local_done[unit]
                    assert rf.exists() and sf.exists() and ack['count'] == len(rows)
                    assert ack['raw_sha256'] == manifest[rf.relative_to(root).as_posix()]['sha256']
                    assert ack['scored_sha256'] == manifest[sf.relative_to(root).as_posix()]['sha256']
                batches.append(dict(unit=unit, start=start, attempted_rows=len(rows),
                     saved_raw_rows=raw_rows, saved_scored_rows=scored_rows,
                     original_ack_present=unit in local_done,
                     independent_raw_or_score_oracle_performed=False))
            assert {p.name for p in (root / 'endpoint1319').glob('*_raw.json')} == expected_raw
            assert {p.name for p in (root / 'endpoint1319').glob('*_scored.jsonl')} == expected_scored
            attempted = sum(b['attempted_rows'] for b in batches)
            raw_count = sum(b['saved_raw_rows'] for b in batches)
            row = dict(run=run, terminal_status='failed', owner_stopped=True,
                 reserved_cents_not_invoice=claim['reserved_cents'], training_blocks=len(blocks),
                 attempted_endpoint_rows=attempted, saved_raw_rows=raw_count,
                 original_acknowledged_rows=sum(b['attempted_rows'] for b in batches if b['original_ack_present']),
                 unacknowledged_saved_raw_rows=sum(b['saved_raw_rows'] for b in batches if not b['original_ack_present']),
                 attempted_missing_raw_rows=attempted - raw_count,
                 never_attempted_rows=1319 - attempted, batches=batches,
                 endpoint_complete=False, endpoint_score_reported=False,
                 independent_raw_score_validation='not performed',
                 failure_type=read(root / 'failure.json')['error_type'],
                 preserved_files=len(manifest), preserved_bytes=sum(x['bytes'] for x in manifest.values()))
            dump(OUT / (run + '_INVENTORY.json'), row)
            inventory[run] = row

        student_root = PRESERVE / 'wrong_teacher_t1/evidence'
        cfg = spec['configs']['wrong_teacher_t1']
        tok = AutoTokenizer.from_pretrained('.local/midpoint_20261011/data_pipeline/reconstruction_r1/tokenizer', local_files_only=True)
        trainrows = read_jsonl(inputs / cfg['rows_file'])
        encoded = [encode_row(r, tok, 2048) for r in trainrows]
        plan = read(inputs / cfg['plan_file'])
        budget = validate_plan(trainrows, encoded, plan, cfg)
        recipe = read(student_root / 'recipe.json')
        assert json.loads(json.dumps(budget)) == recipe['budget']
        assert recipe['identity']['config'] == cfg
        assert read(student_root / 'training_journal_policy.json') == POLICY
        state = ck.load(student_root / 'checkpoint_0256', recipe['identity'])
        assert state['step'] == state['cursor'] == 256
        assert state['schedule'] == plan['updates'] and state['lrs'] == plan['lrs']
        targets = processed = 0
        for step, indices in enumerate(plan['updates'], 1):
            name = f'update_{step:04d}'
            record = dict(step=step, indices=indices, lr=plan['lrs'][step - 1],
                          supervised_tokens=sum(encoded[i]['n_supervised'] for i in indices),
                          processed_tokens=sum(encoded[i]['n_processed'] for i in indices))
            intent = read(student_root / 'intents' / (name + '.json'))
            done = read(student_root / 'completed' / (name + '.json'))
            assert intent == record and all(done[k] == v for k, v in record.items())
            targets += record['supervised_tokens']
            processed += record['processed_tokens']
            assert done['cumulative_targets'] == targets and done['cumulative_processed'] == processed
            assert all(math.isfinite(done[k]) for k in ('loss', 'gradient_norm', 'seconds'))
        assert targets == state['supervised_tokens'] == cfg['targets'] == 524287
        assert processed == state['processed_tokens']
        assert state['trainable_names'] and set(state['trainable_names']) == set(state['adapter'])
        assert state['optimizer']['state'] and state['optimizer']['param_groups']
        assert all(float(v['step']) == 256 for v in state['optimizer']['state'].values())
        assert {'python', 'numpy', 'torch', 'cuda'} == set(state['rng'])
        assert state['rng']['cuda']
        tensors = finite_tensors(dict(adapter=state['adapter'], optimizer=state['optimizer']))
        checkpoint = dict(verified=True, manifest=read(student_root / 'checkpoint_0256/manifest.json'),
             updates=256, targets=targets, processed=processed, training_blocks=16,
             frozen_schedule_and_lrs=True, full_state_loaded_once_locally=True,
             adapter_optimizer_finite_tensor_count=tensors,
             optimizer_steps_all_256=True, rng_fields_preserved=True,
             new_training_updates=0, state_restored_into_model=False, resume_admitted=False)
        dump(OUT / 'STUDENT_CHECKPOINT_VERIFIED.json', checkpoint)
        summary = dict(preservation_and_inventory_verified=True, finished_at_utc=datetime.now(timezone.utc).isoformat(),
             runs={run: {k: v for k, v in row.items() if k != 'batches'} for run, row in inventory.items()},
             student_checkpoint=checkpoint, endpoint_score_oracle_passed=False,
             new_model_calls=0, retry_or_continuation_authorized=False)
        dump(OUT / 'VERIFIED.json', summary)
        print(json.dumps(summary), flush=True)
    except BaseException as exc:
        dump(OUT / 'FAILURE.json', dict(type=type(exc).__name__, error=str(exc),
             utc=datetime.now(timezone.utc).isoformat(), preserve_all_outputs=True))
        raise


if __name__ == '__main__':
    main()
