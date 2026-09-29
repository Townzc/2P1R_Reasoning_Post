"""Optional two-GPU scheduling of the unchanged, frozen evaluation jobs.

Prepare only until the owner changes hardware. One inherited phase lock excludes
the original evaluator; each child sees one CUDA device and owns complete runs.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from .preflight import json_hash, sha, write_json
from .runtime_common import ensure_record, read
from .source_guard import verify_inventory

FROZEN_SOURCE = 'c833d732a7e5b7ecf7589a41ea30f2fb7068a6d9'
FROZEN_INVENTORY = '59edaf26177686556c3a31df9f135276f215fdb76479d4299e0f9e2cfdca1ecc'
COUNTS = {'gsm8k': 1319, 'math500': 500, 'dev': 512}


def partition_jobs(jobs):
    if len(jobs) != 53 or len({j['name'] for j in jobs}) != 53:
        raise ValueError('Expected the complete frozen53-run roster')
    return [jobs[rank::2] for rank in range(2)]


@contextmanager
def phase_lock(output):
    """The same lock as the original single-GPU evaluator; inherited by children."""
    with (Path(output) / 'GPU.lock').open('a+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield stream


def verify_original_sources(frozen_source):
    root = Path(frozen_source)
    verify_inventory(root / 'SOURCE_INVENTORY.json',
        root / 'experiments/public_math_pilot_v1/preflight_inputs.json',
        expected_source_commit=FROZEN_SOURCE,
        expected_inventory_sha256=FROZEN_INVENTORY, repo_root=root)
    inventory = read(root / 'SOURCE_INVENTORY.json')
    current = Path(__file__).resolve().parents[2]
    for name, expected in inventory['source_files_sha256'].items():
        if sha(current / name) != expected:
            raise ValueError('Original model/evaluation code changed: ' + name)


def select_devices(rows, selectors):
    """Resolve two distinct full GPUs, recording UUIDs instead of index aliases."""
    if len(selectors) != 2 or len(set(selectors)) != 2:
        raise ValueError('Exactly two distinct GPU selectors required')
    selected = []
    for selector in selectors:
        matches = [r for r in rows if selector in (r['index'], r['uuid'])]
        if len(matches) != 1:
            raise ValueError('GPU selector is absent or ambiguous')
        item = matches[0]
        if 'A800' not in item['name'] or item['memory_mib'] < 80000:
            raise ValueError('This scheduling amendment requires two A80080GB GPUs')
        selected.append(item)
    if selected[0]['uuid'] == selected[1]['uuid']:
        raise ValueError('GPU aliases resolve to the same physical device')
    return selected


def discover_devices(selectors):
    raw = subprocess.check_output(['nvidia-smi',
        '--query-gpu=index,uuid,name,memory.total', '--format=csv,noheader,nounits'],
        text=True, timeout=20)
    rows = []
    for line in raw.splitlines():
        index, device_uuid, name, memory = [v.strip() for v in line.split(',')]
        rows.append(dict(index=index, uuid=device_uuid, name=name, memory_mib=int(memory)))
    return select_devices(rows, selectors)


def child_environment(device_uuid):
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES=device_uuid, PYTHONUNBUFFERED='1',
        TOKENIZERS_PARALLELISM='false',
        PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
    return env


def expected_evaluation_contract(base_identity, training_contract, rows, jobs, evidence_sha):
    return dict(schema=1, jobs=jobs, base_identity=base_identity,
        training_contract_sha256=json_hash(training_contract),
        model_identities_bound_per_run_before_generation=True,
        concurrency='one separately locked trainer and one generator; immutable checkpoints only',
        prompt_sha256={name: [json_hash(r['prompt_ids']) for r in rr] for name, rr in rows.items()},
        public_generations=26595, dev_generations_including_base=4608, total_generations=31203,
        checkpoint_selection='step128 fixed before results; step64 diagnostic only',
        infrastructure_retry_evidence_sha256=evidence_sha, source_commit=FROZEN_SOURCE,
        implementation_sha256={n: sha(Path(__file__).with_name(n)) for n in
            ('runtime_evaluate.py', 'runtime_common.py', 'preflight.py', 'tokenization.py')})


def checked_context(args):
    from .data import load_inputs
    from .infrastructure_retry import GsmOomRetryLedger
    from .runtime_evaluate import evaluation_jobs
    from .runtime_prepare import prepare_identity
    from .tokenization import encode_prompt
    verify_original_sources(args.frozen_source)
    out = Path(args.output)
    tokenizer, identity, _ = prepare_identity(args.base, args.release, args.inputs)
    contract = read(out / 'TRAIN_CONTRACT.json')
    training_done = read(out / 'TRAINING_COMPLETE.json')
    if (contract['scientific_identity'] != identity or training_done['formal_updates'] != 512
            or training_done['contract_sha256'] != json_hash(contract)):
        raise ValueError('Complete frozen training is required before two-GPU evaluation')
    released = load_inputs(args.release)
    rows = {name: [dict(id=r['problem_id'], prompt_ids=encode_prompt(tokenizer, r['question']))
        for r in released[name]] for name in COUNTS}
    if {k: len(v) for k, v in rows.items()} != COUNTS:
        raise ValueError('Benchmark denominators differ')
    ledger = GsmOomRetryLedger(args.ledger, args.retry_evidence, rows['gsm8k'][:128], identity)
    jobs = evaluation_jobs()
    expected = expected_evaluation_contract(identity, contract, rows, jobs, ledger.evidence_sha256)
    # Preserve the original scientific contract verbatim; changed scheduling is
    # separately declared below with the actual new execution source commit.
    if read(out / 'EVALUATION_CONTRACT.json') != expected:
        raise ValueError('Frozen evaluation contract differs; refuse reinterpretation')
    return tokenizer, identity, contract, training_done, rows, ledger, jobs


def parallel_contract(args, jobs):
    return dict(schema=1, scheduling='two independent processes, one visible CUDA device each',
        source_commit=args.source_commit, implementation_sha256=sha(__file__),
        original_evaluation_contract_sha256=sha(Path(args.output) / 'EVALUATION_CONTRACT.json'),
        original_evaluation_source=FROZEN_SOURCE,
        partitions=[[j['name'] for j in shard] for shard in partition_jobs(jobs)],
        partition_output_counts=[sum(COUNTS[j['dataset']] for j in shard) for shard in partition_jobs(jobs)],
        all_seeded_draws_stay_whole=True, batch_size_and_decoding_unchanged=True,
        old_gpu_lock_held_by_coordinator_and_inherited_by_children=True,
        stop_request='EVALUATION_PAUSE_AFTER_RUN.json; checked before each complete run')


def worker(args):
    import torch
    from .preflight import drop_model, load_base
    from .runtime_common import generate_rows, require_time
    from .runtime_evaluate import model_identity, wait_endpoint, wait_generation_memory
    from .runtime_train import store_for
    rank = args.worker_rank
    attempt = Path(args.attempt_dir)
    start = read(attempt / 'START.json')
    out = Path(args.output)
    inherited = os.fstat(args.owner_lock_fd)
    expected = (out / 'GPU.lock').stat()
    if (inherited.st_ino, inherited.st_dev) != (expected.st_ino, expected.st_dev):
        raise ValueError('Coordinator phase lock was not inherited')
    if (rank not in (0, 1) or start['source_commit'] != args.source_commit
            or os.environ.get('CUDA_VISIBLE_DEVICES') != start['devices'][rank]['uuid']
            or os.environ.get('PYTORCH_CUDA_ALLOC_CONF') != 'expandable_segments:True'
            or torch.cuda.device_count() != 1):
        raise ValueError('Worker device isolation differs')
    with (out / f'DUAL_GPU_WORKER_{rank}.lock').open('a+') as worker_lock:
        fcntl.flock(worker_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        torch.set_num_threads(8)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        tokenizer, identity, contract, _, rows, ledger, jobs = checked_context(args)
        if read(out / 'DUAL_GPU_CONTRACT.json') != parallel_contract(args, jobs):
            raise ValueError('Parallel scheduling contract differs')
        done = []
        for job in partition_jobs(jobs)[rank]:
            if (out / 'EVALUATION_PAUSE_AFTER_RUN.json').exists():
                break
            name = job['name']; folder = out / 'generation' / name
            manifest = wait_endpoint(out, args.volume_root, contract, job['arm'], job['step'], args.deadline_unix)
            model_id = model_identity(identity, manifest, job['arm'], job['step'], json_hash(contract))
            complete = (folder / 'COMPLETE.json').exists()
            model = None
            if not complete:
                require_time(args.deadline_unix, 300)
                wait_generation_memory(job['dataset'], args.deadline_unix)
                model = load_base(args.base, training=False)
                if job['arm'] != 'Base':
                    store = store_for(out, args.volume_root, contract, job['arm'])
                    state = torch.load(store._verify_file(manifest['files']['model']),
                        map_location='cpu', weights_only=True)
                    model.load_state_dict(state, strict=True); del state; gc.collect()
                print(json.dumps(dict(event='evaluation_state_loaded', rank=rank, name=name, model=model_id)), flush=True)
            try:
                generate_rows(model, tokenizer, rows[job['dataset']], folder,
                    model_identity=model_id, logical_name=name, ledger=ledger,
                    deadline=args.deadline_unix, batch_size=job['batch_size'], seed=job['seed'],
                    allow_new_calls=not complete)
            finally:
                if model is not None:
                    drop_model(model); del model; gc.collect(); torch.cuda.empty_cache()
            done.append(dict(name=name, completion_sha256=sha(folder / 'COMPLETE.json')))
            print(json.dumps(dict(event='evaluation_run_complete', rank=rank, name=name)), flush=True)
        value = dict(rank=rank, source_commit=args.source_commit, runs=done,
            status='complete' if len(done) == len(partition_jobs(jobs)[rank]) else 'paused')
        write_json(attempt / f'WORKER_{rank}_RESULT.json', value)
        return value


def finalize(args, attempt, jobs, training_contract, training_done):
    """Close only after both workers independently verified their entire roster."""
    from .losses import ARMS
    from .runtime_train import store_for
    out = Path(args.output)
    results = [read(attempt / f'WORKER_{rank}_RESULT.json') for rank in range(2)]
    for rank, result in enumerate(results):
        if (result['rank'] != rank or result['source_commit'] != args.source_commit
                or result['status'] != 'complete'
                or [v['name'] for v in result['runs']] != [j['name'] for j in partition_jobs(jobs)[rank]]):
            raise ValueError('Workers did not complete their exact disjoint partitions')
        for row in result['runs']:
            if sha(out / 'generation' / row['name'] / 'COMPLETE.json') != row['completion_sha256']:
                raise ValueError('Worker completion changed after verification')
    summaries = {row['name']: row for result in results for row in result['runs']}
    value = dict(contract_sha256=sha(out / 'EVALUATION_CONTRACT.json'),
        runs=[summaries[j['name']] for j in jobs],
        base_dev_sha256=sha(out / 'generation' / 'Base-dev' / 'COMPLETE.json'),
        total_generations=31203, scoring_not_implied=True)
    ensure_record(out / 'EVALUATION_COMPLETE.json', value)
    for arm in ARMS:
        store = store_for(out, args.volume_root, training_contract, arm)
        store.prune_scientific_temp(training_done['endpoints'][arm]['64'], evaluation_complete=True)
    return value


def worker_command(args, rank, attempt, owner_lock_fd):
    remaining = int(args.hard_deadline_unix - time.time())
    if remaining < 600:
        raise TimeoutError('Insufficient two-GPU launch reserve')
    command = ['timeout', '--signal=TERM', '--kill-after=20', str(remaining),
        sys.executable, '-B', '-m', 'experiments.public_math_pilot_v1.parallel_evaluate']
    for key in ('base', 'release', 'inputs', 'output', 'ledger', 'source_commit',
            'frozen_source', 'retry_evidence', 'inventory_sha256', 'deadline_unix', 'hard_deadline_unix'):
        command.extend(['--' + key.replace('_', '-'), str(getattr(args, key))])
    for volume in args.volume_root:
        command.extend(['--volume-root', volume])
    command.extend(['--worker-rank', str(rank), '--attempt-dir', str(attempt),
        '--owner-lock-fd', str(owner_lock_fd)])
    return command


def coordinator(args):
    if args.hard_deadline_unix < args.deadline_unix + 600:
        raise ValueError('Preserve the600-second hard-timeout completion reserve')
    if time.time() + 900 >= args.deadline_unix:
        raise TimeoutError('Insufficient new-coordinator launch reserve')
    out = Path(args.output)
    with phase_lock(out) as lock:
        devices = discover_devices(args.devices.split(','))
        _, _, contract, training_done, _, _, jobs = checked_context(args)
        ensure_record(out / 'DUAL_GPU_CONTRACT.json', parallel_contract(args, jobs))
        attempt = out / 'parallel_evaluation' / ('attempt_' + uuid.uuid4().hex)
        attempt.mkdir(parents=True)
        start = dict(source_commit=args.source_commit, devices=devices,
            started_at_utc=datetime.now(timezone.utc).isoformat(), started_unix=time.time(),
            deadline_unix=args.deadline_unix, hard_deadline_unix=args.hard_deadline_unix,
            coordinator_pid=os.getpid(), contract_sha256=sha(out / 'DUAL_GPU_CONTRACT.json'))
        write_json(attempt / 'START.json', start)
        processes = []
        launch_error = None
        try:
            for rank, device in enumerate(devices):
                with (attempt / f'worker_{rank}.log').open('x') as log:
                    began = time.time()
                    process = subprocess.Popen(worker_command(args, rank, attempt, lock.fileno()),
                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                        env=child_environment(device['uuid']), pass_fds=(lock.fileno(),),
                        start_new_session=True)
                processes.append((rank, process, began))
                write_json(attempt / f'WORKER_{rank}_START.json',
                    dict(rank=rank, pid=process.pid, started_unix=began, device=device))
        except Exception as error:
            # Never kill an already generating sibling because another launch
            # failed. Its independent hard timeout remains in force.
            launch_error = repr(error)
        receipts = []
        pending = list(processes)
        while pending:
            for rank, process, began in list(pending):
                status = process.poll()
                if status is None:
                    continue
                finished = time.time()
                receipt = dict(rank=rank, exit_code=status, start_unix=began,
                    exit_observed_unix=finished, observed_process_seconds=finished - began,
                    observation_poll_interval_seconds=0.5, source_commit=args.source_commit,
                    process_seconds_are_not_billed_instance_hours=True)
                write_json(attempt / f'WORKER_{rank}_RECEIPT.json', receipt)
                receipts.append(receipt)
                pending.remove((rank, process, began))
            if pending:
                time.sleep(0.5)
        complete = (launch_error is None and len(receipts) == 2
            and all(r['exit_code'] == 0 for r in receipts)
            and all(read(attempt / f'WORKER_{r}_RESULT.json')['status'] == 'complete' for r in range(2)))
        if complete:
            finalize(args, attempt, jobs, contract, training_done)
        value = dict(status='generation_complete' if complete else 'incomplete',
            source_commit=args.source_commit, started_unix=start['started_unix'],
            ended_unix=time.time(), launch_error=launch_error, worker_receipts=receipts,
            optional_scientific_runs_added=0)
        write_json(attempt / 'COORDINATOR_RECEIPT.json', value)
        return value


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('base', 'release', 'inputs', 'output', 'ledger', 'source-commit',
            'frozen-source', 'retry-evidence', 'inventory-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--volume-root', action='append', required=True)
    parser.add_argument('--deadline-unix', type=float, required=True)
    parser.add_argument('--hard-deadline-unix', type=float, required=True)
    parser.add_argument('--devices', default='0,1')
    parser.add_argument('--worker-rank', type=int, choices=(0, 1))
    parser.add_argument('--attempt-dir')
    parser.add_argument('--owner-lock-fd', type=int)
    args = parser.parse_args()
    verify_inventory(Path(__file__).resolve().parents[2] / 'SOURCE_INVENTORY.json', args.inputs,
        expected_source_commit=args.source_commit, expected_inventory_sha256=args.inventory_sha256)
    value = coordinator(args) if args.worker_rank is None else worker(args)
    print(json.dumps(value, sort_keys=True), flush=True)
    return 0 if value['status'] in ('complete', 'generation_complete', 'paused') else 1


if __name__ == '__main__':
    raise SystemExit(main())
