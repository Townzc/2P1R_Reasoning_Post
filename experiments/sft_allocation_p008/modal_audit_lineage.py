"""Prepared single-use CPU audit of the original failed-parent/child chain.

No current admission file exists. No generation/training/retries/GPU/controller.
Original remote records are retained; only container-local copies are removed.
"""
from pathlib import Path
import json
import subprocess
import sys
import time
import modal

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    'experiments/sft_allocation_midpoint/common.py',
    'experiments/sft_allocation_midpoint/checkpoint.py',
    'experiments/sft_allocation_midpoint/guard.py',
    'experiments/sft_allocation_p008/contract.py',
    'experiments/sft_allocation_p008/evidence_bundle.py',
    'experiments/sft_allocation_p008/audit_bundle.py',
    'experiments/sft_allocation_p008/audit_binding.py',
    'experiments/sft_allocation_p008/pool_lineage.py',
    'experiments/sft_allocation_p008/audit_continued_pool.py',
    'experiments/sft_allocation_p008/provider_release.py',
    'experiments/sft_allocation_p008/audit_lineage_binding.py',
    'experiments/sft_allocation_p008/completion_queue.py',
    'experiments/sft_allocation_p008/modal_audit_lineage.py',
]
SPEC = 'reports/p008_20261013/final_audit_lineage_admission_v1/ADMISSION.json'
app = modal.App('p008-finite-lineage-cpu-audit')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
         .pip_install('torch==2.8.0', index_url='https://download.pytorch.org/whl/cpu')
         .pip_install('numpy==2.2.6').env({'PYTHONPATH': '/workspace'}))
for name in SOURCES:
    image = image.add_local_file(ROOT / name, '/workspace/' + name, copy=True)
image = image.add_local_file(ROOT / SPEC, '/workspace/' + SPEC, copy=True)


@app.function(image=image, cpu=(4, 4), memory=(16384, 16384), timeout=3500,
              startup_timeout=600, retries=0, max_containers=1, min_containers=0,
              buffer_containers=0, scaledown_window=2, single_use_containers=True,
              serialized=True, include_source=False, volumes={'/evidence': volume})
def work(binding, release):
    started = time.time()
    import os
    import threading
    import tempfile
    import traceback
    import uuid
    from concurrent.futures import ThreadPoolExecutor, as_completed
    # The timer includes imports, validation and original-source reads.
    stop = min(started + 3300, binding['plan']['deadline_epoch'] - 30)
    timer = threading.Timer(max(1, stop - time.time()), lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    won = out = guard = None
    aborted = threading.Event()
    try:
        sys.path.insert(0, '/workspace')
        from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify, manifest
        from experiments.sft_allocation_midpoint.guard import RunGuard
        from experiments.sft_allocation_p008.audit_binding import check_soft_deadline
        from experiments.sft_allocation_p008.audit_lineage_binding import (
            validate, validate_all_labels, source_key, PARENT_LABEL, PARENT_ARCHIVE, CHILD_RUN)
        from experiments.sft_allocation_p008.audit_bundle import verify_packed_run
        from experiments.sft_allocation_p008.audit_continued_pool import verify_failed_parent, verify_completed_child
        from experiments.sft_allocation_p008.evidence_bundle import pack
        import torch
        torch.set_num_threads(2)

        def check():
            if aborted.is_set():
                raise RuntimeError('A source failed; preserve partial proofs without replay')
            check_soft_deadline(time.time(), stop)

        check()
        spec = read('/workspace/' + SPEC)
        roster = validate(binding, spec, release)
        plan, cfg = binding['plan'], binding['config']
        if set(release['source_files']) != set(SOURCES):
            raise ValueError('Complete published CPU source roster required')
        for name, value in release['source_files'].items():
            if sha(Path('/workspace') / name) != value:
                raise ValueError('Unpublished CPU code')
        claims = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
        from experiments.sft_allocation_p008.completion_queue import require_handoff
        require_handoff(claims, plan, binding['original_plan'], binding['student_completion_owner'], 'audit')
        prefix = 'midpoint/' + plan['campaign_id'] + '/'
        for item in binding['labels'].values():
            check()
            if (claims.get(source_key(item, 'terminal')) != item['terminal']
                    or claims.get(source_key(item, 'claim')) != item['claim']):
                raise ValueError('Actual original claim/terminal differs')
        check()
        volume.reload()
        inputs = Path('/evidence') / plan['campaign_id'] / cfg['input_directory']
        if read(inputs / 'manifest.json') != binding['input_manifest']:
            raise ValueError('Foreign immutable inputs')
        verify(inputs, binding['input_manifest']['files'])
        check()
        labels = validate_all_labels(binding, {n: read(inputs / (n + '.json')) for n in sorted(roster)})
        guard = RunGuard(claims, plan)
        guard.register(now_epoch=time.time())
        won = guard.admit(dict(run_id='audit', config_sha256=digest(binding),
            source_sha256=digest(release['source_files']), data_sha256=digest(binding['input_manifest'])),
            attempt_id=uuid.uuid4().hex, now_epoch=time.time(), max_runtime_seconds=3300)
        out = Path('/evidence') / plan['campaign_id'] / 'audit'
        out.mkdir(parents=True, exist_ok=False)
        dump(out / 'intent.json', dict(binding=binding, release=release,
                                     started_epoch=started, hard_stop_epoch=stop))
        dump(out / 'admission.json', spec)
        volume.commit()
        results = {}

        def one(name):
            check()
            item = labels[name]
            with tempfile.TemporaryDirectory(prefix='p008-lineage-audit-') as tmp:
                destination = Path(tmp) / 'checked'
                if name == PARENT_LABEL:
                    return verify_failed_parent(inputs / PARENT_ARCHIVE, destination, item, check)
                source = Path('/evidence') / item['campaign'] / item['run_id']
                if name == CHILD_RUN:
                    return verify_completed_child(source, destination, item, check)
                return verify_packed_run(source, destination, item, check)

        for name in sorted(roster):
            check()
            item = binding['labels'][name]
            unit = dict(label_sha256=digest(labels[name]), campaign=item['campaign'],
                        source_run_id=item['run_id'], original_terminal=item['terminal'])
            if not claims.put(prefix + 'audit/unit/' + name, unit, skip_if_exists=True):
                raise ValueError('Prior or uncertain CPU unit; no replay')
            dump(out / 'intents' / (name + '.json'), unit)
        volume.commit()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(one, name): name for name in sorted(roster)}
            try:
                for future in as_completed(futures):
                    name = futures[future]
                    proof = future.result()
                    check()
                    guard.check_active(won, now_epoch=time.time(), spent_cents=0, next_cost_cents=500)
                    dump(out / 'proofs' / (name + '.json'), proof)
                    volume.commit()
                    done = dict(proof_sha256=sha(out / 'proofs' / (name + '.json')),
                                label_sha256=digest(labels[name]))
                    if not claims.put(prefix + 'audit/done/' + name, done, skip_if_exists=True):
                        raise ValueError('Duplicate CPU completion')
                    dump(out / 'completed' / (name + '.json'), done)
                    volume.commit()
                    results[name] = proof
            except BaseException:
                aborted.set()
                for future in futures:
                    future.cancel()
                raise
        check()
        if set(results) != roster:
            raise ValueError('Incomplete physical-source final audit')
        result = dict(passed=True, labels=results, logical_runs=21, physical_sources=22,
            original_d2_status='failed', child_status='completed', wall_seconds=time.time() - started,
            reserved_cost_usd=5, provider_invoice_usd=None, new_model_calls=0,
            scope='Original compact bytes and full states; merged raw/dose oracles bound, not rescored')
        dump(out / 'result.json', result)
        volume.commit()
        check()
        pack(out)
        volume.commit()
        check()
        files = manifest(out)
        dump(out / 'artifact_manifest.json', files)
        volume.commit()
        check()
        receipt = guard.finish(won, status='completed', evidence_sha256=digest(files),
                               actual_cost_cents=500, finished_epoch=time.time())
        return dict(result=result, artifact_manifest=files, receipt=receipt)
    except BaseException as exc:
        if out is not None and out.exists() and won is not None:
            dump(out / 'failure.json', dict(error_type=type(exc).__name__, error=str(exc),
                traceback=traceback.format_exc(), rule='Preserve all original/partial proofs; no retry'))
            volume.commit()
            files = manifest(out)
            dump(out / 'failure_manifest.json', files)
            volume.commit()
            guard.finish(won, status='failed', evidence_sha256=digest(files),
                         actual_cost_cents=500, finished_epoch=time.time())
        raise
    finally:
        timer.cancel()


@app.local_entrypoint()
def main(binding_json: str, receipt_dir: str):
    from experiments.sft_allocation_midpoint.common import read, dump, sha, digest
    from experiments.sft_allocation_p008.audit_lineage_binding import validate, source_key, validate_all_labels
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    from modal.exception import NotFoundError
    binding = read(binding_json)
    plan, cfg, root = binding['plan'], binding['config'], Path(binding_json).parent

    def window():
        if time.time() + 4000 > plan['deadline_epoch']:
            raise ValueError('Full CPU/startup window unavailable; leave pending')

    window()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(['git', 'ls-remote', 'origin',
        'refs/heads/codex/icml-acl-2027'], cwd=ROOT, text=True).split()[0]
    if commit != remote:
        raise ValueError('Ordinary publication required')
    for name in SOURCES + [SPEC]:
        if subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT) != (ROOT / name).read_bytes():
            raise ValueError('Unpublished source/spec')
    spec = read(ROOT / SPEC)
    release = dict(commit=commit, source_files={n: sha(ROOT / n) for n in SOURCES}, spec_sha256=digest(spec))
    roster = validate(binding, spec, release)
    uploaded = read(root / 'UPLOAD_VERIFIED.json')
    if (uploaded['passed'] is not True or uploaded['binding_sha256'] != digest(binding)
            or uploaded['input_manifest_sha256'] != digest(binding['input_manifest'])):
        raise ValueError('Exact input readback required')
    cli = str(Path(sys.executable).with_name('modal'))
    containers = json.loads(subprocess.check_output([cli, 'container', 'list', '--json'], text=True))
    apps = read_stopped_apps(cli, [binding['labels'][n]['app_id'] for n in sorted(roster)], containers)
    claims = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
    from experiments.sft_allocation_p008.completion_queue import require_handoff
    require_handoff(claims, plan, binding['original_plan'], binding['student_completion_owner'], 'audit')
    prefix = 'midpoint/' + plan['campaign_id'] + '/'
    if any(claims.get(prefix + kind + '/audit') is not None for kind in ('claim', 'intent', 'terminal')):
        raise ValueError('Existing/uncertain CPU attempt')
    if any(k.startswith(prefix + 'audit/') for k in claims.keys()):
        raise ValueError('Existing CPU units')
    for item in binding['labels'].values():
        if (claims.get(source_key(item, 'terminal')) != item['terminal']
                or claims.get(source_key(item, 'claim')) != item['claim']):
            raise ValueError('Actual source claim/terminal changed')
    try:
        entries = list(volume.iterdir('/' + plan['campaign_id'] + '/audit'))
    except NotFoundError:
        entries = []
    if entries:
        raise ValueError('Existing remote CPU evidence')
    labels = {n: read(root / cfg['input_directory'] / (n + '.json')) for n in sorted(roster)}
    validate_all_labels(binding, labels)
    target = Path(receipt_dir)
    if target.resolve() != (root / 'runs' / 'audit').resolve():
        raise ValueError('Canonical new CPU receipt directory required')
    window()  # Recheck after all potentially slow provider and ledger reads.
    target.mkdir(parents=True, exist_ok=False)
    dump(target / 'dispatch_intent.json', dict(binding=binding, release=release,
                                             provider_before=apps, containers=containers))
    call = work.spawn(binding, release)
    dump(target / 'submitted.json', dict(call_id=call.object_id))
    try:
        dump(target / 'result.json', call.get())
    except BaseException as exc:
        dump(target / 'return_error.json', dict(type=type(exc).__name__, error=str(exc)))
        raise
