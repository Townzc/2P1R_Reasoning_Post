"""Copy complete E3 evidence once; never decode, score or recompute metrics."""
import ast
import hashlib
import json
import os
import shutil
import tarfile
import threading
from pathlib import Path

from experiments.p010.common import read, dump, sha, digest, manifest, utc
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps


def archive(dest,files):
    members={n:dict(bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()}
    with tarfile.open(dest,'x:gz') as t:
        for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
    with tarfile.open(dest) as t:
        assert {m.name for m in t.getmembers()}==set(members)
        for m in t.getmembers():
            assert m.isfile() and hashlib.sha256(t.extractfile(m).read()).hexdigest()==members[m.name]['sha256']
    return dict(bytes=dest.stat().st_size,sha256=sha(dest),members=members)


def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    with Path(src).open('rb') as f,dst.open('xb') as g:shutil.copyfileobj(f,g)
    assert sha(src)==sha(dst)


def safe(path):
    if Path(path).suffix in ('.json','.jsonl','.md','.txt'):
        data=Path(path).read_text()
        if '/Users/' in data or '/var/folders/' in data:raise ValueError('Private local locator: '+str(path))


def publish():
    r = Path('.local/p010_20261019/r1')
    p = Path('reports/p010_20261019')
    receipt = r/'e3_runs/temperature_supply_r1'
    export, records = r/'e3_export_r1', r/'e3_records_r1'
    oracle, score = r/'e3_oracle_r1', r/'e3_scores_r1'
    metrics, old, inputs = r/'e3_metrics_r1', r/'e3_t08_metadata_r1', r/'e3_inputs_r1'
    payload = score/'job/payload'
    spec_path = p/'e3_runtime_v1/SPEC.json'
    spec = read(spec_path)
    env, sent, intent = [read(receipt/n) for n in ('RESULT.json', 'SUBMITTED.json', 'INTENT.json')]
    generation = read(oracle/'COMPLETED.json')
    scored, scored_done = read(score/'LOCAL_ORACLE_AUDIT.json'), read(score/'COMPLETED.json')
    measured, measured_done = read(metrics/'METRICS.json'), read(metrics/'COMPLETED.json')
    collection, provider = read(export/'COMPLETED.json'), read(export/'PROVIDER_PRIVATE.json')
    ledger, recorded = read(records/'RECORDS.json'), read(records/'COMPLETED.json')
    old_proof = read(old/'COMPLETED.json')
    settlement = read(receipt/'D1_SETTLEMENT_APPLIED.json')
    assert env['status'] == 'completed' and sent['run'] == 'temperature_supply_r1'
    assert all(not (root/'FAILED.json').exists() for root in (export, records, oracle, score, payload, metrics))
    assert generation['passed'] is True and scored['passed'] is True and scored_done['passed'] is True
    assert measured_done['passed'] is True
    assert generation['original_receipt_sha256'] == sha(receipt/'RESULT.json') == collection['original_result_sha256']
    assert generation['original_artifact_digest'] == digest(env['artifact']['all_files'])
    assert generation['spec_sha256'] == sha(spec_path)
    assert generation['source_files'] == spec['source_files']
    assert generation['verification_source_files'] == spec['verification_source_files']
    assert generation['reviews'] == intent['reviews']
    assert generation['outputs_decoded'] == 3200 and generation['technical_unknown'] == 0
    assert generation['symbolic_scoring_performed'] is False
    assert generation['old_T08_decodes'] == generation['new_training_updates'] == generation['old_binary_loads'] == 0
    assert generation['decoded_rows_sha256'] == sha(oracle/'DECODED_ROWS.json')
    assert generation['scoring_rows_sha256'] == sha(oracle/'SCORING_ROWS.json')
    assert scored['full_generation_proof_sha256'] == sha(oracle/'COMPLETED.json')
    assert scored_done['oracle_sha256'] == sha(score/'LOCAL_ORACLE_AUDIT.json')
    assert scored['original_binding']['original_scoring_rows_sha256'] == sha(oracle/'SCORING_ROWS.json')
    assert scored['scoring_payload_sha256'] == sha(payload/'COMPLETED.json')
    assert scored['scoring_control_sha256'] == sha(score/'job/COMPLETED.json')
    assert read(payload/'COMPLETED.json')['scored_rows_sha256'] == sha(payload/'ALL_SCORED_ROWS.json')
    assert scored['technical_unknown'] == scored['old_T08_symbolic_calls'] == 0
    assert scored['new_generations'] == scored['new_training_updates'] == scored['repeated_raw_decodes'] == scored['repeated_binary_loads'] == 0
    assert scored['independent_adjudication_complete'] is False and scored['independent_A3_pending'] is True
    assert measured_done['metrics_sha256'] == sha(metrics/'METRICS.json')
    assert measured_done['old_saved_rows'] == 1600 and measured_done['new_saved_rows'] == 3200
    assert measured_done['new_statistical_intervals'] == 0
    assert measured['definitions'] == spec['descriptive_metric_definitions']
    assert measured['original_t08_scores_reused'] == 1600 and measured['new_symbolic_scores_by_metrics'] == 0
    assert set(measured['temperatures']) == {'t06', 't08', 't10'}
    assert all(v['attempts'] == 1600 and v['questions'] == 200 for v in measured['temperatures'].values())
    assert sha(inputs/'ORIGINAL_T08_ROWS.json') == spec['original_T08_rows_sha256'] == old_proof['original_rows_sha256']
    assert sha(old/'COMPLETED.json') == spec['original_T08_metadata_proof_sha256']
    assert sha(old/'PHYSICAL_LENGTHS.json') == old_proof['length_rows_sha256']
    assert old_proof['old_raw_decodes'] == old_proof['old_symbolic_calls'] == 0
    assert sha(records/'RECORDS.json') == recorded['records_sha256']
    assert recorded['receipt_sha256'] == sha(receipt/'RESULT.json')
    assert recorded['provider_sha256'] == sha(export/'PROVIDER_PRIVATE.json')
    assert ledger['e3/temperature_supply_r1/terminal'] == env
    assert ledger['e3/temperature_supply_r1/dispatch'] == intent
    assert collection['artifact'] == env['artifact'] and collection['provider_stopped'] is True
    assert provider['app_id'] == sent['app_id']
    validate_stopped_apps([sent['app_id']], provider['original_info'], provider['owned'])
    assert sha(export/'evidence.tar.gz') == env['artifact']['tar_sha256']
    assert settlement['actual_release_applied'] is True and settlement['original_claims_modified'] is False
    assert settlement['runtime_spec_sha256'] == sha(spec_path)
    assert settlement['proposal_sha256'] == spec['settlement_proposal_sha256']
    assert settlement['exact_A2_report_sha256'] == generation['reviews']['A2']['report_sha256']
    sources = {**spec['source_files'], **spec['verification_source_files']}
    for name, expected in sources.items():
        assert sha(name) == expected, name
    copies = {
        receipt/'RESULT.json': 'ORIGINAL_RESULT_ENVELOPE.json',
        receipt/'SUBMITTED.json': 'ORIGINAL_SUBMITTED.json',
        receipt/'INTENT.json': 'ORIGINAL_LOCAL_INTENT.json',
        receipt/'D1_SETTLEMENT_APPLIED.json': 'ORIGINAL_D1_SETTLEMENT_APPLIED.json',
        export/'COMPLETED.json': 'ORIGINAL_COLLECTION_COMPLETED.json',
        export/'evidence.tar.gz': 'original_evidence.tar.gz',
        records/'RECORDS.json': 'ORIGINAL_NAMED_LEDGER.json',
        records/'COMPLETED.json': 'LEDGER_COMPLETED.json',
        oracle/'COMPLETED.json': 'GENERATION_ORACLE.json',
        oracle/'DECODED_ROWS.json': 'DECODED_ROWS.json',
        oracle/'SCORING_ROWS.json': 'SCORING_ROWS.json',
        score/'LOCAL_ORACLE_AUDIT.json': 'SCORING_ORACLE.json',
        score/'COMPLETED.json': 'SCORING_COMPLETED.json',
        score/'job/COMPLETED.json': 'SCORING_PROCESS_COMPLETED.json',
        payload/'COMPLETED.json': 'SCORE_PAYLOAD_COMPLETED.json',
        payload/'ALL_SCORED_ROWS.json': 'ALL_SCORED_ROWS.json',
        payload/'AUDIT_SAMPLES.json': 'AUDIT_SAMPLES.json',
        metrics/'INTENT.json': 'METRICS_INTENT.json',
        metrics/'COMPLETED.json': 'METRICS_COMPLETED.json',
        metrics/'METRICS.json': 'METRICS.json',
        inputs/'ORIGINAL_T08_ROWS.json': 'ORIGINAL_T08_ROWS.json',
        old/'COMPLETED.json': 'ORIGINAL_T08_METADATA_COMPLETED.json',
        old/'PHYSICAL_LENGTHS.json': 'ORIGINAL_T08_PHYSICAL_LENGTHS.json',
        inputs/'ROSTER.json': 'ORIGINAL_ROSTER.json',
        inputs/'GOLD_SOURCE.json': 'ORIGINAL_GOLD_SOURCE.json',
        spec_path: 'ORIGINAL_SPEC.json',
    }
    journal = {f.relative_to(payload).as_posix(): f for f in payload.rglob('*') if f.is_file()}
    assert journal
    for file in list(copies) + list(journal.values()) + list((export/'evidence').rglob('*')):
        if file.is_file():
            safe(file)
    life = provider['original_info'][0]['lifecycle']
    projected_provider = dict(app_id=sent['app_id'],
        lifecycle={k: life[k] for k in ('created_at', 'state', 'stopped_at')},
        owned_count=len(provider['owned']), read_utc=provider['utc'],
        private_original_sha256=sha(export/'PROVIDER_PRIVATE.json'),
        projection='Actor identity omitted; complete original private bytes retained.')
    # Every source proof and privacy check above precedes the create-only output.
    out = p/'e3_complete_results_v1'
    out.mkdir(parents=True, exist_ok=False)
    for src, name in copies.items():
        copy(src, out/name)
    for file in (payload/'audit_by_evaluation').glob('*.json'):
        copy(file, out/'audit_by_evaluation'/file.name)
    dump(out/'SCORING_JOURNAL_ARCHIVE.json', archive(out/'original_scoring_journal.tar.gz', journal))
    dump(out/'PROVIDER.json', projected_provider)
    dump(out/'SOURCE_BINDING.json', dict(source_files=sources, original_spec_sha256=sha(spec_path)))
    for name in sources:
        copy(Path(name), out/'source'/name)
    copy(Path(__file__), out/'publisher.py')
    summary = dict(utc=utc(), new_outputs=3200, reused_original_T08_outputs=1600,
        original_questions=200, new_training_updates=0, technical_unknown=0,
        old_T08_decodes=0, old_T08_symbolic_scores=0, publication_new_scores=0,
        publication_new_metrics=0, publication_new_statistics=0,
        actual_app_id=sent['app_id'], provider_stopped_owned_zero=True,
        original_metrics_sha256=sha(metrics/'METRICS.json'),
        original_scoring_oracle_sha256=sha(score/'LOCAL_ORACLE_AUDIT.json'),
        original_spec_sha256=sha(spec_path), execution_commit=intent['execution'],
        temperatures=measured['temperatures'], independent_A3_pending=True,
        independent_adjudication_complete=False, reserved_usd=intent['budget']['new_reserved_usd'],
        is_actual_spending=False, is_final_invoice=False)
    dump(out/'SUMMARY.json', summary)
    (out/'README.md').write_text(
        '# Original E3 complete evidence; actual A3 pending\n\n'
        'The original 200 questions have eight attempts at each temperature. '
        'T0.6 and T1.0 contain 3,200 new outputs. The 1,600 original T0.8 outputs, '
        'Boolean scores and saved physical lengths are reused without decoding or scoring again. '
        'No training, model replay, source change or statistical interval is introduced here.\n\n'
        'METRICS.json is the original completed descriptive output copied byte-for-byte; '
        'lexical ROUGE-L and equation-set overlap do not establish semantic equivalence. '
        'All stops, caps, failed scoring attempts and fixed audit samples remain in the evidence. '
        'Independent actual A3 and sample adjudication remain pending.\n\n'
        'The original app is STOPPED with zero owned containers. Original raw archive, '
        'claim and batch records, full scoring journal, D1 application and exact sources are retained. '
        'Provider actor identity is projected separately with the private original SHA. '
        'Reservations and D1 accounting charges are not final spending or account balances. '
        'This is technical evidence metadata, not course-report prose.\n')
    dump(out/'MANIFEST.json', manifest(out))
    dump(r/'E3_COMPLETE_PUBLICATION_DONE.json', dict(utc=utc(), packet=str(out),
        manifest_sha256=sha(out/'MANIFEST.json'), new_model_calls=0,
        new_decodes=0, new_scores=0, new_metrics=0))
    print(json.dumps({k:summary[k] for k in ('new_outputs', 'reused_original_T08_outputs', 'independent_A3_pending')}))


if __name__ == '__main__':
    timer = threading.Timer(600, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        publish()
    finally:
        timer.cancel()
