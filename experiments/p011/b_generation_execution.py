"""B-only complete 400x16 generation journal, prepared for shared full-path CR.

The outer path must verify the real input A1, fixed model/engine, owner B16 rule,
source closure, timing, shared budget ledger and claim before calling this body.
No loader, dispatch, scorer, input constructor or paid admission is provided here.
"""
from pathlib import Path
import time

from experiments.p011.short_generation import b_requests
from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
from experiments.sft_allocation_midpoint.common import digest, dump, sha


def validate_queue(ordered400, prompts, rows):
    if set(prompts) != set(ordered400):
        raise ValueError('Only the original400 prompt identities are allowed')
    for ids in prompts.values():
        if (not ids or any(type(i) is not int or not 0 <= i < 151936 for i in ids)
                or len(ids)+1024 > 2048):
            raise ValueError('Complete original native prompt tokens required')
    expected = b_requests(ordered400, prompts, 1.0)
    if rows != expected:
        raise ValueError('Exact B T1.0 original400 x16 ordered seeds/sampling required')
    return digest(rows)


def generate(ordered400, prompts, rows, out, key, claim, store, commit,
             llm, parameter_constructor, transport, forecast, check,
             clock=time.monotonic):
    """Once-only complete generation, retaining raw output before validation.

    `forecast(remaining_batches, complete_cycle_seconds)` includes every old and
    new complete-cycle maximum and the shared remaining category budget. Its
    exact numerical basis must be approved with the eventual outer runtime.
    `transport(raw)` is the original P010 token/EOS transport verifier, not a
    symbolic scorer. The final result write is outside cycle timing and requires
    explicit closing allowance. No prefix resume or retry is implemented.
    """
    roster_sha = validate_queue(ordered400, prompts, rows)
    check()
    if store.get(key+'/claim') != claim:
        raise ValueError('Original outer claim differs')
    out = Path(out)
    if out.exists():
        raise ValueError('Existing output, including partial, cannot be replayed')
    # Constructor validation precedes any batch/model generation.
    parameters = [parameter_constructor(**r['sampling']) for r in rows]
    job = {'claim':claim, 'roster_sha256':roster_sha, 'new_requests':6400,
           'temperature':1.0, 'new_training_updates':0, 'new_symbolic_scores':0}
    if not store.put(key+'/generation', job, skip_if_exists=True):
        raise ValueError('Original B generation was already attempted')
    out.mkdir(parents=False, exist_ok=False)
    cycles, generated = [], 0
    try:
        dump(out/'INTENT.json', job)
        commit()
        for first in range(0, 6400, 256):
            start = clock()
            check()
            if store.get(key+'/claim') != claim:
                raise ValueError('Original outer claim changed')
            number = first//256
            part = rows[first:first+256]
            projection = forecast(25-number, [x['seconds'] for x in cycles])
            requests = [r['request'] for r in part]
            params = [r['sampling'] for r in part]
            intent = {'first':first, 'requests':requests, 'sampling':params,
                      'roster_sha256':roster_sha}
            unit = key+f'/batch/{number:03d}'
            if not store.put(unit, intent, skip_if_exists=True):
                raise ValueError('A B batch was already attempted; no regeneration')
            directory = out/'batches'/f'{number:03d}'
            dump(directory/'FORECAST.json', projection)
            dump(directory/'INTENT.json', intent)
            commit()
            outputs = llm.generate(
                [{'prompt_token_ids':r['prompt_token_ids']} for r in requests],
                parameters[first:first+256], use_tqdm=False)
            raw = returned_records(requests, params, outputs)
            dump(directory/'RAW.json', raw)
            commit()
            check()
            if (len(raw) != len(part) or any(
                    x['candidate_id'] != r['candidate_id'] or
                    x['prompt_token_ids'] != r['prompt_token_ids'] or
                    x['sampling'] != p or x['output_count'] != 1
                    for x, r, p in zip(raw, requests, params))):
                raise ValueError('Incomplete or foreign raw output; original bytes retained')
            verified = [transport(x) for x in raw]
            dump(directory/'TRANSPORT.json', verified)
            ack = {'count':len(raw), 'first':first,
                   'raw_file_sha256':sha(directory/'RAW.json'),
                   'transport_file_sha256':sha(directory/'TRANSPORT.json')}
            dump(directory/'ACK.json', ack)
            commit()
            if not store.put(key+f'/batch_done/{number:03d}', ack, skip_if_exists=True):
                raise ValueError('Duplicate batch acknowledgment')
            end = clock()
            if end <= start:
                raise ValueError('Positive complete-cycle interval required')
            cycles.append({'batch':number, 'seconds':end-start,
                           'three_commits_and_remote_ack_included':True})
            generated += len(raw)
        check()
        result = {'new_outputs':generated, 'complete_batches':len(cycles),
                  'roster_sha256':roster_sha, 'cycles':cycles,
                  'original_P010_outputs_regenerated':0, 'new_symbolic_scores':0,
                  'selection_performed':False, 'training_admitted':False,
                  'final_summary_write_excluded_from_cycles':True}
        dump(out/'COMPLETED.json', result)
        commit()
        check()
        return result
    except BaseException as exc:
        dump(out/'FAILED.json', {'type':type(exc).__name__, 'error':str(exc),
             'complete_batches':len(cycles), 'confirmed_outputs':generated,
             'cycles':cycles, 'automatic_retry':False,
             'partial_raw_must_be_preserved':True})
        commit()
        raise
