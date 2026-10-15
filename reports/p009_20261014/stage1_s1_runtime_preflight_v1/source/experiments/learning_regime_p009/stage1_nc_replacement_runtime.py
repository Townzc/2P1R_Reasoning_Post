# Distinct owner-approved physical replacement; original sources retained unchanged.
"""Two finite NC training/endpoints; the reviewed entry owns admission/timer.

There is one fresh training subprocess and then one fresh endpoint subprocess.
They never overlap. Every ambiguous attempt is permanent; no retry/continuation.
"""
import math
import multiprocessing
from pathlib import Path
import tempfile
import time

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from experiments.learning_regime_p009.p0_runtime import receive, close_process
from experiments.learning_regime_p009.stage1_nc_replacement_contract import slot, forecast, transport_checked
from experiments.learning_regime_p009.stage1_endpoint_engine import checked_endpoint


def spawn_process(target, args):
    ctx = multiprocessing.get_context('spawn')
    parent, remote = ctx.Pipe()
    process = ctx.Process(target=target, args=(remote,)+tuple(args), daemon=False)
    process.start(); remote.close()
    return parent, process


def training_once(target, args, stop):
    """A message alone is insufficient: actual successful exit precedes vLLM."""
    connection, process = spawn_process(target, args)
    try:
        kind, result = receive(connection, process, stop)
        if kind != 'trained':
            raise ValueError('Training did not return its complete state/merge proof')
        process.join(timeout=max(0., min(30., stop-30-time.time())))
        if process.is_alive() or process.exitcode != 0:
            raise RuntimeError('Training process has not exited successfully; no endpoint may start')
        return result, dict(pid=process.pid, exitcode=process.exitcode,
                           observed_exited_epoch=time.time(), joined_before_endpoint=True)
    finally:
        close_process(connection, process, stop, graceful=False)


def endpoint_batches(rows, out, store, guard, claim, commit, start, stop,
                     connection, process, prior, train_seconds, stage_remaining):
    checked_endpoint('NC', rows)
    out = Path(out); durations = []; key = guard.prefix+claim.run_id
    cap = slot(claim.run_id)

    def once(k, value):
        if not store.put(k, value, skip_if_exists=True):
            raise ValueError('Prior or ambiguous NC batch/ack exists; never regenerate')

    for index, offset in enumerate(range(0, len(rows), 256)):
        tick = time.time()
        if tick >= stop-30:
            raise TimeoutError('Whole-worker deadline; preserve remaining missing outputs')
        guard.check_active(claim, now_epoch=tick, spent_cents=cap['reserved_cents'])
        predicted = forecast(time.time()-start, 0, math.ceil((len(rows)-offset)/256),
            prior['training_block_seconds']+train_seconds,
            prior['endpoint_batch_seconds']+durations, stage_remaining)
        dump(out/'endpoint_forecasts'/f'{index:03d}.json', predicted); commit()
        if not predicted['admitted']:
            raise TimeoutError('NC endpoint remainder exceeds the reviewed time/budget gate')
        part = rows[offset:offset+256]; unit = f'endpoint_{offset:05d}'
        request = dict(offset=offset, count=len(part), request_sha256=digest(part),
            candidate_ids=[x['candidate_id'] for x in part], started_epoch=tick,
            preceding_full_batch_seconds=list(durations), measurement_exception=False)
        once(key+'/unit/'+unit, request)
        dump(out/'intents'/f'{unit}.json', request); commit()
        connection.send(('generate', offset))
        kind, raw = receive(connection, process, stop)
        if kind != 'outputs':
            raise ValueError('Ambiguous endpoint response; never resend')
        raw_path = out/'endpoint/raw'/f'{offset:05d}.json'
        dump(raw_path, raw); commit()  # Preserve malformed replies before rejecting them.
        transport_checked(rows, part, raw)
        ack = dict(count=len(part), candidate_ids=request['candidate_ids'],
            request_sha256=request['request_sha256'], raw_sha256=sha(raw_path),
            finished_epoch=time.time(), original_backend_metadata_preserved=True)
        dump(out/'completed'/f'{unit}.json', ack); commit()
        once(key+'/done/'+unit, ack)
        dump(out/'endpoint_timings'/f'{index:03d}.json',
             dict(through_done_ack_seconds=time.time()-tick,
                  final_metadata_write_in_complete_vector=True)); commit()
        durations.append(time.time()-tick)
        print(f'P009 {claim.run_id}: saved endpoint {offset+len(part)}/1319', flush=True)
    return dict(outputs=len(rows), batches=len(durations), full_batch_intervals_seconds=durations,
                new_training_during_endpoint=0, no_partial_score_used=True)


def execute(spec, plan, run, out, store, guard, claim, commit, start, stop):
    from experiments.learning_regime_p009.stage1_nc_replacement_training_process import child as training_child
    from experiments.learning_regime_p009.stage1_endpoint_engine import child as endpoint_child
    cap = slot(run); out = Path(out); inputs = Path(spec['remote_inputs'])
    if abs(stop-start-cap['worker_seconds']) > .001:
        raise ValueError('Whole worker timer must begin before admission/setup')
    verify(inputs, spec['inputs']); verify(spec['base']['remote_path'], spec['base']['files'])
    config = read(inputs/f'nc17_n{cap["n"]}_config.json')
    rows = read(inputs/'NC_ENDPOINT.json'); checked_endpoint('NC', rows)
    prior = spec['timing']; stage_remaining = spec['stage_remaining_before_cents'][run]
    predicted = forecast(time.time()-start, 64, 6, prior['training_block_seconds'],
                         prior['endpoint_batch_seconds'], stage_remaining)
    dump(out/'BEFORE_TRAINING_FORECAST.json', predicted); commit()
    if not predicted['admitted']:
        raise TimeoutError('No training may begin without the complete projected window')
    identity = dict(campaign=plan['campaign_id'], run_id=run, config=config,
        spec_sha256=digest(spec), source_files=spec['source_files'],
        base_files=spec['base']['files'], input_files=spec['inputs'],
        config_sha256=digest(config), actual_NC_G0_report_sha256=spec['G0_report_sha256'],
        input_review_report_sha256=spec['input_report_sha256'])
    temporary = Path(tempfile.mkdtemp(prefix='p009-nc-'))
    paths = dict(base=spec['base']['remote_path'], tokenizer=spec['base']['remote_path'],
                 inputs=str(inputs), out=str(out), merged=str(temporary/'merged'))
    trained, joined = training_once(training_child,
        (paths, plan, claim, identity, prior, stage_remaining, start, stop), stop)
    dump(out/'TRAINING_PROCESS_EXITED.json', joined); commit()
    if trained['updates'] != 1024 or trained['targets'] != 2097148:
        raise ValueError('Incomplete original scientific dose')
    merged = read(out/'MERGE_PROOF.json')['merged_files']
    verify(paths['merged'], merged)
    connection, process = spawn_process(endpoint_child,
        ('NC', dict(model=paths['merged'], tokenizer=paths['merged']), rows, merged))
    success = False
    try:
        kind, info = receive(connection, process, stop)
        if kind != 'ready':
            raise ValueError('Exact merged endpoint engine did not initialize')
        info['training_process_exit'] = joined
        info['endpoint_process_pid'] = process.pid
        dump(out/'endpoint/environment.json', info); commit()
        evaluated = endpoint_batches(rows, out, store, guard, claim, commit, start, stop,
            connection, process, prior, trained['full_block_intervals_seconds'], stage_remaining)
        success = True
    finally:
        close_process(connection, process, stop, graceful=success)
    if time.time() >= stop-30:
        raise TimeoutError('Original shutdown/packing window exhausted')
    return dict(run_id=run, training=trained, endpoint=evaluated,
                worker_seconds_before_pack=time.time()-start, checkpoint_selection=False,
                reserved_cents=cap['reserved_cents'], reservation_is_invoice=False,
                new_outputs=1319, updates=1024, targets=2097148,
                future_host_timing_guarantee=False, scoring='Independent local full oracle required')
