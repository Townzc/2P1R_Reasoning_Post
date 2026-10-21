"""One separately authorized C1 r2 attempt, pending its exact CR/A2.

The dedicated shared ledger is used by all future P011 entry paths. No caller
may reconstruct a missing submission, clear a fence, or retry an unknown call.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import traceback

from experiments.p011.c1_r2 import admission, execution as c1_execution, artifacts as c1_artifacts
from experiments.p011 import c1_outer as original_lifecycle
from experiments.p011.c1_r2 import parent
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest
from experiments.p011.c1_r2.inputs import load_pack

LOGICAL = 'C1_original_token_base_forward_r2'
KEY = 'c1/original_token_base_forward_r2'
LOCAL = '.local/p011_20261020/r1'
REMOTE = '/evidence/p011-20261020/c1_original_token_base_forward_r2'
INPUTS = '/evidence/p011-20261020/c1_inputs_r1'
STORE = 'p011-once-20261020'
SPEC = 'reports/p011_20261020/c1_r2_runtime_v1/SPEC.json'


def published(root, spec):
    """Exact complete source/spec files must be committed and remotely published."""
    root = Path(root)
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, timeout=45)
    if git('branch', '--show-current').decode().strip() != 'codex/icml-acl-2027':
        raise ValueError('Original ordinary execution branch required')
    head = git('rev-parse', 'HEAD').decode().strip()
    remote = git('ls-remote', 'origin', 'refs/heads/codex/icml-acl-2027').decode().split()
    if len(remote) != 2 or remote[0] != head:
        raise ValueError('Exact execution commit not independently remote verified')
    admission.exact_source(spec, root)
    for name in [*spec['source_files'], SPEC]:
        if git('show', head+':'+name) != (root/name).read_bytes():
            raise ValueError('Runtime source/spec differs from the published commit')
    return head


def provider(root, records):
    """One bounded provider observation. Read failures stay unknown; no retry."""
    cli = str(Path(root)/'.local/midpoint_20261011/venv/bin/modal')
    def call(*args):
        return json.loads(subprocess.check_output([cli, *args, '--json'],
            text=True, stderr=subprocess.PIPE, timeout=45))
    containers = call('container', 'list')
    if not isinstance(containers, list):
        raise ValueError('Complete container listing unavailable')
    states = {x['app_id']: 'stopped' for x in records if x.get('saved_provider')}
    active = [x['app_id'] for x in records if x.get('app_id') and not x.get('saved_provider')]
    def state(app):
        try:
            value = call('app', 'info', app)
            if value['app_id'] != app:
                raise ValueError('Provider identity differs')
            return app, value['lifecycle']['state']
        except Exception:
            return app, 'unknown'
    with ThreadPoolExecutor(max_workers=2) as readers:
        states.update(dict(readers.map(state, active)))
    return {'containers': containers, 'states': states, 'observed_epoch': time.time()}


def submit(root, spec, spec_file, review_file, budget_file, store, worker, app_id,
           publication=published, observation=provider):
    """One local intent, remote permanent dispatch fence, and exactly one spawn."""
    root = Path(root)
    execution = publication(root, spec)
    review = read(review_file)
    clean = admission.reviewed_path(spec, spec_file, review)
    raw_report = Path(review['local_report_path']).read_text()
    if hashlib.sha256(raw_report.encode()).hexdigest() != review['report_sha256']:
        raise ValueError('Report must preserve exact UTF8 bytes')
    budget = read(budget_file)
    upload = parent.original_upload(root,spec)
    if (upload.get('spec_file_sha256') != spec['reused_input_upload']['original_spec_file_sha256']
            or upload.get('input_files') != spec['input_files']
            or upload.get('source_files') != spec['reused_input_upload']['original_source_files']
            or upload.get('all_remote_file_bytes_read_back') is not True):
        raise ValueError('Exact one-time input upload and complete SHA readback required')
    # Validate the one copied original-token pack again as input to this new path.
    load_pack(root/LOCAL/'c1_inputs_r1', spec['input_files'], spec['task_inventory'])
    base = root/LOCAL
    base.mkdir(parents=True, exist_ok=True)
    with (base/'dispatch.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        records = parent.records_with_failed_parent(root,spec,original_lifecycle.ledger(root))
        parent.remote_fences(root,spec,store)
        observed = observation(root, records)
        checked = admission.fresh_budget(spec, budget, records, observed['containers'],
            observed['states'], time.time(), root)
        out = base/'dispatch'/LOGICAL
        if out.exists() or any(store.get(KEY+'/'+x) is not None for x in ('dispatch', 'claim', 'terminal')):
            raise ValueError('Original C1 attempt/fence already exists; no replay')
        if not re.fullmatch(r'ap-[A-Za-z0-9]+', app_id):
            raise ValueError('Actual current app identity required before dispatch')
        intent = {'logical_id': LOGICAL, 'execution': execution, 'app_id': app_id,
            'spec_sha256': digest(spec), 'spec_file_sha256': sha(spec_file),
            'budget': checked, 'budget_source_sha256': sha(budget_file),
            'budget_observed_epoch': budget['observed_epoch'], 'review': clean,
            'provider_observation': observed, 'dispatch_epoch': time.time(),
            'prior_attempt_records': records,
            'original_failed_parent_binding':spec['prior_failed_C1'],
            'automatic_retry_allowed': False}
        out.mkdir(parents=True, exist_ok=False)
        dump(out/'INTENT.json', intent)
        with (out/'BUDGET_SOURCE.json').open('xb') as handle:
            handle.write(Path(budget_file).read_bytes())
        with (out/'ORIGINAL_REPORT.md').open('xb') as handle:
            handle.write(raw_report.encode())
        # Fence precedes spawn. Any later error permanently consumes this attempt.
        if not store.put(KEY+'/dispatch', intent, skip_if_exists=True):
            raise ValueError('Global original dispatch already consumed')
        call = worker.spawn(intent, raw_report)
        dump(out/'SUBMITTED.json', {'logical_id': LOGICAL, 'app_id': app_id,
            'call_id': call.object_id, 'submitted_epoch': time.time()})
    try:
        result = call.get()
        dump(out/'RESULT.json', result)
        return result
    except BaseException as exc:
        dump(out/'RETURN_ERROR.json', {'type': type(exc).__name__, 'message': str(exc),
            'observed_epoch': time.time(), 'cloud_failure_not_inferred': True,
            'automatic_retry_allowed': False})
        raise


def worker_body(spec, spec_file, source_root, intent, raw_report, store, volume,
                timer_factory, out=REMOTE, inputs=INPUTS, loader=c1_execution.load_base):
    """Exact original input and review checked before first immutable worker claim."""
    start = time.time()
    c1_execution.validate_spec(spec)
    timer = timer_factory(spec['limits']['worker_seconds'])
    out = Path(out)
    claimed = False
    try:
        admission.exact_source(spec, source_root)
        if (intent['logical_id'] != LOGICAL or intent['spec_sha256'] != digest(spec)
                or intent['spec_file_sha256'] != sha(spec_file)
                or store.get(KEY+'/dispatch') != intent
                or not 0 <= start-intent['dispatch_epoch'] <= spec['limits']['startup_seconds']
                or not 0 <= start-intent['budget_observed_epoch'] <= 3600
                or start+spec['limits']['worker_seconds']+spec['limits']['closeout_seconds']
                    > c1_execution.CUTOFF_EPOCH
                or hashlib.sha256(raw_report.encode()).hexdigest() != intent['review']['report_sha256']):
            raise ValueError('Original admitted dispatch/source/report/window changed')
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'original_report.md'
            report.write_bytes(raw_report.encode())
            admission.reviewed_path(spec, spec_file, {**intent['review'], 'local_report_path': str(report)})
        volume.reload()
        if out.exists():
            raise ValueError('Original remote output exists; partial cannot retry')
        tasks, memberships = load_pack(inputs, spec['input_files'], spec['task_inventory'])
        claim = {'logical_id': LOGICAL, 'execution': intent['execution'],
            'app_id': intent['app_id'], 'dispatch_sha256': digest(intent), 'worker_start_epoch': start}
        if not store.put(KEY+'/claim', claim, skip_if_exists=True):
            raise ValueError('Original C1 claim already exists')
        claimed = True
        out.mkdir(parents=True, exist_ok=False)
        dump(out/'ADMISSION.json', intent)
        dump(out/'CLAIM.json', claim)
        volume.commit()
        basis = {'source_files': spec['source_files'], 'input_files': spec['input_files'],
            'model': spec['model'], 'original_group_binding_sha256': spec['original_group_binding_sha256'],
            'review': intent['review'], 'execution': intent['execution'],
            'spec_file_sha256': intent['spec_file_sha256'], 'dispatch_sha256': digest(intent)}
        result = c1_execution.run_body(spec, tasks, memberships, out/'payload', basis,
            store, KEY, claim, volume.commit, start, start+spec['limits']['worker_seconds'],
            intent['budget']['prior_reserved_usd'], loader, load_timer_factory=timer_factory)
        artifact = c1_artifacts.pack(out/'payload')
        volume.commit()
        finished = time.time()
        if finished >= start+spec['limits']['worker_seconds'] or finished >= c1_execution.CUTOFF_EPOCH:
            raise TimeoutError('Original C1 complete packing window exceeded')
        receipt = {'status': 'completed', 'logical_id': LOGICAL, 'app_id': intent['app_id'],
            'claim': claim, 'spec_sha256': digest(spec), 'spec_file_sha256': sha(spec_file),
            'worker_start_epoch': start, 'finished_epoch': finished, 'result': result,
            'artifact': artifact, 'basis': basis, 'actual_A3_accepted': False}
        dump(out/'TERMINAL.json', receipt)
        volume.commit()
        if not store.put(KEY+'/terminal', receipt, skip_if_exists=True):
            raise ValueError('Original terminal already exists')
        return receipt
    except BaseException as exc:
        if claimed:
            failure = {'status': 'failed', 'type': type(exc).__name__, 'message': str(exc),
                'traceback': traceback.format_exc(), 'app_id': intent['app_id'],
                'finished_epoch': time.time(), 'automatic_retry_allowed': False}
            dump(out/'FAILURE.json', failure)
            volume.commit()
            store.put(KEY+'/terminal', failure, skip_if_exists=True)
        raise
    finally:
        timer.cancel()


def complete_record_keys(spec):
    return [KEY+'/'+x for x in ('dispatch', 'claim', 'terminal')]+[
        KEY+f'/{prefix}/{i:05d}' for i in range(spec['task_inventory']['journal_chunks'])
        for prefix in ('chunk', 'chunk_done')]


def closed_provider(app_id, info, containers, observed_epoch):
    """Used after original returned completion only; no implicit cloud query."""
    counts = Counter(x.get('app_id') for x in containers)
    if info['app_id'] != app_id or str(info['lifecycle']['state']).lower() != 'stopped' or counts[app_id]:
        raise ValueError('Original C1 app not yet actually STOPPED/owned0')
    return {'app_id': app_id, 'state': 'stopped', 'owned_containers': 0,
        'observed_epoch': observed_epoch}
