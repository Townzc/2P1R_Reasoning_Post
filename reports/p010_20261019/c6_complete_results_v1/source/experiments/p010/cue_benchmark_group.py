"""One bounded original four-cell C6 benchmark; no training or model merging.

Each model lifetime owns a fresh child process. The outer single call owns every
cell and every once-only batch, including failures. No completed prefix is
replayed. Exact input/source/numeric A2 is supplied by the future entry.
"""
from math import ceil, isfinite
from pathlib import Path
import time

from experiments.p010.common import read, dump, verify, digest, budget_check
from experiments.p010.cue_benchmark_roster import RUNS

KEY = 'cue/benchmark_group_r1'
HARD_SECONDS = 5400
FULL_WINDOW = 6100
RESERVE = '8.65'
RATE = .001097 + 4*.0000131 + 32*.00000222


def check_rosters(rosters):
    if list(rosters) != list(RUNS):
        raise ValueError('All four original cells in their fixed order required')
    counts = [4500, 11871, 2500, 2500]
    for run, expected in zip(RUNS, counts):
        r = rosters[run]
        if (r['run'] != run or r['selected_cue'] != [1249]
                or r['new_outputs'] != expected or len(r['rows']) != expected
                or len({x['candidate_id'] for x in r['rows']}) != expected
                or r['greedy_regeneration'] is not False
                or r['new_training_updates'] != 0 or r['aliases']):
            raise ValueError('Exact actual selected-cue roster differs')
    return sum(ceil(n/256) for n in counts)


def forecast(elapsed, completed, new_times, observed, prior):
    # Four complete model/setup/closing allowances remain in every scenario.
    # This is deliberately not a speed guarantee or calibrated upper bound.
    if (type(completed) is not int or not 0 <= completed <= 85
            or len(new_times) != completed or not observed
            or not isfinite(elapsed) or elapsed < 0
            or any(not isfinite(x) or x <= 0 for x in list(new_times)+list(observed))):
        raise ValueError('Complete real batch history and finite timing required')
    maximum = max(list(new_times)+list(observed))
    remaining = 1.2*(maximum*(85-completed)+4*600)
    total = elapsed+remaining
    if total > HARD_SECONDS-30:
        raise TimeoutError('Original four-cell remainder exceeds bounded worker')
    return dict(elapsed_seconds=elapsed, completed_batches=completed, full_batches=85,
        maximum_completed_batch_seconds=maximum, original_observations=list(observed),
        actual_completed_batch_seconds=list(new_times), remaining_seconds=remaining,
        total_seconds=total, uncalibrated_setup_allowance_seconds=2400, margin=1.2,
        calibrated_bound=False, first_paid_measurement_exceptions=0,
        budget=budget_check('I', prior, RESERVE, (total+700)*RATE))


def model_reuse(run, binding, store):
    if run not in RUNS or any(binding[k] != 0 for k in
            ('new_training_updates', 'new_checkpoint_loads', 'new_merge_operations')):
        raise ValueError('Original persisted model only; no training/load/merge')
    parent = binding['parent']
    if run.startswith('base_'):
        if parent is not None:
            raise ValueError('Base cannot inherit a student model')
    else:
        expected = ('existing_s1_samples/s1_s17_n400' if run == 's1_n400_math'
                    else 'student/t72_s17_n400_k1')
        if (parent['terminal_key'] != expected+'/terminal'
                or parent['terminal']['status'] != 'completed'
                or store.get(parent['terminal_key']) != parent['terminal']
                or parent['original_merged_files'] != binding['files']):
            raise ValueError('Original completed parent or persisted model differs')
    verify(binding['remote_path'], binding['files'])
    return dict(run=run, model_files=binding['files'], parent=parent,
        new_training_updates=0, new_checkpoint_loads=0, new_merge_operations=0)


def generate_cell(run, out, roster, binding, claim, started, deadline,
                  observed, inherited_times, prior, store, volume):
    """Invoked once in an owned child; all old outputs stay outside this roster."""
    from vllm import LLM, SamplingParams
    from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine
    from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
    if (run not in RUNS or roster['run'] != run
            or abs(deadline-started-HARD_SECONDS) > .001
            or store.get(KEY+'/claim') != claim
            or len(roster['rows']) != roster['new_outputs']):
        raise ValueError('Original group claim, clock or complete cell differs')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    proof = model_reuse(run, binding, store)
    dump(out/'MODEL_REUSE_PROOF.json', proof)
    dump(out/'BENCHMARK_ROSTER.json', roster)
    volume.commit()
    rows = roster['rows']; times = list(inherited_times)
    params = [r['sampling'] for r in rows]
    constructed = [SamplingParams(**p) for p in params]
    dump(out/'BEFORE_MODEL_FORECAST.json', forecast(time.time()-started,
        len(times), times, observed, prior)); volume.commit()
    llm = LLM(model=binding['remote_path'], tokenizer=binding['remote_path'], **engine_kwargs())
    dump(out/'ENGINE.json', actual_engine(llm.llm_engine.vllm_config)); volume.commit()
    for offset in range(0, len(rows), 256):
        unit = f'{offset:05d}'; part = rows[offset:offset+256]
        if store.get(KEY+'/claim') != claim:
            raise ValueError('Original group claim changed')
        if binding['parent'] is not None and store.get(binding['parent']['terminal_key']) != binding['parent']['terminal']:
            raise ValueError('Original persisted model parent changed')
        f = forecast(time.time()-started, len(times), times, observed, prior)
        dump(out/'batch_forecasts'/(unit+'.json'), f)
        intent = dict(rows=part, sampling=params[offset:offset+256], epoch=time.time())
        if not store.put(KEY+'/'+run+'/batch/'+unit, intent, skip_if_exists=True):
            raise RuntimeError('Original benchmark batch already attempted')
        dump(out/'batch_intents'/(unit+'.json'), intent); volume.commit()
        tick = time.monotonic()
        outputs = llm.generate([dict(prompt_token_ids=r['input_ids']) for r in part],
            constructed[offset:offset+256], use_tqdm=False)
        raw = returned_records(part, params[offset:offset+256], outputs)
        dump(out/'raw'/(unit+'.json'), raw); volume.commit()
        if (len(raw) != len(part) or any(x['output_count'] != 1
                or x['candidate_id'] != r['candidate_id'] or x['prompt_token_ids'] != r['input_ids']
                for x, r in zip(raw, part))):
            raise ValueError('Saved original response identity differs')
        ack = dict(count=len(part), raw_sha256=digest(raw), seconds=time.monotonic()-tick)
        times.append(ack['seconds']); dump(out/'batch_acks'/(unit+'.json'), ack)
        if not store.put(KEY+'/'+run+'/batch_done/'+unit, ack, skip_if_exists=True):
            raise RuntimeError('Original benchmark batch acknowledgment exists')
        volume.commit()
    if time.time() >= deadline-15:
        raise TimeoutError('Original whole worker needs closeout time')
    result = dict(run=run, new_outputs=len(rows), batch_seconds=times[len(inherited_times):],
        total_completed_batches=len(times), new_training_updates=0,
        new_checkpoint_loads=0, new_merge_operations=0)
    dump(out/'RESULT.json', result); volume.commit()
    return result


def child(conn, run, input_path, out_path, binding, claim, started, deadline,
          observed, inherited_times, prior):
    import traceback
    import modal
    try:
        volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        store = modal.Dict.from_name('p010-once-20261019', create_if_missing=False)
        volume.reload()
        result = generate_cell(run, out_path, read(input_path), binding, claim, started,
            deadline, observed, inherited_times, prior, store, volume)
        conn.send(('complete', result))
    except BaseException:
        conn.send(('error', traceback.format_exc()))
        raise
    finally:
        conn.close()
