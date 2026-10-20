"""Metadata-only publication of the two unique E4 child results; no scorer/model."""
import ast
import json
import shutil
from pathlib import Path

from experiments.p010.common import read, dump, sha, manifest, utc
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as src, target.open('xb') as dst:
        shutil.copyfileobj(src, dst)
    assert sha(source) == sha(target)


def publish(run):
    assert run in ('e4_s17_n400', 'e4_s17_n3200')
    r = Path('.local/p010_20261019/r1')
    base = Path('reports/p010_20261019')
    receipt = r/'e4_endpoint_only_runs'/run
    export = r/'e4_endpoint_exports'/run
    records = r/'e4_endpoint_records'/run
    oracle = r/'e4_endpoint_oracles'/run
    training_path = r/'e4_training_oracle_completion_r1'/('n'+run.rsplit('n', 1)[1])/'COMPLETED.json'
    env, sent, local = (read(receipt/n) for n in ('RESULT.json', 'SUBMITTED.json', 'INTENT.json'))
    proof, collection, provider = read(oracle/'COMPLETED.json'), read(export/'COMPLETED.json'), read(export/'PROVIDER_PRIVATE.json')
    ledger = read(records/'RECORDS.json')
    assert env['status'] == 'completed' and proof['passed'] and proof['total'] == 1319
    assert proof['technical_unknown'] == 0 and proof['new_training_updates'] == 0 and proof['repeated_training_state_loads'] == 0
    assert proof['original_failed_parent_remains_failed'] is True
    assert proof['original_receipt_sha256'] == sha(receipt/'RESULT.json') == collection['original_result_sha256']
    assert proof['decoded_rows_sha256'] == sha(oracle/'DECODED_ROWS.json')
    assert proof['training_proof_file_sha256'] == sha(training_path)
    assert ledger['e4_endpoint_only/'+run+'/terminal'] == env and ledger['e4/'+run+'/terminal']['status'] == 'failed'
    assert read(records/'COMPLETED.json')['records_sha256'] == sha(records/'RECORDS.json')
    assert collection['provider_stopped'] is True and provider['app_id'] == sent['app_id']
    validate_stopped_apps([sent['app_id']], provider['original_info'], provider['owned'])
    assert sha(export/'evidence.tar.gz') == env['artifact']['tar_sha256']
    for p in (oracle, records):
        assert not (p/'FAILED.json').exists()
    copies = {
        receipt/'RESULT.json': 'ORIGINAL_RESULT_ENVELOPE.json',
        receipt/'SUBMITTED.json': 'ORIGINAL_SUBMITTED.json',
        receipt/'INTENT.json': 'ORIGINAL_LOCAL_INTENT.json',
        export/'COMPLETED.json': 'ORIGINAL_COLLECTION_COMPLETED.json',
        export/'evidence.tar.gz': 'original_evidence.tar.gz',
        records/'RECORDS.json': 'ORIGINAL_NAMED_LEDGER.json',
        records/'COMPLETED.json': 'LEDGER_COMPLETED.json',
        oracle/'COMPLETED.json': 'ENDPOINT_ORACLE.json',
        oracle/'DECODED_ROWS.json': 'DECODED_ROWS.json',
        training_path: 'ORIGINAL_COMPLETE_TRAINING_PROOF.json',
    }
    # Check private host locators before creating any immutable public result.
    for p in list(copies) + list((export/'evidence').rglob('*.json')):
        if p.suffix == '.json':
            text = p.read_text()
            if '/Users/' in text or '/var/folders/' in text:
                raise ValueError('Private locator in proposed public original: '+str(p))
    out = base/'e4_endpoint_results_v1'/run
    out.mkdir(parents=True, exist_ok=False)
    for p, name in copies.items():
        copy(p, out/name)
    life = provider['original_info'][0]['lifecycle']
    dump(out/'PROVIDER.json', dict(app_id=sent['app_id'], lifecycle={k:life[k] for k in ('created_at','state','stopped_at')},
        owned_count=len(provider['owned']), read_utc=provider['utc'], private_original_sha256=sha(export/'PROVIDER_PRIVATE.json'),
        projection='Actor identity omitted; complete private provider file retained unchanged.'))
    summary = dict(run=run, correct=proof['correct'], total=1319, accuracy=proof['correct']/1319,
        logical_stops=proof['logical_stops'], backend_stops=proof['backend_stops'], technical_unknown=0,
        original_training_updates=1024, original_training_targets=2097148, new_training_updates=0,
        repeated_training_state_loads=0, original_failed_parent_remains_failed=True,
        state_sha256=proof['state_sha256'], source_files=proof['source_files'], execution=local['execution'],
        reserved_child_usd=local['budget']['new_reserved_usd'], original_parent_reserved_usd='6.55',
        is_actual_expense_or_invoice=False, independent_A3_pending=True, bootstrap_performed=False, utc=utc())
    dump(out/'SUMMARY.json', summary)
    source = Path('scripts/prepare_p010_runtime_packets.py')
    node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'closure')
    ns = dict(ast=ast, Path=Path, sha=sha)
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<existing source inventory only>', 'exec'), ns)
    sources = ns['closure'](['scripts/audit_p010_e4_endpoint.py', 'scripts/p010_e4_endpoint_io.py'])
    dump(out/'LOCAL_VERIFICATION_SOURCES.json', sources)
    for name in sources:
        copy(Path(name), out/'source'/name)
    copy(Path(__file__), out/'publisher.py')
    (out/'README.md').write_text('# '+run+' — complete endpoint-only evidence, actual A3 pending\n\n'
        'Original final-model endpoint: '+str(proof['correct'])+'/1319, with '+str(proof['logical_stops'].get('length_cap',0))+' logical length caps and zero technical unknowns. '
        'The child app is STOPPED with zero owned containers. It reused the original complete1024-update/2,097,148-target model and generated each original endpoint once. No training or repeated endpoint outputs. The two original training calls remain failed at their pre-generation wrapper-read entrance; their evidence and costs are retained.\n\n'
        'The original compact archive is copied byte-for-byte. Full1319 token streams, six requests/acks/forecasts, original parent and child fences, exact owner exception and A2, engine configuration and frozen marked_answer_v1 decisions were independently verified once locally. Publication only copies and summarizes saved proofs: no tokenization, decoding, state deserialization or rescoring. The old complete-state proof is reused, not rerun. Public state hashes do not assert external access to private binaries. Actual A3 remains pending.\n\n'
        'Provider metadata removes actor identity only and binds the full private original hash. The2.52USD child and6.55USD failed-parent reservations are not actual spending, final cost or balances. No release or category transfer. All original outcomes, including caps and parser failures, remain included. These are operational audit records, not course-report prose.\n')
    dump(out/'MANIFEST.json', manifest(out))
    dump(r/('PUBLICATION_'+run+'_endpoint.json'), dict(packet=str(out), manifest_sha256=sha(out/'MANIFEST.json'), utc=utc(),
        new_training=0, new_generation=0, new_scores=0, repeated_state_loads=0))
    print(json.dumps({k:summary[k] for k in ('run','correct','total','logical_stops','technical_unknown')}))


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',required=True)
    publish(p.parse_args().run)
