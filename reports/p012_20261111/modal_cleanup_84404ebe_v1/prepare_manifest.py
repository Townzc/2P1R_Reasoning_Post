"""Build the owner-authorized leaf manifest using existing small metadata only."""
import collections
import json
from pathlib import Path, PurePosixPath
import subprocess
from cleanup_old_weights import AUTH, LOCAL, PUB, ROOTS, VOLUME, classify, read, sha, utc, write


def existing_hash(path, size, metadata):
    p = PurePosixPath(path)
    options = []
    if p.name == 'state.pt':
        source = str(p.with_name('manifest.json'))
        m = json.loads(metadata[source]['text'])
        assert m['file'] == 'state.pt' and m['bytes'] == size
        assert m['schema'] in ('complete_lora_v1', 'p011_complete_training_state_v1', 'p011_ext4b_resume_state_v1')
        assert m['step'] == int(p.parent.name.split('_')[1])
        return m['sha256'], [{'path': source, 'metadata_sha256': metadata[source]['sha256'],
                              'field': 'sha256', 'schema': m['schema']}]
    if p.parent.name in ('merged', 'model_for_vllm'):
        for name, field in [('MERGE_PROOF.json', 'merged_files'), ('MODEL_EXPORT.json', 'files'),
                            ('ORIGINAL_MODEL_PROOF.json', 'merged_files'),
                            ('ORIGINAL_MODEL_PROOF.json', 'actual_merged_files')]:
            source = str(p.parent.parent / name)
            if source not in metadata:
                continue
            m = json.loads(metadata[source]['text'])
            if field not in m:
                continue
            value = m[field][p.name]
            assert value['bytes'] == size
            options.append((value['sha256'], {'path': source, 'metadata_sha256': metadata[source]['sha256'],
                                             'field': field + '/' + p.name + '/sha256'}))
    if p.parts[1] in ('assets', 'models'):
        source = str(p.parent / '.cache/huggingface/download' / (p.name + '.metadata'))
        if source in metadata:
            lines = metadata[source]['text'].splitlines()
            assert len(lines[1]) == 64 and all(c in '0123456789abcdef' for c in lines[1])
            options.append((lines[1], {'path': source, 'metadata_sha256': metadata[source]['sha256'],
                                      'field': 'Hugging Face local download metadata LFS SHA256',
                                      'revision': lines[0]}))
        if str(p.parent) == 'p011-20261020/models/qwen3b_instruct':
            source = 'reports/p011_20261020/long_preflight_runtime_v1/SPEC.json'
            model = read(source)['jobs']['preflight_S-L3_s17_r1']['model']
            assert model['remote_path'] == '/evidence/' + str(p.parent)
            value = model['files'][p.name]
            assert value['bytes'] == size
            options.append((value['sha256'], {'path': source, 'metadata_sha256': sha(Path(source).read_bytes()),
                'field': 'jobs/preflight_S-L3_s17_r1/model/files/' + p.name + '/sha256'}))
    if options:
        assert len({h for h, _ in options}) == 1
        return options[0][0], [o for _, o in options]
    return None, []


def main():
    before = read(LOCAL / 'before.json')
    metadata = read(PUB / 'EXISTING_METADATA.json')
    targets, keep = [], []
    for f in sorted(before['files'], key=lambda f: f['path']):
        if f['type'] != 1:
            continue
        kind = classify(f['path'])
        if kind is None:
            continue
        if kind.startswith('keep'):
            keep.append({**f, 'reason': kind})
            continue
        digest, source = existing_hash(f['path'], f['bytes'], metadata)
        targets.append({'workspace': 'tangzhice', 'volume': VOLUME, 'path': f['path'],
                        'bytes': f['bytes'], 'mtime': f['mtime'], 'classification': kind,
                        'utc': utc(), 'sha256': digest, 'existing_hash_sources': source,
                        'hash_note': 'Existing recorded digest; large weight/state file not downloaded or rehashed.'
                        if digest else 'No adjacent existing SHA256 record found; path and byte size recorded.'})
    assert len(targets) == 112 and sum(t['bytes'] for t in targets) / 2**30 == 514.4089684039354
    assert len([t for t in targets if t['classification'] == 'training_state']) == 36
    assert all(t['sha256'] for t in targets if t['classification'] == 'training_state')
    by_root, by_type = {}, {}
    for key, table in [(lambda t: PurePosixPath(t['path']).parts[0], by_root), (lambda t: t['classification'], by_type)]:
        for name in sorted({key(t) for t in targets}):
            subset = [t for t in targets if key(t) == name]
            table[name] = {'files': len(subset), 'bytes': sum(t['bytes'] for t in subset),
                           'GiB': sum(t['bytes'] for t in subset) / 2**30}
    out = {'utc': utc(), 'authority_commit': AUTH, 'allowed_roots': ROOTS,
           'before_inventory_sha256': sha((LOCAL / 'before.json').read_bytes()),
           'metadata_sha256': sha((PUB / 'EXISTING_METADATA.json').read_bytes()),
           'targets': targets, 'retained_uncertain_or_evaluation_candidates': keep,
           'by_root': by_root, 'by_type': by_type, 'target_files': len(targets),
           'target_GiB': sum(t['bytes'] for t in targets) / 2**30,
           'targets_with_existing_sha256': sum(bool(t['sha256']) for t in targets),
           'targets_without_existing_sha256': [t['path'] for t in targets if not t['sha256']],
           'tar_files_opened': 0, 'deletion_not_yet_executed': True,
           'classification_sources': {p: sha(Path(p).read_bytes()) for p in (
               'experiments/sft_allocation_midpoint/checkpoint.py', 'experiments/p011/long_checkpoint.py',
               'experiments/p010/student_training.py', 'experiments/p011/long_lr_r2_training.py',
               'experiments/p011/ext4b_training.py')}}
    write(PUB / 'DELETION_MANIFEST.json', out)
    (PUB / 'AUTHORITY.md').write_bytes(subprocess.check_output([
        'git', 'show', AUTH + ':audit/claude/20261114i/MODAL_CLEANUP_ADDENDUM.md']))
    (PUB / 'README.md').write_text(
        '# Historical Modal weight cleanup authorized by 84404ebe\n\n'
        'The deletion manifest names 112 exact leaves (514.408968 GiB) in three owner-authorized '
        'historical project directories. It must be published before deletion. Only model weights, '
        'downloaded model-weight cache files and manifest-identified training state are selected. '
        'All other files and directories are retained. No tar archive is opened.\n\n'
        'EXISTING_METADATA.json preserves small, pre-existing hash proofs; no model or state is '
        'downloaded merely to hash it. BEFORE_INVENTORY.zip contains the complete historical volume '
        'directory listing. PREDELETE_ACTIVE_APPS.json maps every active app to a reviewed A8 request '
        'and its P012-only volume mount. Deletion uses exact published paths and recursive=False. '
        'The after-inventory and receipt must prove the removed path set equals the manifest and '
        'all retained regular files keep their size and timestamp.\n\n'
        'Main-grid P/K8/R, all other P012 weights, and A8 weights remain. A8 weights require endpoint '
        'acceptance before their separate cleanup. Account and billing settings are unchanged.\n')
    print(json.dumps({k: out[k] for k in ('target_files', 'target_GiB', 'targets_with_existing_sha256',
                                        'targets_without_existing_sha256', 'retained_uncertain_or_evaluation_candidates')}))


if __name__ == '__main__':
    main()
