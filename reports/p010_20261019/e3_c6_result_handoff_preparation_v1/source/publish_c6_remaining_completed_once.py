"""Publish saved C6 split-lineage evidence; no decode, score or analysis."""
import hashlib
import json
import os
import shutil
import tarfile
import threading
from pathlib import Path

from experiments.p010.common import read, dump, sha, manifest, utc
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps

RUNS = ('base_math', 'base_gsm', 's1_n400_math', 't72_n400_math')
EXPECTED_NEW = dict(base_math=4500, base_gsm=11871, s1_n400_math=2500, t72_n400_math=2500)
PARENT_TARGET = '2311841a6a6f53ea1be3ce2d12fa1068aa2407ad'
PARENT_MANIFEST = '3f3b06a2212d7807b69e06f099c2718129302cc96cb9e9e9c311826a30d6f2de'


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


def provider_projection(path, sent):
    provider = read(path)
    assert provider['app_id'] == sent['app_id']
    validate_stopped_apps([sent['app_id']], provider['original_info'], provider['owned'])
    life = provider['original_info'][0]['lifecycle']
    return dict(app_id=sent['app_id'],
        lifecycle={k:life[k] for k in ('created_at','state','stopped_at')},
        owned_count=len(provider['owned']), read_utc=provider['utc'],
        private_original_sha256=sha(path),
        projection='Actor identity omitted; complete original private bytes retained.')


def publish():
    r = Path('.local/p010_20261019/r1')
    p = Path('reports/p010_20261019')
    receipt = r/'cue_remaining_runs/t72_remaining_r1'
    export, records = r/'cue_remaining_export_r1', r/'cue_remaining_records_r1'
    oracle, scores = r/'cue_remaining_oracle_r1', r/'cue_remaining_scores'
    preserved, parent = r/'cue_benchmark_failure_preservation_r1', r/'cue_benchmark_runs/benchmark_group_r1'
    inputs = r/'cue_benchmark_inputs_r1'
    spec_path = p/'c6_remaining_runtime_v1/SPEC.json'
    spec, proof = read(spec_path), read(oracle/'COMPLETED.json')
    original_spec = read(spec['original_spec_file'])
    env, sent, intent = [read(receipt/n) for n in ('RESULT.json','SUBMITTED.json','INTENT.json')]
    collection, ledger = read(export/'COMPLETED.json'), read(records/'RECORDS.json')
    recorded = read(records/'COMPLETED.json')
    settlement = read(receipt/'I_D1_SETTLEMENT_APPLIED.json')
    assert proof['passed'] is True and proof['technical_unknown'] == 0
    assert proof['original_parent_status'] == 'failed' and proof['new_outputs'] == 21371
    assert proof['outputs_from_failed_parent'] == 18871 and proof['outputs_from_new_remaining_call'] == 2500
    assert proof['new_training_updates'] == proof['new_symbolic_scoring'] == proof['old_no_cue_decodes'] == proof['old_binary_loads'] == 0
    assert proof['spec_sha256'] == sha(spec_path)
    assert proof['source_files'] == spec['source_files']
    assert proof['verification_source_files'] == spec['verification_source_files']
    assert proof['reviews'] == intent['reviews']
    assert proof['original_failure_manifest_sha256'] == spec['failed_parent_manifest_sha256'] == sha(preserved/'MANIFEST.json')
    assert proof['original_preserved_ledger_sha256'] == spec['failed_parent_ledger_sha256']
    assert not (parent/'RESULT.json').exists() and (parent/'ERROR.json').exists()
    assert sha(p/'c6_benchmark_failed_preservation_v1/MANIFEST.json') == PARENT_MANIFEST
    assert env['status'] == 'completed' and sent['run'] == 't72_remaining_r1'
    assert proof['original_receipt_sha256'] == collection['original_result_sha256'] == sha(receipt/'RESULT.json')
    assert collection['provider_stopped'] is True and collection['artifact'] == env['artifact']
    assert recorded['records_sha256'] == sha(records/'RECORDS.json')
    assert recorded['receipt_sha256'] == sha(receipt/'RESULT.json')
    assert recorded['provider_sha256'] == sha(export/'PROVIDER_PRIVATE.json')
    assert ledger['cue/t72_remaining_r1/terminal'] == env
    assert ledger['cue/t72_remaining_r1/dispatch'] == intent
    assert sha(export/'evidence.tar.gz') == env['artifact']['tar_sha256']
    assert sha(inputs/'EXISTING_NO_CUE_TABLES.json') == spec['existing_tables_sha256']
    assert sha(spec['original_spec_file']) == spec['original_spec_sha256']
    assert settlement['actual_release_applied'] is True and settlement['original_claims_modified'] is False
    assert settlement['runtime_spec_sha256'] == sha(spec_path)
    assert settlement['exact_A2_report_sha256'] == intent['reviews']['runtime_A2']['report_sha256']
    assert settlement['owner_evidence_sha256'] == intent['reviews']['owner']['evidence_sha256']
    sources = {**original_spec['source_files'], **original_spec['verification_source_files'],
               **spec['source_files'], **spec['verification_source_files']}
    for name, expected in sources.items():
        assert sha(name) == expected, name
    for root in (oracle, records, export, preserved):
        assert not (root/'FAILED.json').exists()
    projected = {
        'failed_original_parent': provider_projection(preserved/'PROVIDER_PRIVATE.json', read(parent/'SUBMITTED.json')),
        'completed_unattempted_cell': provider_projection(export/'PROVIDER_PRIVATE.json', sent)}
    copies = {
        receipt/'RESULT.json': 'ORIGINAL_NEW_RESULT_ENVELOPE.json',
        receipt/'SUBMITTED.json': 'ORIGINAL_NEW_SUBMITTED.json',
        receipt/'INTENT.json': 'ORIGINAL_NEW_LOCAL_INTENT.json',
        receipt/'I_D1_SETTLEMENT_APPLIED.json': 'ORIGINAL_I_D1_SETTLEMENT_APPLIED.json',
        export/'COMPLETED.json': 'ORIGINAL_NEW_COLLECTION_COMPLETED.json',
        export/'evidence.tar.gz': 'original_remaining_evidence.tar.gz',
        records/'RECORDS.json': 'ORIGINAL_NEW_NAMED_LEDGER.json',
        records/'COMPLETED.json': 'ORIGINAL_NEW_LEDGER_COMPLETED.json',
        oracle/'COMPLETED.json': 'COMPLETE_SPLIT_LINEAGE_RAW_ORACLE.json',
        inputs/'EXISTING_NO_CUE_TABLES.json': 'ORIGINAL_NO_CUE_BOOLEAN_TABLES.json',
        spec_path: 'ORIGINAL_REMAINING_SPEC.json',
    }
    cell_summaries = {}
    journal_files = {}
    for run in RUNS:
        root = scores/run
        done = read(root/'COMPLETED.json')
        assert done['passed'] is True and done['run'] == run
        assert done['technical_unknown'] == done['old_scoring_repeated'] == done['old_generation_repeated'] == 0
        assert done['new_outputs'] == EXPECTED_NEW[run] and done['bootstrap_performed'] is False
        assert done['original_binding']['oracle_sha256'] == sha(oracle/'COMPLETED.json')
        assert done['original_binding']['spec_sha256'] == sha(spec_path)
        assert done['original_binding']['reused_tables_sha256'] == spec['existing_tables_sha256']
        assert done['original_binding']['original_rows_sha256'] == sha(oracle/run/'SCORING_ROWS.json')
        assert done['question_correct_sha256'] == sha(root/'QUESTION_CORRECT.json')
        assert proof['cells'][run]['decoded_sha256'] == sha(oracle/run/'DECODED_ROWS.json')
        assert proof['cells'][run]['scoring_sha256'] == sha(oracle/run/'SCORING_ROWS.json')
        assert not list(root.rglob('FAILED.json'))
        for name in ('COMPLETED.json','QUESTION_CORRECT.json','CONDITION_SUMMARIES.json','INTENT.json'):
            copies[root/name] = 'cells/'+run+'/'+name
        for name in ('DECODED_ROWS.json','SCORING_ROWS.json'):
            copies[oracle/run/name] = 'cells/'+run+'/'+name
        journal_files[run] = {f.relative_to(root).as_posix():f for f in root.rglob('*') if f.is_file()}
        cell_summaries[run] = dict(new_outputs=done['new_outputs'],
            conditions=read(root/'CONDITION_SUMMARIES.json'),
            original_conditions_reused=done['original_conditions_reused'],
            technical_unknown=0, scoring_proof_sha256=sha(root/'COMPLETED.json'),
            question_correct_sha256=sha(root/'QUESTION_CORRECT.json'),
            independent_A3_pending=True)
    # Check privacy before creating the output; no evidence is silently omitted.
    for file in list(copies) + [f for files in journal_files.values() for f in files.values()] + list((export/'evidence').rglob('*')):
        if file.is_file():
            safe(file)
    out = p/'c6_complete_results_v1'
    out.mkdir(parents=True, exist_ok=False)
    for src, name in copies.items():
        copy(src, out/name)
    for run, files in journal_files.items():
        dump(out/'cells'/run/'SCORING_JOURNAL_ARCHIVE.json',
             archive(out/'cells'/run/'original_scoring_journal.tar.gz', files))
    dump(out/'PROVIDERS.json', projected)
    dump(out/'FAILED_PARENT_REFERENCE.json', dict(
        target_commit=PARENT_TARGET,
        packet='reports/p010_20261019/c6_benchmark_failed_preservation_v1',
        public_manifest_sha256=PARENT_MANIFEST,
        original_private_manifest_sha256=spec['failed_parent_manifest_sha256'],
        original_private_ledger_sha256=spec['failed_parent_ledger_sha256'],
        original_status='failed', original_raw_outputs=18871,
        original_completed_batches=75, original_T72_attempts=0,
        parent_republished_or_reclassified=False))
    dump(out/'SOURCE_BINDING.json', dict(source_files=sources, spec_sha256=sha(spec_path)))
    for name in sources:
        copy(Path(name), out/'source'/name)
    copy(Path(__file__), out/'publisher.py')
    summary = dict(utc=utc(), cells=cell_summaries, original_failed_parent_retained=True,
        saved_parent_outputs=18871, new_remaining_outputs=2500,
        total_complete_outputs=21371, no_cue_Boolean_tables_reused=True,
        new_training_updates=0, publication_new_decodes=0, publication_new_scores=0,
        publication_new_statistics=0, independent_A3_pending=True,
        reserved_usd=intent['budget']['new_reserved_usd'], is_actual_spending=False,
        cue_selected_before_test=True, selection_sha256=spec['selection_sha256'])
    dump(out/'SUMMARY.json', summary)
    (out/'README.md').write_text(
        '# Complete original C6 cue benchmark; actual A3 pending\n\n'
        'The failed original group contributes three fully saved cells: 18,871 outputs and 75 batch acknowledgements. '
        'Its fourth cell had no attempted generation. The independently approved remaining call contributes '
        'only the original 2,500 T72-n400 outputs. The original parent remains failed. '
        'Both provider lifecycles are STOPPED with zero owned containers.\n\n'
        'The complete combined raw oracle covers 21,371 outputs once. All four cells retain '
        'greedy and four samples with and without the original development-selected cue. '
        'Existing no-cue Boolean tables are reused without decoding, symbolic scoring or generation. '
        'Each new frozen score journal preserves caps, failures, fixed samples and original condition identities. '
        'Independent actual A3 and scoring-sample adjudication remain pending.\n\n'
        'The original failed-parent public archive is referenced at its immutable commit; it is not rebuilt. '
        'The new raw archive is copied byte-for-byte. Provider actor identity is projected with original private SHA. '
        'No training, checkpoint load, merge, rescoring or bootstrap occurs in this publication. '
        'Reservations are not actual spending, invoices or balances. This is technical evidence metadata.\n')
    dump(out/'MANIFEST.json', manifest(out))
    dump(r/'C6_COMPLETE_PUBLICATION_DONE.json', dict(utc=utc(), packet=str(out),
        manifest_sha256=sha(out/'MANIFEST.json'), new_model_calls=0, new_scores=0, new_statistics=0))
    print(json.dumps(dict(packet=str(out), original_saved=18871, new_remaining=2500, actual_A3_pending=True)))


if __name__ == '__main__':
    timer = threading.Timer(600, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        publish()
    finally:
        timer.cancel()
