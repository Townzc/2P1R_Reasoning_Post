"""Prepared finite CPU-only continuation. Requires a published failure admission.

Never call this for a live or completed original audit. It has no student or
teacher entry point, no GPU, no controller, and no automatic retry.
"""
from pathlib import Path
import json
import subprocess
import sys
import time
import modal
from .modal_token_student_runner import ROOT, SOURCES as ORIGINAL_SOURCES, image as original_image

ADMISSION = 'reports/sft_allocation_midpoint_20261011/P007B_FINAL_CPU_AUDIT_CONTINUATION_ADMISSION.json'
SOURCES = ORIGINAL_SOURCES + ['experiments/sft_allocation_acquisition/audit_continuation.py',
                            'experiments/sft_allocation_acquisition/modal_audit_continuation.py', ADMISSION]
image = original_image
for name in SOURCES[len(ORIGINAL_SOURCES):]:
    image = image.add_local_file(ROOT / name, '/workspace/' + name, copy=True)
app = modal.App('sft-allocation-final-audit-continuation')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)


@app.function(image=image, cpu=(2, 2), memory=(8192, 8192), timeout=3400, startup_timeout=300,
              retries=0, max_containers=1, min_containers=0, buffer_containers=0, scaledown_window=2,
              single_use_containers=True, serialized=True, include_source=False, volumes={'/evidence': volume})
def audit_remaining(binding, release):
    started = time.time()
    import os
    import threading
    import traceback
    import uuid
    from concurrent.futures import ThreadPoolExecutor, as_completed
    sys.path.insert(0, '/workspace')
    from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_acquisition.audit_continuation import validate_partition, verify_carried, verify_remaining
    admission = read('/workspace/' + ADMISSION)
    if digest(binding) != admission['binding_sha256'] or admission['status'] != 'admitted_after_original_stopped':
        raise ValueError('No published exact continuation admission')
    spec = read('/workspace/reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json')
    roster = validate_partition(binding, spec)
    for name, value in release['source_files'].items():
        if sha(Path('/workspace') / name) != value:
            raise ValueError('Unpublished source bytes')
    claims = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
    parent_prefix = 'midpoint/' + binding['parent']['campaign'] + '/'
    parent_claim = claims.get(parent_prefix + 'claim/audit')
    if digest(parent_claim) != binding['parent']['claim_sha256']:
        raise ValueError('Original claim changed')
    parent_terminal = claims.get(parent_prefix + 'terminal/audit')
    if parent_terminal and parent_terminal['status'] == 'completed':
        raise ValueError('Original audit already completed')
    def terminal_get(campaign, run):
        return claims.get('midpoint/' + campaign + '/terminal/' + run)
    volume.reload()
    plan = binding['plan']
    guard = RunGuard(claims, plan)
    guard.register(now_epoch=time.time())
    won = guard.admit(dict(run_id='audit_remaining', config_sha256=digest(binding),
                           source_sha256=digest(release['source_files']), data_sha256=binding['reconciliation_sha256']),
                      attempt_id=uuid.uuid4().hex, now_epoch=time.time(), max_runtime_seconds=3360)
    stop = min(started + 3300, plan['deadline_epoch'] - 30)
    timer = threading.Timer(max(1, stop - time.time()), lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    out = Path('/evidence') / plan['campaign_id'] / 'audit_remaining'
    try:
        out.mkdir(parents=True, exist_ok=False)
        dump(out / 'intent.json', dict(binding=binding, release=release))
        carried = verify_carried('/evidence', binding, spec, terminal_get)
        results = dict(carried)
        for label, value in carried.items():
            dump(out / (label + '.json'), value)
        dump(out / 'carried_provenance.json', dict(parent=binding['parent'], carried=binding['carried'],
                                                  reconciliation_sha256=binding['reconciliation_sha256']))
        volume.commit()
        terminals = {label: terminal_get(**dict(campaign=roster[label]['campaign'], run=roster[label]['run']))
                     for label in binding['remaining']}
        def one(label):
            if time.time() >= stop - 60:
                raise TimeoutError('Finite CPU continuation deadline')
            return verify_remaining('/evidence', roster[label], terminals[label])
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(one, label): label for label in binding['remaining']}
            for future in as_completed(futures):
                guard.check_active(won, now_epoch=time.time(), spent_cents=0, next_cost_cents=300)
                label = futures[future]
                results[label] = future.result()
                dump(out / (label + '.json'), results[label])
                volume.commit()
        if set(results) != set(roster):
            raise ValueError('Incomplete combined CPU audit')
        dump(out / 'result.json', results)
        volume.commit()
        files = manifest(out)
        dump(out / 'artifact_manifest.json', files)
        volume.commit()
        receipt = guard.finish(won, status='completed', evidence_sha256=digest(files), actual_cost_cents=300, finished_epoch=time.time())
        return dict(result=results, artifact_manifest=files, receipt=receipt,
                    continuation=dict(parent=binding['parent'], carried=sorted(carried), newly_verified=binding['remaining']))
    except BaseException as exc:
        if out.exists():
            dump(out / 'failure.json', dict(error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc(),
                                            rule='Keep parent/child partial proof. No replay or automatic retry.'))
            volume.commit()
            files = manifest(out)
            dump(out / 'failure_manifest.json', files)
            volume.commit()
            guard.finish(won, status='failed', evidence_sha256=digest(files), actual_cost_cents=300, finished_epoch=time.time())
        raise
    finally:
        timer.cancel()


@app.local_entrypoint()
def main(binding_json: str, receipt_dir: str):
    from experiments.sft_allocation_midpoint.common import read, dump, sha, digest
    from experiments.sft_allocation_acquisition.audit_continuation import validate_partition
    binding = read(binding_json)
    admission = read(ROOT / ADMISSION)
    if digest(binding) != admission['binding_sha256'] or admission['status'] != 'admitted_after_original_stopped':
        raise ValueError('Unadmitted repair')
    validate_partition(binding, read(ROOT / 'reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json'))
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/codex/icml-acl-2027'], cwd=ROOT, text=True).split()[0]
    if commit != remote:
        raise ValueError('Publish first')
    for name in SOURCES:
        if subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT) != (ROOT / name).read_bytes():
            raise ValueError('Unpublished source')
    cli = str(Path(sys.executable).with_name('modal'))
    containers = json.loads(subprocess.check_output([cli, 'container', 'list', '--json']))
    apps = json.loads(subprocess.check_output([cli, 'app', 'list', '--json']))
    parent = next(a for a in apps if a['app_id'] == binding['parent']['provider']['app_id'])
    if containers or parent['state'] != 'stopped' or str(parent['tasks']) != '0':
        raise ValueError('Original worker not confirmed released')
    claims = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
    prefix = 'midpoint/' + binding['plan']['campaign_id'] + '/'
    if any(k.startswith(prefix) for k in claims.keys()):
        raise ValueError('Continuation already has records; never dispatch twice')
    old_prefix = 'midpoint/' + binding['parent']['campaign'] + '/'
    if digest(claims.get(old_prefix + 'claim/audit')) != binding['parent']['claim_sha256']:
        raise ValueError('Parent claim differs')
    terminal = claims.get(old_prefix + 'terminal/audit')
    if terminal and terminal['status'] == 'completed':
        raise ValueError('Completed parent cannot be continued')
    from modal.exception import NotFoundError
    try:
        entries = list(volume.iterdir('/' + binding['plan']['campaign_id'] + '/audit_remaining'))
    except NotFoundError:
        entries = []
    if entries:
        raise ValueError('Continuation evidence directory already exists')
    out = Path(receipt_dir)
    out.mkdir(parents=True, exist_ok=False)
    release = dict(commit=commit, source_files={n: sha(ROOT / n) for n in SOURCES})
    dump(out / 'intent.json', dict(binding=binding, release=release, provider=parent, containers=containers))
    result = audit_remaining.remote(binding, release)
    dump(out / 'result.json', result)
