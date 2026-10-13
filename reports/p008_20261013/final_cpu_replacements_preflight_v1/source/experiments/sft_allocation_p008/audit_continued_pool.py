"""Read-only integrity helpers for a failed original and a completed child.

These bind the existing merged raw oracle; they do not rescore answers or admit
a CPU/cloud run. Original evidence is copied into temporary local destinations.
"""
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read, digest, verify
from .audit_bundle import CONTAINERS, copy_checked
from .evidence_bundle import safe_name, unpack
from .pool_lineage import PARENT_CAMPAIGN, CHILD_CAMPAIGN, CHILD_RUN


def _archive(source, destination, archive_files, contents, check):
    source, destination = Path(source), Path(destination)
    if set(archive_files) != CONTAINERS:
        raise ValueError('Exact three-file archive required')
    for name in contents:
        safe_name(name)
    destination.mkdir(parents=True, exist_ok=False)
    transfer = destination / 'transfer'
    transfer.mkdir()
    timing = {}
    for name in sorted(CONTAINERS):
        timing[name] = copy_checked(source / name, transfer / name, archive_files[name], check)
    if read(transfer / 'compact_manifest.json') != contents:
        raise ValueError('Archived content differs from admitted original bytes')
    check()
    evidence = destination / 'evidence'
    unpack(transfer / 'compact_evidence.tar.gz', transfer / 'compact_manifest.json',
           transfer / 'bundle_receipt.json', evidence)
    check()
    return evidence, transfer, timing


def verify_failed_parent(source, destination, label, check=lambda: None):
    """Verify a new archive of the preserved ORIGINAL failure, never completed."""
    terminal, claim = label['terminal'], label['claim']
    rec = label['reconciliation']
    if (label['campaign'] != PARENT_CAMPAIGN or label['run_id'] != 'pool_d2'
            or terminal['status'] != 'failed' or terminal['claim_sha256'] != digest(claim)
            or rec['parent_terminal'] != terminal or rec['parent_claim'] != claim
            or rec['passed'] is not True or rec['physical_attempts'] != 3992
            or rec['physical_raw_unknown'] != 0
            or rec['all_raw_independently_redecoded'] is not True
            or rec['all_wallet_prefixes_replayed'] is not True):
        raise ValueError('Real failed-parent provenance required')
    contents = label['preserved_manifest']
    evidence, _, timing = _archive(source, destination, label['archive_files'], contents, check)
    original = read(evidence / 'failure_manifest.json')
    if digest(original) != terminal['evidence_sha256']:
        raise ValueError('Original failure manifest differs')
    if set(contents) != set(original) | {'failure_manifest.json'}:
        raise ValueError('Preservation must contain exactly original failure bytes and manifest')
    if any(contents[n] != record for n, record in original.items()):
        raise ValueError('Preserved original file was replaced')
    verify(evidence, original)
    sent = read(evidence / 'intent.json')
    if (sent['plan']['campaign_id'] != PARENT_CAMPAIGN
            or sent['config'] != label['config'] or sent['config']['run_id'] != 'pool_d2'
            or digest(sent['plan']) != claim['plan_sha256']
            or sent['release']['commit'] != rec['parent_source_commit']):
        raise ValueError('Archived original configuration/source differs')
    check()
    return dict(passed=True, campaign=PARENT_CAMPAIGN, run_id='pool_d2',
                original_status='failed', files_verified=len(contents),
                original_artifact_digest=digest(original), timings=timing,
                new_model_calls=0, raw_rescoring=False)


def verify_completed_child(source, destination, label, check=lambda: None):
    """Verify child bytes and bind combined oracle without relabeling the parent."""
    source = Path(source)
    env, cfg, oracle = label['envelope'], label['config'], label['local_oracle']
    terminal, files, claim = env['receipt'], env['artifact_manifest'], label['claim']
    if (label['campaign'] != CHILD_CAMPAIGN or label['run_id'] != CHILD_RUN
            or cfg['run_id'] != CHILD_RUN or cfg['role'] != 'pool_continuation'
            or terminal['status'] != 'completed' or digest(files) != terminal['evidence_sha256']
            or terminal['claim_sha256'] != digest(claim)):
        raise ValueError('Exact completed-child envelope required')
    if (oracle['passed'] is not True or oracle['manifest_digest'] != digest(files)
            or oracle['child_terminal'] != terminal or oracle['parent_status'] != 'failed'
            or oracle['child_status'] != 'completed' or oracle['parent_physical_outputs'] != 3992
            or oracle['parent_plus_child_redecoded'] is not True
            or oracle['all_raw_redecoded'] is not True or oracle['all_wallets_replayed'] is not True):
        raise ValueError('Actual merged independent oracle required')
    if read(source / 'artifact_manifest.json') != files:
        raise ValueError('Original child manifest changed')
    if not CONTAINERS <= set(files) or any(n.endswith('.pt') for n in files):
        raise ValueError('Unexpected child archive/state roster')
    contents = {n: v for n, v in files.items() if n not in CONTAINERS}
    evidence, transfer, timing = _archive(source, destination,
        {n: files[n] for n in CONTAINERS}, contents, check)
    for name in CONTAINERS:
        (evidence / name).hardlink_to(transfer / name)
    verify(evidence, files)
    sent, result = read(evidence / 'intent.json'), read(evidence / 'result.json')
    if (sent['config'] != cfg or sent['plan']['campaign_id'] != CHILD_CAMPAIGN
            or digest(sent['plan']) != claim['plan_sha256']
            or result != env['result'] or result['original_parent_status'] != 'failed'
            or result['cumulative_parent_plus_child'] is not True):
        raise ValueError('Archived child identity/cumulative status differs')
    if (result['physical_outputs'] != oracle['physical_outputs']
            or result['child_physical_outputs'] != oracle['child_physical_outputs']
            or result['child_physical_outputs'] <= 0
            or result['physical_outputs'] != 3992 + result['child_physical_outputs']
            or result['returned_tokens'] != oracle['returned_tokens']
            or result['wallets'] != oracle['wallets']):
        raise ValueError('Parent outputs cannot count as new child outputs')
    check()
    return dict(passed=True, campaign=CHILD_CAMPAIGN, run_id=CHILD_RUN,
                role='pool_continuation', files_verified=len(files),
                original_artifact_digest=digest(files), local_oracle_sha256=digest(oracle),
                timings=timing, new_model_calls=0, raw_rescoring=False,
                scope='Original child bytes checked; existing merged raw oracle bound')
