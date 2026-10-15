"""One finite parent owns all P0 raw writes; isolated processes never dispatch."""
from pathlib import Path
import math
import multiprocessing
import tempfile
import time
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, verify
from experiments.learning_regime_p009.p0_contract import (
    ROLES, WORKER_SECONDS, RESERVED_CENTS, prompts_checked, raw_checked, remaining_forecast)


def receive(connection, process, stop):
    while time.time() < stop-30:
        if connection.poll(min(1., max(.001, stop-30-time.time()))):
            kind, payload = connection.recv()
            if kind == 'error':
                raise RuntimeError(payload)
            return kind, payload
        if not process.is_alive():
            raise RuntimeError('Engine exited without its response; never repeat generation')
    raise TimeoutError('P0 whole-worker deadline')


def isolated(mode, paths):
    from experiments.learning_regime_p009.p0_engine import child
    context = multiprocessing.get_context('spawn')
    parent, remote = context.Pipe()
    process = context.Process(target=child, args=(remote, mode, paths), daemon=False)
    process.start(); remote.close()
    return parent, process


def close_process(connection, process, stop, *, graceful=False):
    if graceful and process.is_alive():
        connection.send(('close', None))
    process.join(timeout=max(0., min(15., stop-30-time.time())))
    if process.is_alive():
        process.terminate(); process.join(timeout=5)
    if process.is_alive():
        process.kill(); process.join(timeout=5)
    connection.close()
    if graceful and process.exitcode != 0:
        raise RuntimeError('Engine shutdown failed; keep original outputs')


def execute(spec, out, store, guard, admitted, commit, start, stop):
    out = Path(out)
    inputs = Path(spec['remote_inputs'])
    verify(inputs, spec['inputs'])
    rows = prompts_checked(read(inputs/'qwen_gsm_zero_parity.json'))
    base = Path(spec['remote_base_model'])
    verify(base, spec['base_files'])
    checkpoint = Path(spec['remote_reference_checkpoint'])
    verify(checkpoint, spec['checkpoint_files'])
    total_batches = len(ROLES)*math.ceil(len(rows)/32)
    completed = 0; durations = []; forecasts = []; setup = []
    tmp = Path(tempfile.mkdtemp(prefix='p009-parity-'))
    key = guard.prefix+admitted.run_id

    def check():
        if time.time() >= stop-30:
            raise TimeoutError('P0 whole-worker soft deadline')
        guard.check_active(admitted, now_epoch=time.time(), spent_cents=RESERVED_CENTS)

    def once(record_key, value):
        if not store.put(record_key, value, skip_if_exists=True):
            raise ValueError('Existing or ambiguous unit; no repeat')

    for role in ROLES:
        setup_start = time.time()
        check(); model = base
        if role == 'correct_969':
            connection, process = isolated('merge', dict(base=str(base), checkpoint=str(checkpoint),
                destination=str(tmp/'merged_969'), proof=str(out/'MERGE_PROOF.json')))
            try:
                kind, info = receive(connection, process, stop)
                if kind != 'merged':
                    raise ValueError('Reference merge did not complete')
            finally:
                close_process(connection, process, stop)
            if process.exitcode != 0:
                raise RuntimeError('Reference merge subprocess failed')
            commit(); model = tmp/'merged_969'
        connection, process = isolated('evaluate', dict(model=str(model), tokenizer=str(base)))
        try:
            kind, info = receive(connection, process, stop)
            if kind != 'ready':
                raise ValueError('Engine not ready')
            dump(out/role/'environment.json', info); commit()
            setup.append(dict(role=role, seconds=time.time()-setup_start))
            role_batches = 0
            for offset in range(0, len(rows), 32):
                batch_start = time.time()
                check()
                if role_batches >= 4:
                    forecast = remaining_forecast(time.time()-start, durations,
                                                  total_batches-completed)
                    forecasts.append(forecast)
                    dump(out/'forecasts'/f'{completed:03d}.json', forecast); commit()
                    if not forecast['admitted']:
                        raise TimeoutError('Measured full-batch forecast exceeds reviewed cap/budget')
                part = rows[offset:offset+32]; name = f'{role}_{offset:04d}'
                intent = dict(role=role, offset=offset, problem_ids=[r['problem_id'] for r in part],
                              prompt_sha256=digest(part), started_epoch=batch_start,
                              preceding_full_batch_seconds=list(durations))
                once(key+'/unit/'+name, intent)
                dump(out/'intents'/f'{name}.json', intent); commit()
                connection.send(('generate', part))
                kind, raw = receive(connection, process, stop)
                if kind != 'outputs':
                    raise ValueError('Unexpected engine reply')
                # Save unmodified returned bytes before interpretation. Invalid
                # or incomplete responses stay attributable and never repeat.
                rawpath = out/role/'raw'/f'{offset:04d}.json'
                dump(rawpath, raw); commit()
                raw_checked(part, raw)
                ack = dict(count=len(part), raw_sha256=sha(rawpath),
                           problem_ids=intent['problem_ids'], finished_epoch=time.time())
                dump(out/'completed'/f'{name}.json', ack); commit()
                once(key+'/done/'+name, ack)
                dump(out/'timings'/f'{name}.json', dict(
                    through_done_ack_seconds=time.time()-batch_start,
                    note='Final metadata-write/commit is included in the next intent and final full-batch vector'))
                commit()
                durations.append(time.time()-batch_start)
                completed += 1; role_batches += 1
                print(f'P0 {role}: saved {offset+len(part)}/1319', flush=True)
            dump(out/role/'GENERATION_COMPLETE.json', dict(outputs=1319, batches=role_batches,
                new_training_updates=0, score_not_computed_on_gpu=True)); commit()
        finally:
            close_process(connection, process, stop, graceful=True)
    check()
    result = dict(roles=list(ROLES), outputs=2638, new_training_updates=0,
        full_batch_intervals_seconds=durations, forecasts=forecasts,
        setup_observations=setup,
        time_interval_definition='before guard/forecast through generation, all durable journals and timing-metadata commit',
        worker_seconds_before_pack=time.time()-start, scoring='independent CPU required',
        source_revision=spec['base_revision'], parity_decision='not yet scored')
    return result
