"""Original zero-update failure integrity; no retry, re-scoring or model call."""
from experiments.sft_allocation_midpoint.common import read, digest, verify
from .audit_continued_pool import _archive
from .audit_replacement_binding import FAILED_STUDENTS, STUDENT_CAMPAIGN, REPLACEMENT_SPEC


def verify_failed_student(source, destination, label, check=lambda: None):
    name = label['run_id']
    spec = label['replacement_spec']
    if name not in FAILED_STUDENTS or digest(spec) != REPLACEMENT_SPEC:
        raise ValueError('Exact authorized zero-update failure required')
    parent = spec['parents'][name]
    row = spec['zero_update_reconciliation']['runs'][name]
    terminal, claim = label['terminal'], label['claim']
    if (label['campaign'] != STUDENT_CAMPAIGN or terminal != parent['terminal']
            or claim != parent['claim'] or terminal['status'] != 'failed'
            or terminal['claim_sha256'] != digest(claim)
            or any(row[k] != 0 for k in ('training_updates_attempted','training_updates_completed',
                'supervised_targets','endpoint_outputs','unresolved_scientific_units'))):
        raise ValueError('Original failure must remain zero-update and failed')
    contents = label['preserved_manifest']
    evidence, _, timing = _archive(source,destination,label['archive_files'],contents,check)
    original = read(evidence/'failure_manifest.json')
    if (digest(original) != terminal['evidence_sha256']
            or set(contents) != set(original) | {'failure_manifest.json'}
            or any(contents[n] != record for n,record in original.items())
            or any(n.startswith(('intents/','completed/','endpoint1319/','checkpoint_')) for n in original)):
        raise ValueError('Original failed bytes include unexpected scientific units')
    verify(evidence,original)
    sent = read(evidence/'intent.json')
    if (sent['config'] != label['config'] or sent['config'] != spec['original_spec']['configs'][name]
            or sent['release'] != spec['original_releases'][name]
            or digest(sent['plan']) != claim['plan_sha256']
            or sent['plan'] != spec['original_execution_plan']):
        raise ValueError('Original failure source or input identity differs')
    metrics = read(evidence/'block_journal_metrics.json')
    if any(metrics[k] != 0 for k in ('block_boundary_calls','completed_blocks','completed_local_updates')):
        raise ValueError('Failed source performed scientific updates')
    check()
    return dict(passed=True,campaign=label['campaign'],run_id=name,original_status='failed',
        files_verified=len(contents),original_artifact_digest=digest(original),timings=timing,
        attempted_updates=0,endpoint_outputs=0,new_model_calls=0,raw_rescoring=False,
        scope='Original archived failure bytes and existing zero-update reconciliation; no parent replay')
