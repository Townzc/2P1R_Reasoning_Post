"""Durable finite P2/P3 batch loop. The future reviewed entry owns the hard timer."""
import math
import multiprocessing
from pathlib import Path
import time

from experiments.sft_allocation_midpoint.common import dump, sha, digest, verify
from experiments.learning_regime_p009.p0_runtime import receive, close_process
from experiments.learning_regime_p009.stage0_generation_contract_v2 import (
    DATASETS, BATCH_SIZE, slot_checked, load_rows, transport_checked, remaining_forecast,
)


def isolated(run_id, paths):
    from experiments.learning_regime_p009.stage0_generation_engine_v2 import child
    ctx = multiprocessing.get_context('spawn')
    parent, remote = ctx.Pipe()
    process = ctx.Process(target=child, args=(remote, run_id, paths), daemon=False)
    process.start(); remote.close()
    return parent, process


def generate_batches(run_id, datasets, out, store, guard, claim, commit, start, stop,
                     connection, process):
    """Called only with a live exact gate/claim by execute; injectable I/O for tests."""
    slot = slot_checked(run_id); out = Path(out)
    if list(datasets) != slot['datasets']:
        raise ValueError('Frozen acquisition/endpoint order changed')
    if any(len(rows) != DATASETS[n]['n'] for n, rows in datasets.items()):
        raise ValueError('Whole frozen rosters required')
    total_batches = sum(math.ceil(len(rows)/BATCH_SIZE) for rows in datasets.values())
    completed = 0; durations = []; forecast_count = 0
    key = guard.prefix+claim.run_id

    def check():
        if time.time() >= stop-30:
            raise TimeoutError('Whole-worker soft deadline; no automatic continuation')
        guard.check_active(claim, now_epoch=time.time(), spent_cents=slot['reserved_cents'])

    def once(k, value):
        if not store.put(k, value, skip_if_exists=True):
            raise ValueError('Existing/ambiguous unit or acknowledgement; never replay')

    for name, rows in datasets.items():
        dataset_batches = 0
        for offset in range(0, len(rows), BATCH_SIZE):
            batch_start = time.time(); check()
            if completed:
                forecast = remaining_forecast(run_id, time.time()-start, durations,
                                              total_batches-completed)
                dump(out/'forecasts'/f'{completed:03d}.json', forecast); commit()
                forecast_count += 1
                if not forecast['admitted']:
                    raise TimeoutError('New full-batch timing/cost gate failed')
            # One first256 request batch per model lifetime is the explicitly
            # proposed, paid measurement exception. Not one per endpoint.
            part = rows[offset:offset+BATCH_SIZE]; unit = f'{name}_{offset:05d}'
            intent = dict(dataset=name, offset=offset, count=len(part),
                candidate_ids=[r['candidate_id'] for r in part], request_sha256=digest(part),
                started_epoch=batch_start, preceding_full_batch_seconds=list(durations),
                first_measurement_exception=(completed == 0), new_training_updates=0)
            once(key+'/unit/'+unit, intent)
            dump(out/'intents'/f'{unit}.json', intent); commit()
            connection.send(('generate', dict(dataset=name, rows=part)))
            kind, raw = receive(connection, process, stop)
            if kind != 'outputs':
                raise ValueError('Unexpected engine response; retain unit and do not repeat')
            path = out/name/'raw'/f'{offset:05d}.json'
            # Preserve even a malformed returned batch before checking it.
            dump(path, raw); commit()
            transport_checked(name, part, raw)
            ack = dict(count=len(part), candidate_ids=intent['candidate_ids'],
                raw_sha256=sha(path), request_sha256=intent['request_sha256'],
                finished_epoch=time.time(), native_stop_metadata_preserved=True)
            dump(out/'completed'/f'{unit}.json', ack); commit()
            once(key+'/done/'+unit, ack)
            dump(out/'timings'/f'{unit}.json', dict(through_done_ack_seconds=time.time()-batch_start,
                final_write_included_in_next_intent_and_final_vector=True))
            commit(); durations.append(time.time()-batch_start)
            completed += 1; dataset_batches += 1
            print(f'P009 {run_id}/{name}: saved {offset+len(part)}/{len(rows)}', flush=True)
        dump(out/name/'GENERATION_COMPLETE.json', dict(outputs=len(rows), batches=dataset_batches,
            full_frozen_roster=True, no_score_on_gpu=True, new_training_updates=0)); commit()
    check()
    return dict(run_id=run_id, datasets=list(datasets),
        dataset_counts={n:len(rows) for n, rows in datasets.items()}, batches=completed,
        new_outputs=sum(len(rows) for rows in datasets.values()), new_training_updates=0,
        first_measurement_exceptions=1, forecasts=forecast_count,
        full_batch_intervals_seconds=durations,
        interval_definition='before guard/forecast through generation and all durable metadata commits',
        no_partial_scores_used=True, scoring='Separate independent CPU oracle/P1/A3 required')


def execute(spec, run_id, out, store, guard, claim, commit, start, stop):
    """No launch route yet: later exact entry must validate release and own timer."""
    slot = slot_checked(run_id); model = spec['models'][slot['model']]
    if abs((stop-start)-slot['worker_seconds']) > .001:
        raise ValueError('Reviewed entry timer must cover setup through final packing')
    # Exact remote file manifests are prerequisites, never a fresh Hub download.
    inputs = Path(spec['remote_inputs']); verify(inputs, spec['inputs'])
    verify(model['remote_path'], model['files'])
    rows = {name:load_rows(inputs, name) for name in slot['datasets']}
    setup_start = time.time()
    guard.check_active(claim, now_epoch=setup_start, spent_cents=slot['reserved_cents'])
    if setup_start >= stop-30:
        raise TimeoutError('No setup window remains')
    connection, process = isolated(run_id, dict(model=model['remote_path'], tokenizer=model['remote_path'],inputs=str(inputs)))
    successful = False
    try:
        kind, info = receive(connection, process, stop)
        if kind != 'ready':
            raise ValueError('Exact model/engine was not ready')
        dump(Path(out)/'environment.json', info); commit()
        dump(Path(out)/'SETUP_OBSERVATION.json', dict(seconds=time.time()-setup_start,
            worker_elapsed_seconds=time.time()-start, includes_graph_compilation=True,
            observed_only_not_future_bound=True)); commit()
        result = generate_batches(run_id, rows, out, store, guard, claim, commit, start, stop,
                                  connection, process)
        successful = True
    finally:
        close_process(connection, process, stop, graceful=successful)
    if time.time() >= stop-30:
        raise TimeoutError('Model shutdown consumed closing reserve')
    result['worker_seconds_before_pack'] = time.time()-start
    return result
