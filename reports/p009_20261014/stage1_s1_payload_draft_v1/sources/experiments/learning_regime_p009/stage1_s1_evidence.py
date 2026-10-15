"""Prepared S1 payload checks, without dispatch or full admission authority.

The future exact oracle must first verify its runtime/source/input reviews,
claim/terminal/envelope, complete manifest and provider STOPPED0. These helpers
then verify the original training trajectory and decode every endpoint once.
They do not perform symbolic scoring, select checkpoints or grant S1 admission.
"""
from collections import Counter
import math
from pathlib import Path

from analyses.completion_contract import first_stop
from experiments.sft_allocation_midpoint.common import read, sha, digest
from experiments.sft_allocation_midpoint import checkpoint as ck
from experiments.sft_allocation_p008.block_journal import POLICY, verify_training_blocks
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, validate_observed_engine
from experiments.learning_regime_p009.stage1_s1_contract import recipe, limits_checked, forecast, transport_checked
from experiments.learning_regime_p009.stage1_training_core import checked_recipe
from scripts.audit_p009_stage1_nc import check_state
from src.sft_data import encode_row


def positive_intervals(values, count):
    if (not isinstance(values, list) or len(values) != count
            or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in values)):
        raise ValueError('All original finite positive completion intervals required')
    return values


def assemble_math_rows(endpoint, decoded, gold):
    """Bind all500 rows to original gold; no extraction, label or symbolic work."""
    if (not isinstance(endpoint, list) or len(endpoint) != 500
            or len({x['problem_id'] for x in endpoint}) != 500
            or len({x['candidate_id'] for x in endpoint}) != 500
            or not isinstance(decoded, list) or len(decoded) != 500
            or set(gold) != {x['problem_id'] for x in endpoint}):
        raise ValueError('Exactly the500 original endpoint identities and golds required')
    rows = []
    for original, item in zip(endpoint, decoded):
        if (item['problem_id'] != original['problem_id']
                or item['candidate_id'] != original['candidate_id']
                or item['source_row_sha256'] != original['source_row_sha256']):
            raise ValueError('Original endpoint order/source identity differs')
        answer = gold[original['problem_id']]['answer']
        stop = item['stop']
        if (not isinstance(answer, str) or not answer.strip()
                or stop['stop_reason'] not in ('native_eos', 'new_problem_boundary',
                                                'length_cap', 'invalid_special_token')
                or not isinstance(stop['answer_segment'], str)):
            raise ValueError('Unsupported gold or unknown stop cannot become a score zero')
        rows.append(dict(id=item['candidate_id'], problem_id=item['problem_id'],
            gold=answer, original_gold_row_sha256=digest(gold[item['problem_id']]),
            answer_segment=stop['answer_segment'], stop_reason=stop['stop_reason'],
            original_decoded_record_sha256=digest(item)))
    return dict(rows=rows, row_count=500, unsupported_gold_count=0,
                symbolic_scoring_performed=False, scientific_G1_admitted=False)


def verify_training_payload(root, inputs, spec, run, terminal, ledger, tokenizer):
    """Verify a full1024 original state once, after the future outer binding."""
    root, inputs = Path(root), Path(inputs)
    expected = recipe(run); cap = limits_checked(spec['slots'][run])
    rows, encoded, plan, cfg = [read(inputs/(run+'_'+k+'.json'))
                                for k in ('rows', 'encoded', 'plan', 'config')]
    if any(cfg.get(k) != expected[k] for k in ('setting', 'seed', 'n', 'updates', 'targets')):
        raise ValueError('Only the original complete S1 recipe is supported')
    checked_recipe(cfg, encoded, plan)
    if [encode_row(x, tokenizer, 2048) for x in rows] != encoded:
        raise ValueError('Independent full-answer encoding differs')
    stored = read(root/'recipe.json'); identity = stored['identity']
    wanted = dict(campaign=spec['campaign'], run_id=run, config=cfg,
        spec_sha256=digest(spec), source_files=spec['source_files'],
        base_files=spec['base']['files'], input_files=spec['inputs'],
        config_sha256=digest(cfg), actual_S1_G0_report_sha256=spec['G0_report_sha256'],
        actual_NC_A4_report_sha256=spec['NC_A4_report_sha256'],
        input_review_report_sha256=spec['input_report_sha256'])
    if (identity != wanted or stored['schedule'] != plan['updates']
            or stored['lrs'] != plan['lrs']):
        raise ValueError('Original S1 identity/schedule/LR differs')
    attempts = {p.stem: read(p) for p in (root/'intents').glob('*.json')}
    done = {p.stem: read(p) for p in (root/'completed').glob('*.json')}
    if set(attempts) != set(done):
        raise ValueError('Unknown/partial units cannot be accepted')
    prefix = 'midpoint/'+spec['campaign']+'/'+run+'/'
    blocks = verify_training_blocks(attempts, done, ledger, prefix, 1024)
    expected_units = ({f'update_{i:04d}' for i in range(1, 1025)} | blocks
                      | {'terminal_merge', 'endpoint_00000', 'endpoint_00256'})
    if set(done) != expected_units:
        raise ValueError('Extra/missing original S1 training or endpoint units')
    targets = processed = 0
    for step, indices in enumerate(plan['updates'], 1):
        value = dict(step=step, indices=indices, lr=plan['lrs'][step-1],
            supervised_tokens=sum(encoded[i]['n_supervised'] for i in indices),
            processed_tokens=sum(encoded[i]['n_processed'] for i in indices))
        targets += value['supervised_tokens']; processed += value['processed_tokens']
        key = f'update_{step:04d}'
        if (attempts[key] != value or any(done[key].get(k) != v for k, v in value.items())
                or done[key]['cumulative_targets'] != targets
                or done[key]['cumulative_processed'] != processed):
            raise ValueError('Actual complete-answer per-update dose differs')
    if targets != 2097148:
        raise ValueError('Original full S1 target dose differs')
    state = ck.load(root/'checkpoint_1024', identity)
    check_state(state, identity, plan, targets, processed)
    result = read(root/'result.json'); trained = result['training']
    train_seconds = positive_intervals(trained['full_block_intervals_seconds'], 64)
    merge = read(root/'MERGE_PROOF.json'); joined = read(root/'TRAINING_PROCESS_EXITED.json')
    if (read(root/'TRAINING_CHILD_RESULT.json') != trained
            or trained['checkpoint'] != read(root/'checkpoint_1024/manifest.json')
            or trained['identity_sha256'] != digest(identity)
            or merge['checkpoint'] != trained['checkpoint'] or merge['merge_dtype'] != 'float32'
            or merge['saved_dtype'] != 'bfloat16' or merge['optimizer_updates_after_terminal_save'] != 0
            or done['terminal_merge']['proof_sha256'] != digest(merge)
            or joined['exitcode'] != 0 or joined['joined_before_endpoint'] is not True
            or joined['observed_exited_epoch'] > terminal['finished_epoch']):
        raise ValueError('Complete original checkpoint/merge/process-exit proof differs')
    process = read(root/'TRAINING_PROCESS.json'); env = read(root/'training_environment.json')
    if (process['threads'] != 4 or process['CUBLAS_WORKSPACE_CONFIG'] != ':4096:8'
            or 'H100' not in process['gpu'] or process['tokenizer_is_verified_base'] is not True
            or env['deterministic_algorithms'] is not True or env['allow_tf32'] is not False):
        raise ValueError('Original deterministic training environment differs')
    metrics = read(root/'block_journal_metrics.json')
    if any(metrics[k] != v for k, v in dict(policy=POLICY, completed_blocks=64,
            completed_local_updates=1024, configured_updates=1024, block_boundary_calls=128).items()):
        raise ValueError('Original block journal metrics differ')
    prior = spec['timing']; stage = spec['stage_remaining_before_cents'][run]
    f = read(root/'BEFORE_TRAINING_FORECAST.json')
    if (f != forecast(f['elapsed_worker_seconds'], 64, 2, prior['training_block_seconds'],
                      prior['endpoint_batch_seconds'], stage, cap) or not f['admitted']):
        raise ValueError('Original pretraining forecast failed')
    for index in range(64):
        f = read(root/'training_forecasts'/f'{index:03d}.json')
        if (f != forecast(f['elapsed_worker_seconds'], 64-index, 2,
                prior['training_block_seconds']+train_seconds[:index],
                prior['endpoint_batch_seconds'], stage, cap) or not f['admitted']):
            raise ValueError('Original all-observation training forecast differs')
        t = read(root/'training_timings'/f'{index:03d}.json')
        if not 0 < t['through_original_block_commit_seconds'] <= train_seconds[index]:
            raise ValueError('Original full training-block timing is incomplete')
    return dict(identity=identity, attempts=attempts, done=done, joined=joined,
        train_seconds=train_seconds, result=result, targets=targets, processed=processed,
        state_sha256=sha(root/'checkpoint_1024/state.pt'),
        payload_only=True, full_runtime_lineage_admission_checked=False)


def verify_endpoint_payload(root, endpoint, spec, run, terminal, training, tokenizer, gold):
    """Decode the two complete original batches exactly once, without scoring."""
    root = Path(root); cap = limits_checked(spec['slots'][run])
    prior = spec['timing']; stage = spec['stage_remaining_before_cents'][run]
    durations = positive_intervals(training['result']['endpoint']['full_batch_intervals_seconds'], 2)
    environment = read(root/'endpoint/environment.json')
    validate_observed_engine(environment['actual_engine'])
    if (environment['requested_engine'] != engine_kwargs()
            or environment['training_process_exit'] != training['joined']
            or environment['endpoint_rows_sha256'] != digest(endpoint)
            or {p.name for p in (root/'endpoint/raw').glob('*.json')} != {'00000.json', '00256.json'}):
        raise ValueError('Original exact500 endpoint/engine/process/batch roster differs')
    vocab = set(tokenizer.get_vocab().values()); special = tuple(tokenizer.all_special_ids)
    decoded = []; stops = Counter()
    for index, offset in enumerate((0, 256)):
        f = read(root/'endpoint_forecasts'/f'{index:03d}.json')
        if (f != forecast(f['elapsed_worker_seconds'], 0, 2-index,
                prior['training_block_seconds']+training['train_seconds'],
                prior['endpoint_batch_seconds']+durations[:index], stage, cap) or not f['admitted']):
            raise ValueError('Original endpoint forecast differs')
        part = endpoint[offset:offset+256]; p = root/'endpoint/raw'/f'{offset:05d}.json'; raw = read(p)
        transport_checked(endpoint, part, raw)
        unit = f'endpoint_{offset:05d}'; a = training['attempts'][unit]; d = training['done'][unit]
        if (a['request_sha256'] != digest(part) or a['offset'] != offset or a['count'] != len(part)
                or a['candidate_ids'] != [x['candidate_id'] for x in part]
                or a['measurement_exception'] is not False or a['preceding_full_batch_seconds'] != durations[:index]
                or d['raw_sha256'] != sha(p) or d['request_sha256'] != a['request_sha256']
                or d['count'] != len(part) or d['candidate_ids'] != a['candidate_ids']
                or not training['joined']['observed_exited_epoch'] <= a['started_epoch']
                    <= d['finished_epoch'] <= terminal['finished_epoch']):
            raise ValueError('Original endpoint attempt/ack/completion timing differs')
        timing = read(root/'endpoint_timings'/f'{index:03d}.json')
        if not 0 < timing['through_done_ack_seconds'] <= durations[index]:
            raise ValueError('Original endpoint full interval is incomplete')
        for row, item in zip(part, raw):
            if any(t not in vocab for t in item['token_ids']):
                raise ValueError('Unknown token cannot become an incorrect answer')
            stop = first_stop(item['token_ids'], lambda ids: tokenizer.decode(ids,
                skip_special_tokens=False, clean_up_tokenization_spaces=False), 151643, 1024, special)
            stops[stop['stop_reason']] += 1
            decoded.append(dict(problem_id=row['problem_id'], candidate_id=row['candidate_id'],
                source_row_sha256=row['source_row_sha256'], raw_file=str(p.relative_to(root)),
                raw_file_sha256=d['raw_sha256'], stop=stop, backend_finish_reason=item['finish_reason'],
                backend_stop_reason=item['stop_reason']))
    assembled = assemble_math_rows(endpoint, decoded, gold)
    return dict(decoded=decoded, scoring_rows=assembled['rows'], outputs_decoded=500,
        logical_stops=dict(stops), technical_unknown=0, symbolic_scoring_performed=False,
        payload_only=True, full_runtime_lineage_admission_checked=False,
        scientific_G1_admitted=False)
