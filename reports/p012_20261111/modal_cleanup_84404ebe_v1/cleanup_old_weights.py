"""Exact-path historical cleanup authorized by 84404ebe; never opens tar files."""
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

AUTH = '84404ebe3ef55e5409f7f13cd94019f989d2444c'
VOLUME = 'sft-allocation-midpoint-v1'
ROOTS = ('p010-20261019', 'p011-20261020', 'p011-ext-3B-20261022')
PUB = Path('reports/p012_20261111/modal_cleanup_84404ebe_v1')
LOCAL = Path('.local/p012_20261111/modal_cleanup_84404ebe_v1')
RUNS = Path('.local/p012_20261111/amendment8_modal_runs_v1')
MODAL = '.local/midpoint_20261011/venv/bin/modal'
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(Path(p).read_text())


def write(p, data):
    Path(p).write_text(json.dumps(data, indent=2) + '\n')


def inventory(volume):
    return {'utc': utc(), 'volume': VOLUME, 'files': [
        {'path': e.path, 'type': int(e.type), 'bytes': e.size, 'mtime': e.mtime}
        for e in volume.iterdir('/', recursive=True)]}


def classify(path):
    p = PurePosixPath(path)
    if p.is_absolute() or '..' in p.parts or p.parts[0] not in ROOTS:
        return None
    if p.suffix == '.pt':
        if p.name == 'state.pt' and re.fullmatch(r'checkpoint_\d+', p.parent.name):
            return 'training_state'
        return 'keep_evaluation_or_uncertain_pt'
    if p.suffix == '.safetensors':
        if p.parent.name in ('merged', 'model_for_vllm') and p.name.startswith('model'):
            return 'trained_model_weights'
        if p.parts[1] in ('assets', 'models') and p.name.startswith('model'):
            return 'downloaded_model_weight_cache'
        return 'keep_uncertain_safetensors'
    return None


def active_check():
    apps = json.loads(subprocess.check_output([MODAL, 'app', 'list', '--json'], text=True))
    active = [a for a in apps if a['state'] != 'stopped']
    known = {}
    for log in RUNS.glob('*/run.log'):
        for app in re.findall(r'https://modal.com/apps/tangzhice/main/(ap-[A-Za-z0-9]+)', log.read_text(errors='replace')):
            request = read(log.parent / 'request.json')
            known[app] = (log.parent.name, request, sha((log.parent / 'request.json').read_bytes()))
    checked = []
    # These launchers mount only the P012 volume, never the historical volume.
    sources = {p: sha(Path(p).read_bytes()) for p in (
        'experiments/p012/modal_train.py', 'experiments/p012/modal_g0.py')}
    train = Path('experiments/p012/modal_train.py').read_text()
    common = Path('experiments/p012/modal_g0.py').read_text()
    assert 'from .modal_g0 import digest, volume' in train
    assert 'Volume.from_name("p012-g0-assets-results-20261111"' in common
    assert VOLUME not in train + common
    for app in active:
        assert app['app_id'] in known, 'Unmapped active application: ' + app['app_id']
        run, request, digest = known[app['app_id']]
        assert run.startswith('a8_')
        assert not any(p in json.dumps(request) for p in (VOLUME, *ROOTS))
        checked.append({'app_id': app['app_id'], 'run_id': run,
                        'request_sha256': digest, 'historical_paths_referenced': False})
    return {'utc': utc(), 'workspace': 'tangzhice', 'active_apps': checked,
            'launcher_sources': sources, 'only_mounted_volume': 'p012-g0-assets-results-20261111',
            'historical_volume_unused_by_all_active_apps': True}


def collect(volume):
    assert not (LOCAL / 'before.json').exists(), 'Use the existing immutable inventory'
    inv = inventory(volume)
    write(LOCAL / 'before.json', inv)
    files = {f['path']: f for f in inv['files'] if f['type'] == 1}
    candidates = [f for f in files.values() if classify(f['path'])]
    wanted = set()
    for f in candidates:
        p = PurePosixPath(f['path'])
        if classify(str(p)) == 'training_state':
            wanted.add(str(p.with_name('manifest.json')))
        if classify(str(p)) == 'downloaded_model_weight_cache':
            wanted.add(str(p.parent / '.cache/huggingface/download' / (p.name + '.metadata')))
            wanted.add(str(p.parent / 'DOWNLOAD_VERIFIED.json'))
        if classify(str(p)) == 'trained_model_weights':
            parent = str(p.parent.parent) + '/'
            wanted.update(q for q, v in files.items() if q.startswith(parent)
                          and '/' not in q[len(parent):] and q.endswith('.json') and v['bytes'] < 131072)
    wanted &= files.keys()
    metadata = {}
    for path in sorted(wanted):
        assert path.endswith(('.json', '.metadata')) and files[path]['bytes'] < 131072
        data = b''.join(volume.read_file(path))
        assert len(data) == files[path]['bytes']
        metadata[path] = {'sha256': sha(data), 'bytes': len(data), 'text': data.decode()}
    write(PUB / 'EXISTING_METADATA.json', metadata)
    write(PUB / 'PREDELETE_ACTIVE_APPS.json', active_check())
    with zipfile.ZipFile(PUB / 'BEFORE_INVENTORY.zip', 'x', zipfile.ZIP_DEFLATED) as z:
        z.write(LOCAL / 'before.json', 'before.json')
    print(json.dumps({'inventory_files': len(files), 'candidate_files': len(candidates),
                      'metadata_files_read': len(metadata), 'tar_files_opened': 0}), flush=True)


def remove(volume, commit):
    manifest_path = PUB / 'DELETION_MANIFEST.json'
    manifest = read(manifest_path)
    assert manifest['authority_commit'] == AUTH
    assert subprocess.check_output(['git', 'show', commit + ':' + str(manifest_path)]) == manifest_path.read_bytes()
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'origin/codex/icml-acl-2027'], check=True)
    targets = manifest['targets']
    assert targets and len({t['path'] for t in targets}) == len(targets)
    assert all(t['volume'] == VOLUME and t['workspace'] == 'tangzhice' and
               classify(t['path']) == t['classification'] and not t['classification'].startswith('keep')
               for t in targets)
    receipt_path = PUB / 'DELETION_RECEIPT.json'
    assert not receipt_path.exists(), 'Do not repeat a deletion operation'
    before = read(LOCAL / 'before.json')
    fresh = inventory(volume)
    original = {f['path']: f for f in before['files']}
    current = {f['path']: f for f in fresh['files']}
    assert original == current, 'Historical volume changed since public manifest preparation'
    for t in targets:
        assert current[t['path']]['type'] == 1 and current[t['path']]['bytes'] == t['bytes']
    receipt = {'utc': utc(), 'authority_commit': AUTH, 'manifest_publication_commit': commit,
               'manifest_sha256': sha(manifest_path.read_bytes()), 'workspace': 'tangzhice',
               'volume': VOLUME, 'active_app_checks': [], 'deleted': [], 'complete': False,
               'tar_files_opened': 0, 'recursive_deletions': 0}
    for root in ROOTS:
        receipt['active_app_checks'].append(active_check())
        write(receipt_path, receipt)
        for t in [t for t in targets if PurePosixPath(t['path']).parts[0] == root]:
            volume.remove_file(t['path'], recursive=False)
            receipt['deleted'].append({'path': t['path'], 'bytes': t['bytes'], 'utc': utc()})
            write(receipt_path, receipt)
        print('deleted approved leaves in', root, flush=True)
    after = inventory(volume)
    write(LOCAL / 'after.json', after)
    actual = {f['path']: f for f in after['files']}
    paths = {t['path'] for t in targets}
    assert set(original) - set(actual) == paths
    assert set(actual) - set(original) == set()
    # Directory timestamps may change; all retained files must be byte-size/mtime-identical.
    assert all(actual[p] == f for p, f in original.items() if f['type'] == 1 and p not in paths)
    receipt.update(complete=True, completed_utc=utc(), removed_paths_exactly_manifest=True,
                   retained_files_metadata_unchanged=True, retained_regular_files=sum(f['type'] == 1 for f in actual.values()),
                   tar_files_retained=sum(f['type'] == 1 and p.endswith('.tar') for p, f in actual.items()),
                   deleted_files=len(paths), deleted_bytes=sum(t['bytes'] for t in targets),
                   deleted_GiB=sum(t['bytes'] for t in targets) / 2**30,
                   volume_after_GiB=sum(f['bytes'] for f in actual.values() if f['type'] == 1) / 2**30)
    write(receipt_path, receipt)
    with zipfile.ZipFile(PUB / 'AFTER_INVENTORY.zip', 'x', zipfile.ZIP_DEFLATED) as z:
        z.write(LOCAL / 'after.json', 'after.json')
    print(json.dumps({k: receipt[k] for k in ('complete', 'deleted_files', 'deleted_GiB', 'volume_after_GiB')}), flush=True)


def main():
    assert os.environ.get('MODAL_PROFILE') == 'tangzhice'
    PUB.mkdir(exist_ok=True); LOCAL.mkdir(parents=True, exist_ok=True)
    volume = modal.Volume.from_name(VOLUME, create_if_missing=False)
    if sys.argv[1] == 'collect':
        collect(volume)
    elif sys.argv[1] == 'delete':
        assert len(sys.argv) == 3
        remove(volume, sys.argv[2])
    else:
        raise ValueError('Only collect or delete modes')


if __name__ == '__main__':
    main()
