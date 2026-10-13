"""Read-only audit continuation contracts; never generates, trains, or dispatches.

An existing completed label may be carried only from a pinned interrupted audit.
The caller must first establish that its original worker has stopped. Completed
labels are not rehashed in full; their parent proof and immutable source bindings
are checked. Remaining labels receive the original full artifact/state checks.
"""
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read, sha, digest, verify


def expected_roster(spec):
    campaign = spec['campaign_id']
    out = {name: dict(campaign=spec['inputs_manifest']['acquisition_audits'][name]['campaign'], run=name)
           for name in ('breadth_p0', 'depth_p0', 'breadth_p4', 'depth_p4')}
    for cell in ('breadth_p0', 'depth_p0', 'breadth_p4', 'depth_p4'):
        for seed in (17, 23):
            run = f'{cell}_s{seed}'
            out[run] = dict(campaign=campaign, run=run)
    for run in ('breadth_p0_s17', 'depth_p0_s17'):
        out['original_pilot_' + run] = dict(campaign='mp-policy-cost-20261012-r1', run=run)
    return out


def validate_partition(binding, spec):
    roster = expected_roster(spec)
    if binding['roster'] != roster or len(roster) != 14:
        raise ValueError('Audit roster or campaign mapping differs')
    carried, remaining = set(binding['carried']), binding['remaining']
    if (len(remaining) != len(set(remaining)) or not remaining or not carried
            or carried & set(remaining) or carried | set(remaining) != set(roster)):
        raise ValueError('Exact disjoint completed/remaining partition required')
    if binding['max_seconds'] != 3300 or binding['parallel_readers'] != 2:
        raise ValueError('Unbounded or changed CPU continuation')
    parent = binding['parent']
    if (parent['campaign'] != spec['campaign_id'] or parent['run'] != 'audit'
            or parent['provider']['state'] != 'stopped' or parent['containers']
            or parent['terminal_status'] == 'completed'):
        raise ValueError('Only a stopped incomplete original audit may continue')
    if binding['plan']['deadline_epoch'] != binding['original_deadline_epoch']:
        raise ValueError('No absolute deadline extension')
    if (set(binding['plan']['slots']) != {'audit_remaining'}
            or binding['plan']['slots']['audit_remaining']['reserved_cents'] != 300):
        raise ValueError('Exactly one three-dollar CPU slot required')
    return roster


def verify_carried(root, binding, spec, terminal_get):
    roster = validate_partition(binding, spec)
    root = Path(root)
    parent = root / binding['parent']['campaign'] / 'audit'
    if sha(parent / 'intent.json') != binding['parent']['intent_file_sha256']:
        raise ValueError('Original audit intent changed')
    results = {}
    for label, proof in binding['carried'].items():
        path = parent / (label + '.json')
        if path.stat().st_size != proof['bytes'] or sha(path) != proof['sha256']:
            raise ValueError('Carried CPU proof changed')
        x = read(path)
        source = roster[label]
        folder = root / source['campaign'] / source['run']
        files = read(folder / 'artifact_manifest.json')
        terminal = terminal_get(source['campaign'], source['run'])
        if (not terminal or terminal['status'] != 'completed' or x['terminal'] != terminal
                or x['source_campaign'] != source['campaign']
                or x['manifest_digest'] != digest(files) or digest(files) != terminal['evidence_sha256']
                or x['files_verified'] != len(files) or x['result'] != read(folder / 'result.json')):
            raise ValueError('Carried result is not bound to completed source')
        checkpoint_names = {Path(name).parts[0] for name in files if name.startswith('checkpoint_')}
        if set(x['checkpoints']) != checkpoint_names:
            raise ValueError('Missing or additional carried checkpoint')
        for name, m in x['checkpoints'].items():
            if (m != read(folder / name / 'manifest.json')
                    or sha(folder / name / 'manifest.json') != files[name + '/manifest.json']['sha256']
                    or m['sha256'] != files[name + '/state.pt']['sha256']
                    or m['bytes'] != files[name + '/state.pt']['bytes']):
                raise ValueError('Carried checkpoint manifest differs')
        results[label] = x
    return results


def verify_remaining(root, source, terminal):
    """Original full audit semantics, including every full checkpoint load."""
    from experiments.sft_allocation_midpoint import checkpoint as ck
    folder = Path(root) / source['campaign'] / source['run']
    files = read(folder / 'artifact_manifest.json')
    if not terminal or terminal['status'] != 'completed' or digest(files) != terminal['evidence_sha256']:
        raise ValueError('Remaining source terminal binding differs')
    verify(folder, files)
    checkpoints = {}
    for path in sorted(folder.glob('checkpoint_*')):
        state = ck.load(path)
        checkpoints[path.name] = read(path / 'manifest.json')
        del state
    return dict(source_campaign=source['campaign'], files_verified=len(files),
                manifest_digest=digest(files), terminal=terminal, checkpoints=checkpoints,
                result=read(folder / 'result.json'))
