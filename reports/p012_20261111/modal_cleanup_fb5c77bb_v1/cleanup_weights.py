"""Owner-authorized exact-file L/K4 cleanup; no GPU calls or scientific changes."""
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile
import modal

PUB = Path('reports/p012_20261111/modal_cleanup_fb5c77bb_v1')
LOCAL = Path('.local/p012_20261111/modal_cleanup_fb5c77bb_v1')
RUNS = Path('.local/p012_20261111/amendment8_modal_runs_v1')
MODAL = '.local/midpoint_20261011/venv/bin/modal'
AUTH = 'fb5c77bbf5a46c5d30843fb9f00a94aef1255dfa'
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(Path(p).read_text())


def write(p, obj):
    Path(p).write_text(json.dumps(obj, indent=2) + '\n')


def valid_target(t):
    p = PurePosixPath(t['path'])
    assert t['cell'] in ('L', 'K4') and not t['run_id'].startswith('a8_')
    assert t['volume'] == 'p012-g0-assets-results-20261111'
    assert not p.is_absolute() and '..' not in p.parts
    assert p.parts[:3] == ('training', t['run_id'], 'checkpoint')
    assert p.suffix == '.safetensors' and t['bytes'] > 0
    assert len(t['sha256']) == 64


def active_paths(profile, targets):
    apps = json.loads(subprocess.check_output([MODAL, 'app', 'list', '--json'],
                                             env=dict(os.environ, MODAL_PROFILE=profile), text=True))
    active = [a for a in apps if a['state'] != 'stopped']
    known = {}
    for log in RUNS.glob('*/run.log'):
        for app in re.findall(r'https://modal.com/apps/' + profile + r'/main/(ap-[A-Za-z0-9]+)', log.read_text(errors='replace')):
            request = read(log.parent / 'request.json')
            known[app] = (log.parent.name, request, sha((log.parent / 'request.json').read_bytes()))
    result = []
    for a in active:
        assert a['app_id'] in known, 'Unmapped active application: ' + a['app_id']
        name, request, digest = known[a['app_id']]
        assert name.startswith('a8_')
        # Inspection covers the complete request, including checkpoint/model paths.
        for t in targets:
            assert t['run_id'] not in json.dumps(request)
        result.append({'app_id': a['app_id'], 'run_id': name, 'request_sha256': digest,
                       'target_path_references': 0})
    return {'utc': utc(), 'workspace': profile, 'active_apps': result,
            'all_active_apps_mapped_to_A8_requests': True, 'target_paths_unused': True}


def listing(v, path):
    return {e.path: {'type': int(e.type), 'bytes': e.size, 'mtime': e.mtime}
            for e in v.iterdir(path, recursive=True)}


def public_check(proof):
    for evidence in proof['public_evidence'].values():
        p = Path(evidence['archive'])
        assert sha(p.read_bytes()) == evidence['archive_sha256']
        assert subprocess.check_output(['git', 'hash-object', str(p)], text=True).strip() == subprocess.check_output(
            ['git', 'rev-parse', 'HEAD:' + str(p)], text=True).strip()
        with zipfile.ZipFile(p) as z:
            assert sha(z.read(evidence['member'])) == evidence['sha256']


def main():
    mode, profile = sys.argv[1:3]
    assert profile == os.environ['MODAL_PROFILE'] and profile in ('tangzhice', 'townzc')
    proof_all = read(PUB / 'PUBLIC_EVIDENCE_CHECKS.json')['candidate_runs']
    proofs = [p for p in proof_all if p['workspace'] == profile]
    manifest = read(LOCAL / 'DELETION_CANDIDATE.json' if mode == 'verify' else PUB / 'DELETION_MANIFEST.json')
    assert manifest['authority_commit'] == AUTH
    targets = [t for t in manifest['targets'] if t['workspace'] == profile]
    assert len({t['path'] for t in targets}) == len(targets)
    for t in targets:
        valid_target(t)
    v = modal.Volume.from_name('p012-g0-assets-results-20261111', create_if_missing=False)
    if mode == 'delete':
        assert len(sys.argv) == 4, 'Require published manifest commit'
        published = subprocess.check_output(['git', 'show', sys.argv[3] + ':' + str(PUB / 'DELETION_MANIFEST.json')])
        assert published == (PUB / 'DELETION_MANIFEST.json').read_bytes()
        # The commit must already be reachable on the remote branch.
        subprocess.run(['git', 'merge-base', '--is-ancestor', sys.argv[3], 'origin/codex/icml-acl-2027'], check=True)
    else:
        assert mode == 'verify'
    out = PUB / (profile + ('_PREDELETE_VERIFICATION.json' if mode == 'verify' else '_DELETION_RECEIPT.json'))
    assert not out.exists(), 'Refuse duplicate cleanup operation'
    receipt = {'utc': utc(), 'workspace': profile, 'authority_commit': AUTH, 'mode': mode, 'runs': [],
               'manifest_publication_commit': sys.argv[3] if mode == 'delete' else None}
    for proof in proofs:
        run = proof['run_id']
        subset = [t for t in targets if t['run_id'] == run]
        assert subset
        public_check(proof)
        remote_manifest = b''.join(v.read_file('training/' + run + '/CHECKPOINT_FILES.json'))
        assert sha(remote_manifest) == proof['public_evidence']['checkpoint_manifest']['sha256']
        before = listing(v, 'training/' + run)
        for t in subset:
            assert before[t['path']]['type'] == 1 and before[t['path']]['bytes'] == t['bytes']
        active = active_paths(profile, targets)
        r = {'run_id': run, 'utc': utc(), 'public_evidence_verified': True,
             'remote_checkpoint_manifest_sha256': sha(remote_manifest), 'active_path_check': active,
             'before': before, 'files': subset}
        if mode == 'delete':
            for t in subset:
                # Only exact, published leaf paths. recursive=False is deliberate.
                v.remove_file(t['path'], recursive=False)
            after = listing(v, 'training/' + run)
            expected = {p: x for p, x in before.items() if p not in {t['path'] for t in subset}}
            # Directory mtime can change. Every retained file must keep its size and mtime.
            assert set(after) == set(expected)
            assert all(after[p] == e for p, e in expected.items() if e['type'] == 1)
            r.update(after=after, retained_files_unchanged=True,
                     deleted_bytes=sum(t['bytes'] for t in subset), completed_utc=utc())
        receipt['runs'].append(r)
        write(out, receipt)
        print(mode, profile, run, 'OK', flush=True)
    receipt.update(completed_utc=utc(), complete=True, file_count=len(targets),
                   bytes=sum(t['bytes'] for t in targets), GiB=sum(t['bytes'] for t in targets)/2**30)
    write(out, receipt)


if __name__ == '__main__':
    main()
