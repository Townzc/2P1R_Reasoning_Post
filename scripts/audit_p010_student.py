"""One P010 completed-student ledger read and one independent state/raw oracle."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
from pathlib import Path
import signal

from experiments.p010.common import read, dump, sha, digest, verify, utc
from experiments.p010.student_evidence import (
    expected_record_keys, verify_training, verify_endpoint, GOLD_SHA256, SCORER_SHA256,
)
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps


def collect_records(receipt, export, run, out):
    """Read only152 named original keys after the original STOPPED0 collection.

    Each returned value is preserved immediately. A partial directory cannot be
    retried wholesale. This does not enumerate or mutate unrelated campaigns.
    """
    import modal
    receipt, export, out = Path(receipt), Path(export), Path(out)
    result = read(receipt/'RESULT.json'); sent = read(receipt/'SUBMITTED.json')
    completed = read(export/'COMPLETED.json'); provider = read(export/'PROVIDER_PRIVATE.json')
    if (result['status'] != 'completed' or sent['run'] != run
            or completed['original_result_sha256'] != sha(receipt/'RESULT.json')
            or completed['provider_stopped'] is not True or provider['app_id'] != sent['app_id']):
        raise ValueError('Original completed result and stopped collection required')
    validate_stopped_apps([sent['app_id']], provider['original_info'], provider['owned'])
    keys = expected_record_keys(run); prefix = 'student/'+run+'/'
    out.mkdir(parents=True, exist_ok=False)
    dump(out/'INTENT.json', dict(run=run, keys=keys, original_receipt_sha256=sha(receipt/'RESULT.json'),
        provider_file_sha256=sha(export/'PROVIDER_PRIVATE.json'), utc=utc(), read_only=True,
        maximum_local_seconds=600, automatic_retry=False, roster_is_exact_named_keys_not_global_enumeration=True))
    def expire(*_):
        raise TimeoutError('Original600-second ledger read expired; preserve partial records')
    prior_handler = signal.signal(signal.SIGALRM, expire); signal.alarm(600)
    try:
        store = modal.Dict.from_name('p010-once-20261019', create_if_missing=False)
        before = {k: store.get(prefix+k) for k in ('claim', 'terminal')}
        dump(out/'BEFORE.json', before)
        if before['terminal'] != result:
            raise ValueError('Original terminal differs before collection')
        records = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = {pool.submit(store.get, key): (index, key) for index, key in enumerate(keys)}
            for future in as_completed(pending, timeout=580):
                index, key = pending[future]; value = future.result()
                dump(out/'records'/f'{index:04d}.json', dict(key=key, value=value))
                if value is None:
                    raise ValueError('Missing original completed record: '+key)
                records[key] = value
        after = {k: store.get(prefix+k) for k in ('claim', 'terminal')}
        dump(out/'AFTER.json', after)
        if before != after or records[prefix+'claim'] != before['claim'] or records[prefix+'terminal'] != result:
            raise ValueError('Original claim/terminal changed during collection')
        dump(out/'RECORDS.json', records)
        dump(out/'COMPLETED.json', dict(run=run, records_sha256=sha(out/'RECORDS.json'),
            original_receipt_sha256=sha(receipt/'RESULT.json'), keys=keys, utc=utc(),
            new_model_calls=0, remote_writes=0, scoped_to_named_keys=True))
    except BaseException as exc:
        dump(out/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
                                   partial_records_preserved=True, automatic_retry=False))
        raise
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM, prior_handler)


def audit(args):
    from transformers import AutoTokenizer
    from src.sft_data import read_jsonl
    receipt, export, inputs = Path(args.receipt), Path(args.export), Path(args.inputs)
    root = export/'evidence'; spec = read(args.spec); out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    dump(out/'INTENT.json', dict(run=args.run, spec_sha256=sha(args.spec), utc=utc(),
        automatic_retry=False, new_model_calls=0, symbolic_scoring_performed=False))
    try:
        env = read(receipt/'RESULT.json'); submitted = read(receipt/'SUBMITTED.json')
        local = read(receipt/'INTENT.json'); original = read(root/'INTENT.json')
        collection = read(export/'COMPLETED.json'); provider = read(export/'PROVIDER_PRIVATE.json')
        ledger_proof = read(Path(args.records)/'COMPLETED.json')
        ledger = read(Path(args.records)/'RECORDS.json'); run = args.run; prefix = 'student/'+run+'/'
        if (env['status'] != 'completed' or submitted['run'] != run or local['run'] != run
                or collection['original_result_sha256'] != sha(receipt/'RESULT.json')
                or collection['artifact'] != env['artifact'] or collection['provider_stopped'] is not True
                or provider['app_id'] != submitted['app_id']
                or ledger_proof['run'] != run or ledger_proof['records_sha256'] != sha(Path(args.records)/'RECORDS.json')
                or ledger_proof['original_receipt_sha256'] != sha(receipt/'RESULT.json')
                or set(ledger) != set(expected_record_keys(run)) or ledger[prefix+'terminal'] != env):
            raise ValueError('Actual receipt, collection, provider or ledger binding differs')
        validate_stopped_apps([submitted['app_id']], provider['original_info'], provider['owned'])
        for name, expected in spec['source_files'].items():
            if sha(name) != expected:
                raise ValueError('Actual original source changed: '+name)
        reviews = {}
        for label, file in [('A1', args.data_review), ('A2', args.runtime_review)]:
            value = read(file)
            if (value['decision'] not in ('PASS', 'PASS-WITH-NOTES')
                    or sha(value['local_report_file']) != value['report_sha256']):
                raise ValueError('Original exact fixed review report required')
            reviews[label] = {k: v for k, v in value.items() if k != 'local_report_file'}
        if (reviews['A1']['scope'] != spec['data_review_scope']
                or reviews['A1']['data_manifest_sha256'] != spec['data_manifest_sha256']
                or reviews['A2']['scope'] != 'p010-C4-A2'
                or reviews['A2']['spec_sha256'] != sha(args.spec) or local['reviews'] != reviews):
            raise ValueError('Exact original A1/A2 bindings differ')
        expected_identity = dict(run_id=run, config=spec['configs'][run], execution=local['execution'],
            source_files=spec['source_files'], input_files=spec['input_files'],
            base_files=spec['model']['files'], reviews=reviews)
        if (original['identity'] != expected_identity or original['claim'] != ledger[prefix+'claim']
                or original['claim']['run'] != run or original['claim']['execution'] != local['execution']
                or original['claim']['epoch'] != original['worker_start_epoch']
                or original['prior_T_reserved_usd'] != local['budget']['prior_reserved_usd']
                or abs(original['hard_deadline_epoch']-original['worker_start_epoch']-4500) > .001
                or datetime.fromisoformat(env['finished_utc']).timestamp() > original['hard_deadline_epoch']
                or not 0 < env['seconds_including_pack'] <= 4500
                or env['result'] != read(root/'RESULT.json')):
            raise ValueError('Original execution identity, claim or hard deadline differs')
        files = env['artifact']['all_files']; compact = env['artifact']['compact_members']
        if (read(root/'COMPACT_MEMBERS.json') != compact
                or {k for k in files if k.endswith('.pt')} != {'checkpoint_1024/state.pt'}
                or sha(export/'evidence.tar.gz') != env['artifact']['tar_sha256']):
            raise ValueError('Original immutable complete-state/raw artifact differs')
        verify(root, compact); verify(root, {'checkpoint_1024/state.pt': files['checkpoint_1024/state.pt']})
        verify(inputs, {k: v for k, v in spec['input_files'].items()
                        if k.startswith(run+'/') or k == 'MATH_ENDPOINT.json'})
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True, use_fast=True)
        for name in ('tokenizer.json', 'tokenizer_config.json', 'vocab.json', 'merges.txt', 'config.json'):
            if sha(Path(args.tokenizer)/name) != spec['model']['files'][name]['sha256']:
                raise ValueError('Frozen model/tokenizer bytes differ')
        if sha(args.gold) != GOLD_SHA256 or sha('experiments/learning_regime_p009/math_scoring.py') != SCORER_SHA256:
            raise ValueError('Original S1 gold/scorer bytes differ')
        gold_rows = read_jsonl(args.gold); gold = {r['problem_id']: r for r in gold_rows}
        if len(gold_rows) != 500 or len(gold) != 500:
            raise ValueError('Original unique500 gold roster required')
        trained = verify_training(root, inputs, spec, run, expected_identity, ledger,
                                  tokenizer, original['prior_T_reserved_usd'])
        endpoint = verify_endpoint(root, read(inputs/'MATH_ENDPOINT.json'), spec, run, ledger,
            trained, tokenizer, gold, original['prior_T_reserved_usd'])
        dump(out/'DECODED_ROWS.json', endpoint.pop('decoded'))
        dump(out/'SCORING_ROWS.json', endpoint.pop('scoring_rows'))
        proof = dict(passed=True, run=run, **endpoint, updates_verified=1024,
            targets_verified=trained['targets'], processed_tokens_verified=trained['processed'],
            state_sha256=trained['state_sha256'], original_artifact_digest=digest(files),
            original_receipt_sha256=sha(receipt/'RESULT.json'), spec_sha256=sha(args.spec),
            source_files=spec['source_files'], scoring_rows_sha256=sha(out/'SCORING_ROWS.json'),
            decoded_rows_sha256=sha(out/'DECODED_ROWS.json'), gold_sha256=GOLD_SHA256,
            scorer_sha256=SCORER_SHA256, reviews=reviews, full_state_loaded_once=True,
            independent_A3_pending=True, utc=utc())
        dump(out/'COMPLETED.json', proof)
        return proof
    except BaseException as exc:
        dump(out/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
            partial_evidence_preserved=True, automatic_retry=False, complete=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest='action', required=True)
    c = sub.add_parser('records')
    for name in ('receipt', 'export', 'run', 'out'):
        c.add_argument('--'+name, required=True)
    a = sub.add_parser('audit')
    for name in ('receipt', 'export', 'inputs', 'spec', 'run', 'records', 'tokenizer', 'gold',
                 'data-review', 'runtime-review', 'out'):
        a.add_argument('--'+name, required=True)
    args = parser.parse_args()
    if args.action == 'records':
        collect_records(args.receipt, args.export, args.run, args.out)
    else:
        value = audit(args)
        print(json.dumps({k: v for k, v in value.items() if k not in ('source_files', 'reviews')}))
