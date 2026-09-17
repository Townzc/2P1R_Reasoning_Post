"""Finite paired goal training; independent budgets preserve all completed ledgers."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import importlib.metadata
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from experiments.thursday_probe.common import stamp
from experiments.thursday_probe_v2.training import atomic_json
from experiments.thursday_probe_v2.resume_launcher import _run_worker, _immutable_json
from src.sft_data import sha256_file


RUN_ID = 'post_e037_goal_training_v1'
OUT = Path('runs') / RUN_ID
PLANNED_GENERATIONS = 3344
GENERATION_CAP = 3600
FORWARD_CONTEXTS = 288
CANDIDATE_SCORES = 1152
MAX_POWERED_SECONDS = 10800
MAX_RENTAL_CNY = 30.0
EXPORT_RESERVE_SECONDS = 600
PROCESS_SLICE_SECONDS = 3600
GUARD_SECONDS = 15
MIN_USEFUL_SECONDS = 60
LOAD_ALLOWANCE_SECONDS = 120
MINIMUM_DISK_GIB = 1.0
HISTORICAL_PHASE_SHA256 = '661a25943c3747996a11aefe937c0430f3508ec3895834a495639203c0f26a5e'


def _read(path):
    return json.loads(Path(path).read_text())


def epoch(value):
    timestamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        raise ValueError('Explicit timezone required for rental events')
    return timestamp.timestamp()


class GenerationBudget:
    """New phase starts at zero; reservation retries never erase physical cost."""
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.exists():
            atomic_json(self.path, dict(phase=RUN_ID, cap=GENERATION_CAP, used=0,
                planned=PLANNED_GENERATIONS, events=[],
                historical_generation_attempts=4784, historical_generation_cap=4864,
                historical_goal_generation_attempts=2112, historical_goal_generation_cap=2304,
                historical_phase_ledger_sha256=HISTORICAL_PHASE_SHA256,
                accounting='Separate training phase; old4784/4864 and goal2112/2304 remain unchanged. '
                           'Teacher-forced candidate scores consume time but no autoregressive reservations.'))
        self.record()

    def record(self):
        record = _read(self.path)
        if (record['phase'] != RUN_ID or record['cap'] != GENERATION_CAP or
                record['planned'] != PLANNED_GENERATIONS or
                record['historical_generation_attempts'] != 4784 or record['historical_generation_cap'] != 4864 or
                record['historical_goal_generation_attempts'] != 2112 or record['historical_goal_generation_cap'] != 2304 or
                record['historical_phase_ledger_sha256'] != HISTORICAL_PHASE_SHA256):
            raise ValueError('Generation phase/history limits changed')
        events = record['events']
        if (any(type(e['reserved']) is not int or e['reserved'] <= 0 for e in events) or
                len({e['name'] for e in events}) != len(events) or
                type(record['used']) is not int or record['used'] != sum(e['reserved'] for e in events) or
                not 0 <= record['used'] <= GENERATION_CAP):
            raise ValueError('Generation ledger inconsistent')
        return record

    @property
    def used(self):
        return self.record()['used']

    def reserve(self, name, n):
        record = self.record()
        if not isinstance(name, str) or not name or type(n) is not int or n <= 0 or record['used'] + n > GENERATION_CAP:
            raise ValueError('Invalid request or new-phase generation cap exceeded')
        if name in {event['name'] for event in record['events']}:
            raise ValueError('Duplicate reservation; reconcile ambiguous physical work instead of regenerating')
        record['events'].append(dict(name=name, reserved=n, at_utc=stamp()))
        record['used'] += n
        atomic_json(self.path, record)


class RentalBudget:
    """Three powered-on hours/CNY30 cumulatively, including setup, idle and export."""
    def __init__(self, path, power_on_at_utc, rate):
        self.path = Path(path)
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError('Current verified positive rental rate required')
        start = epoch(power_on_at_utc)
        if start > time.time():
            raise ValueError('Power-on event is in the future')
        if self.path.exists():
            record = self.record()
            active = [w for w in record['windows'] if w['shutdown_confirmed_at_utc'] is None]
            if active:
                if len(active) != 1 or epoch(active[0]['power_on_at_utc']) != start or active[0]['rate_cny_per_hour'] != rate:
                    raise ValueError('Existing active power window and price must be preserved')
                return
            if record['windows'] and start < epoch(record['windows'][-1]['shutdown_confirmed_at_utc']):
                raise ValueError('Power windows cannot overlap')
        else:
            record = dict(phase=RUN_ID, maximum_powered_seconds=MAX_POWERED_SECONDS,
                maximum_rental_cny=MAX_RENTAL_CNY, export_shutdown_reserve_seconds=EXPORT_RESERVE_SECONDS,
                historical_phase_ledger_sha256=HISTORICAL_PHASE_SHA256,
                prior_all_phases_receipts=26, prior_all_phases_charged_process_seconds=14605,
                overall_shared_monetary_ceiling_cny=3000,
                historical_actual_spend_and_remaining_ceiling_unknown=True,
                authority='Owner requested the finite two-arm Post-E037 training plan; '
                          'three powered-on hours/CNY30 within existing CNY3000 ceiling, no recharge or extra instance.',
                windows=[])
        record['windows'].append(dict(power_on_at_utc=power_on_at_utc,
            rate_cny_per_hour=rate, shutdown_confirmed_at_utc=None))
        atomic_json(self.path, record)
        self.record()

    def record(self):
        record = _read(self.path)
        if (record['phase'] != RUN_ID or record['maximum_powered_seconds'] != MAX_POWERED_SECONDS or
                record['maximum_rental_cny'] != MAX_RENTAL_CNY or
                record['export_shutdown_reserve_seconds'] != EXPORT_RESERVE_SECONDS or
                record['historical_phase_ledger_sha256'] != HISTORICAL_PHASE_SHA256 or
                record['prior_all_phases_receipts'] != 26 or record['prior_all_phases_charged_process_seconds'] != 14605):
            raise ValueError('Rental caps/history cannot be reset or enlarged')
        previous_end = None
        for index, window in enumerate(record['windows']):
            start = epoch(window['power_on_at_utc']); end = window['shutdown_confirmed_at_utc']
            if not math.isfinite(window['rate_cny_per_hour']) or window['rate_cny_per_hour'] <= 0:
                raise ValueError('Invalid stored rate')
            if previous_end is not None and start < previous_end:
                raise ValueError('Stored power windows overlap')
            if end is None:
                if index != len(record['windows']) - 1:
                    raise ValueError('Only the latest power window can be active')
            else:
                previous_end = epoch(end)
                if previous_end < start:
                    raise ValueError('Shutdown predates power-on')
        return record

    def remaining(self, now=None):
        now = time.time() if now is None else now
        record = self.record(); powered = cost = 0.; active = None
        for window in record['windows']:
            ended = epoch(window['shutdown_confirmed_at_utc']) if window['shutdown_confirmed_at_utc'] else now
            seconds = max(0., ended - epoch(window['power_on_at_utc']))
            powered += seconds; cost += seconds * window['rate_cny_per_hour'] / 3600
            if window['shutdown_confirmed_at_utc'] is None:
                active = window
        if active is None:
            raise ValueError('No active power window')
        remaining = max(0., min(MAX_POWERED_SECONDS - powered,
            (MAX_RENTAL_CNY - cost) * 3600 / active['rate_cny_per_hour']))
        return dict(powered_seconds_used=powered, rental_cost_proxy_cny=cost,
            remaining_hard_seconds=remaining, hard_deadline_epoch=now + remaining,
            worker_deadline_epoch=now + remaining - EXPORT_RESERVE_SECONDS,
            estimate_is_invoice=False)

    def close(self, confirmed_utc):
        record = self.record()
        active = [w for w in record['windows'] if w['shutdown_confirmed_at_utc'] is None]
        if len(active) != 1 or epoch(confirmed_utc) < epoch(active[0]['power_on_at_utc']):
            raise ValueError('A factual provider-confirmed close time is required')
        active[0]['shutdown_confirmed_at_utc'] = confirmed_utc
        atomic_json(self.path, record)


def source(expected_published_commit):
    """The operator supplies the published full SHA; all executable bytes bind it."""
    if (not isinstance(expected_published_commit, str) or len(expected_published_commit) != 40 or
            any(c not in '0123456789abcdef' for c in expected_published_commit)):
        raise ValueError('Expected published full commit SHA is required')
    head = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
    if head != expected_published_commit:
        raise ValueError('Checkout differs from expected published source')
    roots = ('src','analyses','scripts','experiments/thursday_probe',
             'experiments/thursday_probe_v2','experiments/post_e036_goal_probe','experiments/post_e037_goal_training')
    files = sorted(str(p) for folder in roots for p in Path(folder).glob('*.py'))
    subprocess.check_call(['git','ls-files','--error-unmatch','--',*files], stdout=subprocess.DEVNULL)
    subprocess.check_call(['git','diff','--quiet','HEAD','--',*files])
    return dict(source_commit=head, source_files_sha256={p:sha256_file(p) for p in files})


def load_inputs():
    from experiments.post_e037_goal_training.queue import dry_run
    plan = dry_run()
    if plan.get('planned_generations') != PLANNED_GENERATIONS or plan.get('generation_cap') != GENERATION_CAP:
        raise ValueError('Prepared finite goal-probe plan differs')
    return plan


def server_preflight(configuration, snapshot):
    from scripts.run_relation_engineering import server_preflight as check
    return check(configuration, snapshot)


def historical_binding(path):
    if sha256_file(path) != HISTORICAL_PHASE_SHA256:
        raise ValueError('Completed historical phase bytes changed; never reset/rewrite them')
    old = _read(path)
    if (old['closed'] is not True or old['provider_shutdown_confirmed'] is not True or
            old['new_generation_attempts'] != 2112 or old['total_receipts_across_phases'] != 26 or
            old['total_charged_seconds_across_phases'] != 14605 or old['active_worker']):
        raise ValueError('Prior completed phase is not reconciled')
    return dict(sha256=HISTORICAL_PHASE_SHA256, receipts=26, charged_seconds=14605,
                generation_attempts=2112, generation_cap=2304, older_attempts=4784, older_cap=4864)


def slice_seconds(remaining, now=None):
    now = time.time() if now is None else now
    cap = math.floor(min(PROCESS_SLICE_SECONDS, remaining['worker_deadline_epoch'] - now - GUARD_SECONDS))
    return cap if cap >= MIN_USEFUL_SECONDS + LOAD_ALLOWANCE_SECONDS else None


def _receipts(output):
    receipts = []
    for number, folder in enumerate(sorted((output/'attempts').glob('attempt_*')), 1):
        if folder.name != f'attempt_{number:06d}' or not (folder/'resource_receipt.json').exists():
            raise ValueError('Unreconciled or noncontiguous prior attempt; preserve and inspect it')
        receipt = _read(folder/'resource_receipt.json')
        if (receipt['attempt'] != number or receipt['run_id'] != RUN_ID or
                receipt['charged_seconds'] != math.ceil(receipt['wall_seconds']) or
                not receipt['historical_phase_unchanged'] or
                receipt['historical_phase_sha256'] != HISTORICAL_PHASE_SHA256):
            raise ValueError('Invalid prior receipt')
        receipts.append(receipt)
    return receipts


def _forward_progress(output):
    path = output/'progress.json'
    progress = _read(path) if path.exists() else {}
    contexts = progress.get('forward_contexts', 0); scores = progress.get('candidate_scores', 0)
    if type(contexts) is not int or not 0 <= contexts <= FORWARD_CONTEXTS or type(scores) is not int or not 0 <= scores <= CANDIDATE_SCORES:
        raise ValueError('Forward progress must be separate bounded context/candidate counts')
    operators = progress.get('operators', [])
    return dict(planned_forward_contexts=FORWARD_CONTEXTS, planned_candidate_scores=CANDIDATE_SCORES,
        completed_forward_contexts=contexts, candidate_scores=scores,
        recorded_contexts=sum(o.get('recorded_contexts', 0) for o in operators),
        unavailable_contexts=sum(o.get('unavailable_contexts', 0) for o in operators),
        actual_forward_calls=progress.get('forward_calls', sum(o.get('forward_calls', 0) for o in operators)),
        forward_processed_tokens=progress.get('forward_tokens', sum(o.get('input_tokens', 0) for o in operators)),
        forward_seconds=progress.get('forward_seconds', sum(o.get('seconds', 0.) for o in operators)),
        teacher_forced_scores_are_autoregressive_generations=False,
        reference_forward_calls=progress.get('reference_forward_calls',0),
        reference_forward_tokens=progress.get('reference_forward_tokens',0),
        reference_forward_seconds=progress.get('reference_forward_seconds',0.))


def _validate_completion(output, budget):
    """An exit-zero process must also have the complete frozen request views."""
    progress = _read(output/'progress.json')
    if progress['status'] != 'completed' or not PLANNED_GENERATIONS <= budget.used <= GENERATION_CAP:
        raise ValueError('Completed worker has incomplete status/generation accounting')
    from experiments.post_e037_goal_training.queue import evaluation_queue
    expected = {event['name']:event['expected_records'] for event in evaluation_queue()}
    if progress.get('training_updates') != 512:
        raise ValueError('Both arms must commit 256 updates')
    runs = progress.get('runs', [])
    if len(runs) != 2 or {r['state'] for r in runs} != {'G-single','G-paired'} or any(r['status'] != 'completed' or r['completed_updates'] != 256 for r in runs):
        raise ValueError('Both frozen training endpoints required')
    evaluations = progress['evaluations']
    if (len(evaluations) != len(expected) or {e['name'] for e in evaluations} != set(expected) or
            any(e['status'] != 'completed' or e['completed_records'] != expected[e['name']]
                for e in evaluations)):
        raise ValueError('Completed worker has incomplete or duplicate evaluation views')
    available = 0
    for state in ('E031','G-single','G-paired'):
        aggregate = _read(output/'operator_scores'/(state+'.json'))
        records = aggregate['records']
        if (aggregate['state'] != state or aggregate['status'] != 'completed' or len(records) != 96 or
                any(r['status'] not in ('available','unavailable') for r in records)):
            raise ValueError('Completed worker must account for all operator contexts')
        for index, record in enumerate(records):
            if _read(output/'operator_scores'/state/f'{index:06d}.json') != record:
                raise ValueError('Operator aggregate differs from immutable context result')
            if record['status'] == 'unavailable' and not record.get('reason'):
                raise ValueError('Unavailable operator context requires an explicit reason')
        count = sum(r['status'] == 'available' for r in records)
        if aggregate['forward_contexts'] != count or aggregate['candidate_scores'] != count*4:
            raise ValueError('Operator candidate accounting differs from recorded results')
        available += count
    if progress['forward_contexts'] != available or progress['candidate_scores'] != 4*available:
        raise ValueError('Completed forward totals differ from immutable contexts')


def _work_state(output, budget):
    durable = []
    for path in output.rglob('*.json'):
        candidate = ('operator_scores' in path.relative_to(output).parts and len(path.stem) == 6 and path.stem.isdigit())
        if candidate or path.name.endswith(('.raw.json','.scored.json')) or path.name == 'latest.json' or (path.name.startswith('reference_') and not path.name.endswith('.intent.json')):
            durable.append((str(path.relative_to(output)), sha256_file(path)))
    return budget.used, tuple(sorted(durable))


def _export(output):
    target = output/'export_manifest_final.json'
    files = {str(p.relative_to(output)):dict(sha256=sha256_file(p), bytes=p.stat().st_size)
             for p in sorted(output.rglob('*')) if p.is_file() and p != target and not p.name.startswith('backup_confirmed.') and not p.is_symlink() and not any(q.is_symlink() for q in p.parents if q != output)}
    record = dict(created_at_utc=stamp(), files=files,
        inventory_scope='New training adapters, recovery states, outputs and receipts; shared E031/base references and external mutable backup acknowledgments are excluded.')
    atomic_json(target, record)
    return record


def _phase_summary(output, receipts, status, budget, rental):
    charged = sum(r['charged_seconds'] for r in receipts)
    record = dict(phase=RUN_ID, status=status, receipts=len(receipts), attempt_charged_seconds=charged,
        prior_receipts=26, prior_charged_seconds=14605, total_receipts_across_phases=26+len(receipts),
        total_charged_seconds_across_phases=14605+charged,
        historical_phase_sha256=HISTORICAL_PHASE_SHA256, historical_generation_attempts=4784,
        historical_generation_cap=4864, historical_goal_generation_attempts=2112,
        historical_goal_generation_cap=2304, new_generation_attempts=budget.used, new_generation_cap=GENERATION_CAP,
        planned_new_generations=PLANNED_GENERATIONS, forwards=_forward_progress(output), training_updates=_read(output/'progress.json').get('training_updates',0) if (output/'progress.json').exists() else 0,
        active_worker=False, rental=rental.remaining(), provider_shutdown_confirmed=False,
        shutdown_note='Worker/launcher exit is not provider-confirmed shutdown or stopped billing.')
    atomic_json(output/'phase_ledger.json', record)


def launch(snapshot, endpoint_root, historical_phase_ledger, power_on_at_utc, current_rate,
           expected_published_commit, *, output=OUT):
    provenance = source(expected_published_commit); plan = load_inputs()
    historical = historical_binding(historical_phase_ledger)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    with (output/'launcher.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('A launcher already owns this training phase') from exc
        receipts = _receipts(output)
        for name in ('generation_ledger.json','rental_budget.json','launch_manifest.json'):
            if receipts and not (output/name).exists():
                raise ValueError('Missing persistent phase state; refuse budget reset: '+name)
        launch_manifest = output/'launch_manifest.json'
        identity = dict(**provenance, historical_phase=historical,
            planned_generations=PLANNED_GENERATIONS, generation_cap=GENERATION_CAP,
            planned_forward_contexts=FORWARD_CONTEXTS, planned_candidate_scores=CANDIDATE_SCORES,
            maximum_powered_seconds=MAX_POWERED_SECONDS, maximum_rental_cny=MAX_RENTAL_CNY,
            prepared_plan=plan, planned_training_updates=512)
        if launch_manifest.exists():
            if _read(launch_manifest)['identity'] != identity:
                raise ValueError('Execution source/plan identity changed during resume')
        else:
            _immutable_json(launch_manifest, dict(identity=identity, created_at_utc=stamp()))
        budget = GenerationBudget(output/'generation_ledger.json')
        if receipts and receipts[-1]['status'] == 'completed':
            return 0
        rental = RentalBudget(output/'rental_budget.json', power_on_at_utc, current_rate)
        previous_handler = signal.getsignal(signal.SIGTERM)
        def terminate(*_):
            raise TimeoutError('Launcher termination: stop/reap worker before closeout')
        signal.signal(signal.SIGTERM, terminate)
        try:
            while True:
                remaining = rental.remaining(); cap = slice_seconds(remaining)
                if cap is None:
                    _phase_summary(output, receipts, 'paused_resource', budget, rental); _export(output)
                    return 75
                server = server_preflight({'min_free_gib':MINIMUM_DISK_GIB}, Path(snapshot))
                if importlib.metadata.version('peft') != '0.17.1':
                    raise ValueError('Pinned PEFT0.17.1 required')
                remaining = rental.remaining(); cap = slice_seconds(remaining)
                if cap is None:
                    _phase_summary(output, receipts, 'paused_resource', budget, rental); _export(output)
                    return 75
                attempt = len(receipts)+1; directory = output/'attempts'/f'attempt_{attempt:06d}'
                directory.mkdir(parents=True, exist_ok=False)
                deadline = time.time()+cap
                command = ['timeout','--signal=TERM',f'--kill-after={GUARD_SECONDS}s',f'{cap}s',
                    sys.executable,'-m','experiments.post_e037_goal_training.queue','--worker',
                    '--snapshot',str(snapshot),'--endpoint-root',str(endpoint_root)]
                public_command = command[:4]+['PINNED_RUNTIME']+command[5:9]+[
                    'PINNED_MODEL_SNAPSHOT','--endpoint-root','PRESERVED_E031_PARENT_ROOT']
                intent = dict(attempt=attempt, run_id=RUN_ID, started_at_utc=stamp(),
                    process_cap_seconds=cap, guard_seconds=GUARD_SECONDS, worker_deadline_epoch=deadline,
                    global_worker_deadline_epoch=remaining['worker_deadline_epoch'],
                    historical_phase_sha256=HISTORICAL_PHASE_SHA256,
                    generation_attempts_before=budget.used, forwards_before=_forward_progress(output),
                    command=public_command, **provenance)
                _immutable_json(directory/'intent.json', intent)
                _immutable_json(directory/'preflight.json', dict(server=server,
                    minimum_free_disk_gib=MINIMUM_DISK_GIB, rental=remaining, historical_phase=historical))
                environment = {**os.environ, 'GOAL_TRAINING_BOUNDED':RUN_ID,
                    'GOAL_TRAINING_DEADLINE':str(deadline), 'GOAL_TRAINING_GLOBAL_DEADLINE':str(remaining['worker_deadline_epoch']),
                    'GOAL_TRAINING_PUBLISHED_COMMIT':expected_published_commit, 'GOAL_TRAINING_OUTPUT':str(output),
                    'TOKENIZERS_PARALLELISM':'false','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
                before = _work_state(output,budget); tick = time.monotonic(); failure = None
                with (directory/'stdout.log').open('x') as stream:
                    try:
                        code = _run_worker(command,environment,stream)
                    except BaseException as exc:
                        code = 1; failure = dict(type=type(exc).__name__, message=str(exc))
                    stream.flush(); os.fsync(stream.fileno())
                elapsed = time.monotonic()-tick
                unchanged = sha256_file(historical_phase_ledger) == HISTORICAL_PHASE_SHA256
                effective_code = code if unchanged else 1
                if effective_code == 0:
                    try:
                        _validate_completion(output, budget)
                    except Exception as exc:
                        effective_code = 1; failure = dict(type=type(exc).__name__, message=str(exc))
                status = 'completed' if effective_code == 0 else 'paused_resource' if effective_code == 75 else f'failed:{effective_code}'
                receipt = dict(attempt=attempt, run_id=RUN_ID, status=status, exit_code=effective_code,
                    worker_exit_code=code, wall_seconds=elapsed, charged_seconds=math.ceil(elapsed),
                    process_cap_seconds=cap, guard_seconds=GUARD_SECONDS, started_at_utc=intent['started_at_utc'],
                    finished_at_utc=stamp(), historical_phase_sha256=HISTORICAL_PHASE_SHA256,
                    historical_phase_unchanged=unchanged, generation_attempts_after=budget.used,
                    forwards_after=_forward_progress(output), training_updates=_read(output/'progress.json').get('training_updates',0) if (output/'progress.json').exists() else 0,
                    source_commit=provenance['source_commit'], failure=failure, command=public_command)
                _immutable_json(directory/'resource_receipt.json', receipt); receipts.append(receipt)
                _phase_summary(output, receipts, status, budget, rental); _export(output)
                print(json.dumps(receipt, sort_keys=True), flush=True)
                if effective_code != 75 or _work_state(output,budget) == before:
                    return effective_code
        finally:
            signal.signal(signal.SIGTERM, previous_handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['launch'])
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--endpoint-root', required=True)
    parser.add_argument('--historical-phase-ledger', required=True)
    parser.add_argument('--power-on-at-utc', required=True)
    parser.add_argument('--current-rate', type=float, required=True)
    parser.add_argument('--expected-published-commit', required=True)
    args = parser.parse_args()
    sys.exit(launch(args.snapshot,args.endpoint_root,args.historical_phase_ledger,
        args.power_on_at_utc,args.current_rate,args.expected_published_commit))
