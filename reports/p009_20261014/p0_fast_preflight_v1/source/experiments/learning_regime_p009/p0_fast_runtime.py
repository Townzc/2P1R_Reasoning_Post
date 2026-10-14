"""One fresh full P0 under Plan A, with one paid first-batch measurement."""
from pathlib import Path
import multiprocessing
import tempfile
import time
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, verify
from experiments.learning_regime_p009.p0_runtime import receive, close_process
from experiments.learning_regime_p009.p0_fast_contract import (
    ROLES, BATCH_SIZE, RESERVED_CENTS, prompts_checked, raw_checked,
    remaining_forecast, fence_original,
)


def isolated(mode, paths):
    from experiments.learning_regime_p009.p0_fast_engine import child
    context = multiprocessing.get_context('spawn')
    parent, remote = context.Pipe()
    process = context.Process(target=child, args=(remote, mode, paths), daemon=False)
    process.start(); remote.close()
    return parent, process


def execute(spec, out, store, guard, admitted, commit, start, stop):
    out = Path(out)
    marker = fence_original(store, spec, admitted)
    dump(out/'FRESH_CONFIGURATION_MARKER.json', marker); commit()
    inputs = Path(spec['remote_inputs']); verify(inputs, spec['inputs'])
    rows = prompts_checked(read(inputs/'qwen_gsm_zero_parity.json'))
    base = Path(spec['remote_base_model']); verify(base, spec['base_files'])
    checkpoint = Path(spec['remote_reference_checkpoint']); verify(checkpoint, spec['checkpoint_files'])
    total_batches = 12
    completed = 0; durations = []; forecasts = []; setup = []
    tmp = Path(tempfile.mkdtemp(prefix='p009-fast-parity-'))
    key = guard.prefix+admitted.run_id

    def check():
        if time.time() >= stop-30:
            raise TimeoutError('P0 fast whole-worker soft deadline')
        guard.check_active(admitted, now_epoch=time.time(), spent_cents=RESERVED_CENTS)

    def once(record_key, value):
        if not store.put(record_key, value, skip_if_exists=True):
            raise ValueError('Existing or ambiguous batch; no repeat')

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
            setup.append(dict(role=role, seconds=time.time()-setup_start,
                              includes_graph_compilation=True))
            role_batches = 0
            for offset in range(0, len(rows), BATCH_SIZE):
                batch_start = time.time(); check()
                # Only the very first base batch is a measurement exception.
                # The first correct-969 batch is also gated by all observations.
                if completed:
                    forecast = remaining_forecast(time.time()-start, durations,
                                                  total_batches-completed)
                    forecasts.append(forecast)
                    dump(out/'forecasts'/f'{completed:03d}.json', forecast); commit()
                    if not forecast['admitted']:
                        raise TimeoutError('New full-batch forecast exceeds reviewed cap/budget')
                part = rows[offset:offset+BATCH_SIZE]; name = f'{role}_{offset:04d}'
                intent = dict(role=role, offset=offset, problem_ids=[r['problem_id'] for r in part],
                    prompt_sha256=digest(part), started_epoch=batch_start,
                    preceding_full_batch_seconds=list(durations),
                    first_measurement_exception=(completed == 0), inherited_outputs=0)
                once(key+'/unit/'+name, intent)
                dump(out/'intents'/f'{name}.json', intent); commit()
                connection.send(('generate', part))
                kind, raw = receive(connection, process, stop)
                if kind != 'outputs':
                    raise ValueError('Unexpected engine reply')
                rawpath = out/role/'raw'/f'{offset:04d}.json'
                dump(rawpath, raw); commit()
                raw_checked(part, raw)
                ack = dict(count=len(part), raw_sha256=sha(rawpath),
                    problem_ids=intent['problem_ids'], finished_epoch=time.time())
                dump(out/'completed'/f'{name}.json', ack); commit()
                once(key+'/done/'+name, ack)
                dump(out/'timings'/f'{name}.json', dict(
                    through_done_ack_seconds=time.time()-batch_start,
                    note='Final timing write/commit included in subsequent intent and final duration vector'))
                commit(); durations.append(time.time()-batch_start)
                completed += 1; role_batches += 1
                print(f'P0-fast {role}: saved {offset+len(part)}/1319', flush=True)
            dump(out/role/'GENERATION_COMPLETE.json', dict(outputs=1319, batches=role_batches,
                new_training_updates=0, inherited_outputs=0, score_not_computed_on_gpu=True)); commit()
        finally:
            close_process(connection, process, stop, graceful=True)
    check()
    return dict(roles=list(ROLES), outputs=2638, inherited_outputs=0, new_training_updates=0,
        full_batch_intervals_seconds=durations, forecasts=forecasts, batches=completed,
        setup_observations=setup, old_eager_timings_used=False,
        time_interval_definition='before guard/forecast through generation, durable journals and metadata commit',
        worker_seconds_before_pack=time.time()-start, scoring='independent CPU required',
        source_revision=spec['base_revision'], parity_decision='not yet scored')
