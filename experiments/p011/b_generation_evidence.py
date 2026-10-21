"""Read-only complete B generation-body verification; full shared CR pending.

This verifies new B outputs only. It neither generates nor symbolically scores
answers. The eventual outer oracle must separately bind the accepted source,
actual inputs, model/engine, receipt, STOPPED0 provider and common deadline.
"""
from pathlib import Path
import math

from experiments.p011.b_generation_execution import validate_queue
from experiments.sft_allocation_midpoint.common import read, sha, digest


def check_body(ordered400, prompts, rows, out, key, claim, records,
               verify_transport, replay_forecast):
    """Verify every raw row and immutable acknowledgment without writing.

    Both callbacks must be the exact reviewed, deterministic read-only checks.
    verify_transport reconstructs the original token/EOS transport only; it is
    not a symbolic scorer. replay_forecast receives all previous full cycles.
    Original timing reports are checked for consistency, not remeasured.
    """
    roster_sha = validate_queue(ordered400, prompts, rows)
    out = Path(out)
    names = {'INTENT.json', 'COMPLETED.json'} | {
        f'batches/{i:03d}/{name}.json' for i in range(25)
        for name in ('FORECAST', 'INTENT', 'RAW', 'TRANSPORT', 'ACK')}
    actual = {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}
    if (actual != names or any(p.is_symlink() for p in out.rglob('*'))
            or records.get(key+'/claim') != claim):
        raise ValueError('Complete original B files and exact claim required; no partial oracle')
    job = {'claim':claim, 'roster_sha256':roster_sha, 'new_requests':6400,
           'temperature':1.0, 'new_training_updates':0, 'new_symbolic_scores':0}
    if read(out/'INTENT.json') != job or records.get(key+'/generation') != job:
        raise ValueError('Original B generation intent differs')
    expected_units = {key+f'/{kind}/{i:03d}' for kind in ('batch', 'batch_done')
                      for i in range(25)}
    actual_units = {k for k in records if k.startswith(key+'/batch/')
                    or k.startswith(key+'/batch_done/')}
    if actual_units != expected_units:
        raise ValueError('All25 original attempts and acknowledgments required')
    result = read(out/'COMPLETED.json')
    cycles = result.get('cycles')
    if not isinstance(cycles, list) or len(cycles) != 25:
        raise ValueError('All25 complete-cycle timing records required')
    expected_result = {'new_outputs':6400, 'complete_batches':25,
        'roster_sha256':roster_sha, 'cycles':cycles,
        'original_P010_outputs_regenerated':0, 'new_symbolic_scores':0,
        'selection_performed':False, 'training_admitted':False,
        'final_summary_write_excluded_from_cycles':True}
    if result != expected_result:
        raise ValueError('Original B complete result scope differs')
    seen, seconds, raw_hashes = set(), [], []
    for number, cycle in enumerate(cycles):
        duration = cycle.get('seconds')
        if (type(duration) not in (int, float) or not math.isfinite(duration)
                or duration <= 0 or cycle != {'batch':number, 'seconds':duration,
                    'three_commits_and_remote_ack_included':True}):
            raise ValueError('Positive original full-cycle timing required')
        first = 256*number
        part = rows[first:first+256]
        requests = [r['request'] for r in part]
        sampling = [r['sampling'] for r in part]
        directory = out/'batches'/f'{number:03d}'
        intent = {'first':first, 'requests':requests, 'sampling':sampling,
                  'roster_sha256':roster_sha}
        if (read(directory/'INTENT.json') != intent
                or records[key+f'/batch/{number:03d}'] != intent):
            raise ValueError('Saved batch input identity differs')
        if read(directory/'FORECAST.json') != replay_forecast(25-number, list(seconds)):
            raise ValueError('Original full-cycle forecast replay differs')
        raw = read(directory/'RAW.json')
        saved_transport = read(directory/'TRANSPORT.json')
        if len(raw) != 256 or len(saved_transport) != 256:
            raise ValueError('All256 raw outputs and transport records required')
        for x, request, params, transport in zip(raw, requests, sampling, saved_transport):
            cid = request['candidate_id']
            if (cid in seen or x.get('candidate_id') != cid
                    or x.get('problem_id') != request['problem_id']
                    or x.get('source_row_sha256') is not None
                    or x.get('prompt_token_ids') != request['prompt_token_ids']
                    or x.get('sampling') != params or type(x.get('output_count')) is not int
                    or x['output_count'] != 1
                    or set(x) != {'candidate_id','problem_id','source_row_sha256',
                        'sampling','prompt_token_ids','output_count','token_ids',
                        'backend_text','finish_reason','stop_reason'}):
                raise ValueError('Foreign, duplicated or incomplete original raw output')
            if verify_transport(x) != transport:
                raise ValueError('Original complete token/EOS transport differs')
            seen.add(cid)
        ack = {'count':256, 'first':first, 'raw_file_sha256':sha(directory/'RAW.json'),
               'transport_file_sha256':sha(directory/'TRANSPORT.json')}
        if (read(directory/'ACK.json') != ack
                or records[key+f'/batch_done/{number:03d}'] != ack):
            raise ValueError('Original byte hashes or immutable batch acknowledgment differ')
        raw_hashes.append(ack['raw_file_sha256'])
        seconds.append(duration)
    if len(seen) != 6400:
        raise ValueError('Full original400x16 output roster required')
    return {'verified_new_outputs':len(seen), 'verified_batches':25,
        'roster_sha256':roster_sha, 'ordered_raw_files_sha256':digest(raw_hashes),
        'new_generation_calls':0, 'new_symbolic_scores':0, 'selection_performed':False,
        'original_P010_outputs_read_or_scored':0,
        'actual_timing_not_remeasured':True,
        'outer_receipt_provider_source_input_budget_window_still_required':True}
