"""Candidate suffix execution. Original 128 raw rows are read, never generated."""
import math
from pathlib import Path
import tempfile
import time
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from experiments.learning_regime_p009.p0_contract import ROLES, prompts_checked, raw_checked
from experiments.learning_regime_p009.p0_runtime import isolated, receive, close_process
from experiments.learning_regime_p009.p0_suffix_contract import (
    PARENT_CAMPAIGN, PARENT_RUN, RUN, OFFSETS, RESERVED_CENTS,
    check_parent, remaining_forecast,
)


def execute(spec, out, store, guard, admitted, commit, start, stop):
    out = Path(out); original = spec['parent_spec']
    inputs = Path(original['remote_inputs']); verify(inputs, original['inputs'])
    pre = 'midpoint/'+PARENT_CAMPAIGN+'/'
    parent_ledger = {key: store.get(key) for key in spec['parent_ledger_keys']}
    prefix_proof = check_parent(spec, Path('/evidence')/PARENT_CAMPAIGN/PARENT_RUN,
                                parent_ledger, inputs)
    marker = dict(child_campaign=guard.plan['campaign_id'], child_run=RUN,
        child_claim_sha256=admitted.claim_sha256, spec_sha256=digest(spec),
        original_terminal=spec['parent_terminal'], suffix_outputs=2510)
    # One immutable cross-campaign marker: a later distinct child cannot replay.
    marker_key = pre+'continuation/'+PARENT_RUN
    if not store.put(marker_key, marker, skip_if_exists=True):
        raise ValueError('Any prior suffix marker permanently blocks this call')
    dump(out/'PARENT_PREFIX_PROOF.json', prefix_proof)
    dump(out/'PARENT_CONTINUATION_MARKER.json', marker); commit()
    rows = prompts_checked(read(inputs/'qwen_gsm_zero_parity.json'))
    base = Path(original['remote_base_model']); verify(base, original['base_files'])
    checkpoint = Path(original['remote_reference_checkpoint'])
    verify(checkpoint, original['checkpoint_files'])
    tmp = Path(tempfile.mkdtemp(prefix='p009-p0-suffix-'))
    observed = [spec['failed_forecast']['full_batch_max_seconds']]
    completed = 0; total_batches = 80; setup = []; forecasts = []
    key = guard.prefix+admitted.run_id

    def check():
        if time.time() >= stop-30:
            raise TimeoutError('Suffix worker soft deadline')
        guard.check_active(admitted, now_epoch=time.time(), spent_cents=RESERVED_CENTS)

    def once(record_key, value):
        if not store.put(record_key, value, skip_if_exists=True):
            raise ValueError('Existing/ambiguous suffix unit; never repeat')

    for role in ROLES:
        setup_start = time.time(); check(); model = base
        if role == 'correct_969':
            connection, process = isolated('merge', dict(base=str(base), checkpoint=str(checkpoint),
                destination=str(tmp/'merged_969'), proof=str(out/'MERGE_PROOF.json')))
            try:
                kind, info = receive(connection, process, stop)
                if kind != 'merged':
                    raise ValueError('Reference merge incomplete')
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
            for offset in range(OFFSETS[role], len(rows), 32):
                batch_start = time.time(); check()
                forecast = remaining_forecast(time.time()-start, observed, total_batches-completed)
                dump(out/'forecasts'/f'{completed:03d}.json', forecast); commit()
                forecasts.append(forecast)
                if not forecast['admitted']:
                    raise TimeoutError('Actual remaining suffix forecast exceeds original reviewed amendment')
                part = rows[offset:offset+32]; name = f'{role}_{offset:04d}'
                intent = dict(role=role, offset=offset, problem_ids=[r['problem_id'] for r in part],
                    prompt_sha256=digest(part), started_epoch=batch_start,
                    preceding_observed_max_and_new_full_batches=list(observed))
                once(key+'/unit/'+name, intent)
                dump(out/'intents'/f'{name}.json', intent); commit()
                connection.send(('generate', part))
                kind, raw = receive(connection, process, stop)
                if kind != 'outputs':
                    raise ValueError('Unexpected engine reply')
                rawpath = out/role/'raw'/f'{offset:04d}.json'
                dump(rawpath, raw); commit(); raw_checked(part, raw)
                ack = dict(count=len(part), raw_sha256=sha(rawpath),
                    problem_ids=intent['problem_ids'], finished_epoch=time.time())
                dump(out/'completed'/f'{name}.json', ack); commit(); once(key+'/done/'+name, ack)
                dump(out/'timings'/f'{name}.json', dict(through_done_ack_seconds=time.time()-batch_start,
                    note='Final timing metadata commit is included in the complete interval vector'))
                commit(); observed.append(time.time()-batch_start); completed += 1
                print(f'P0 suffix {role}: original endpoint through {offset+len(part)}/1319', flush=True)
            dump(out/role/'GENERATION_COMPLETE.json', dict(original_endpoint_outputs=1319,
                new_outputs=1319-OFFSETS[role], inherited_outputs=OFFSETS[role], new_training_updates=0))
            commit()
        finally:
            close_process(connection, process, stop, graceful=True)
    check()
    if completed != total_batches:
        raise ValueError('Incomplete suffix batch count')
    return dict(suffix_outputs=2510, inherited_outputs=128, total_logical_outputs=2638,
        suffix_batches=80, new_training_updates=0, parent_status='failed',
        inherited_full_batch_max_seconds=observed[0], new_full_batch_seconds=observed[1:],
        setup=setup, forecasts=forecasts, worker_seconds_before_pack=time.time()-start,
        original_failed_forecast=spec['failed_forecast'], parity_decision='not yet scored')
