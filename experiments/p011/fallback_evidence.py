"""Prepared B full-state/raw oracle; outer receipt/input/source/window required.

Original P010 scientific checks are retained. Only the new B identity and
complete-cycle numerical policy are substituted. No old result is reanalyzed.
"""
from collections import Counter
import json
import math
from pathlib import Path

from analyses.completion_contract import first_stop
from experiments.p010.common import read, sha, digest
from experiments.p010.student_contract import evaluation_jobs, sampling
from experiments.p011.fallback_numeric import forecast
from experiments.p011.fallback_training import checked_recipe
from experiments.sft_allocation_p008.block_journal import verify_training_blocks
from experiments.sft_allocation_midpoint import checkpoint
from experiments.learning_regime_p009.high_throughput_v1 import validate_observed_engine
from scripts.audit_p009_stage1_nc import check_state
from src.sft_data import encode_row

GOLD_SHA256 = '132582ca829ff11820b9d739a14c6e3ce383aacb51dba50e406acd2d27d1b95d'
SCORER_SHA256 = 'd310d7e61b049cdd750f14c65f0ad12551ee45b7eeb0913646a6447a4cbc36fe'


def positive(values, count):
    if (not isinstance(values, list) or len(values) != count
            or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in values)):
        raise ValueError('All finite positive original completion intervals required')
    return values


def expected_record_keys(run):
    prefix = 'fallback/student/'+run+'/'
    units = [f'training_block_{i:04d}_{i+15:04d}' for i in range(1, 1025, 16)]
    units += ['terminal_merge']
    keys = [prefix+'claim', prefix+'terminal']
    keys += [prefix+kind+'/'+unit for unit in units for kind in ('unit', 'done')]
    keys += [prefix+kind+'/'+job[0]+f'/{offset:04d}'
             for job in evaluation_jobs() for offset in (0, 256)
             for kind in ('eval', 'eval_done')]
    return keys


def verify_training(root, inputs, policy, run, identity, ledger, tokenizer):
    root, inputs = Path(root), Path(inputs)
    rows, encoded, plan, config = [read(inputs/run/(n+'.json'))
                                  for n in ('rows', 'encoded', 'plan', 'config')]
    recipe = json.loads(json.dumps(checked_recipe(config, encoded, plan), allow_nan=False))
    if config != identity['config'] or digest(rows) != config['training_rows_sha256']:
        raise ValueError('Exact source rows/configuration differ')
    if [encode_row(row, tokenizer, 2048) for row in rows] != encoded:
        raise ValueError('Independent whole-answer encoding differs')
    stored = read(root/'recipe.json')
    if (stored['identity'] != identity or stored['recipe'] != recipe
            or stored['schedule'] != plan['updates'] or stored['lrs'] != plan['lrs']
            or stored['row_path_ids'] != plan['row_path_ids']
            or stored['row_exposures'] != plan['row_exposures']
            or stored['targets'] != 2097148 or stored['seed'] != config['seed']):
        raise ValueError('Full original recipe, exposure or trajectory differs')
    attempts = {p.stem: read(p) for p in (root/'intents').glob('*.json')}
    done = {p.stem: read(p) for p in (root/'completed').glob('*.json')}
    if set(attempts) != set(done):
        raise ValueError('Partial/unknown training unit')
    blocks = verify_training_blocks(attempts, done, ledger, 'fallback/student/'+run+'/', 1024)
    wanted = {f'update_{i:04d}' for i in range(1, 1025)} | blocks | {'terminal_merge'}
    if set(done) != wanted:
        raise ValueError('Extra or missing original training units')
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
            raise ValueError('Actual per-update full-answer dose differs')
    if targets != 2097148:
        raise ValueError('Original full target dose differs')
    state = checkpoint.load(root/'checkpoint_1024', identity)
    check_state(state, identity, plan, targets, processed)
    child = read(root/'TRAINING_PROCESS_RESULT.json')
    trained = child['result']; result = read(root/'RESULT.json')
    times = positive(child['block_seconds'], 64)
    if (child.get('complete_block_commits_and_remote_ack_included') is not True
            or child.get('checkpoint_merge_and_final_proof_outside_cycles') is not True):
        raise ValueError('Original complete block timing scope required')
    joined = read(root/'TRAINING_EXIT.json'); merge = read(root/'MERGE_PROOF.json')
    if (result['training'] != trained or trained['updates'] != 1024
            or trained['targets'] != targets or trained['processed_tokens'] != processed
            or trained['checkpoint'] != read(root/'checkpoint_1024/manifest.json')
            or trained['requested_seed'] != config['seed']
            or trained['evaluation_performed'] is not False
            or trained['no_intermediate_checkpoint_selection'] is not True
            or joined['pid'] != child['pid'] or joined['exitcode'] != 0
            or joined['joined_before_vllm'] is not True
            or merge['checkpoint'] != trained['checkpoint']
            or merge['merge_dtype'] != 'float32' or merge['saved_dtype'] != 'bfloat16'
            or merge['optimizer_updates_after_terminal_save'] != 0
            or merge['complete_optimizer_rng_preserved'] is not True
            or merge['terminal_state_saved_before_merge'] is not True
            or merge['final_checkpoint_only'] is not True
            or trained['merge_proof_sha256'] != digest(merge)
            or done['terminal_merge']['proof_sha256'] != digest(merge)):
        raise ValueError('Original terminal state, process exit or merge proof differs')
    env = read(root/'training_environment.json')
    if (env['deterministic_algorithms'] is not True or env['allow_tf32'] is not False
            or env['training_parameters'] != 'float32' or env['forward_autocast'] != 'bfloat16'
            or 'H100' not in env['gpu'] or env['cuda'] != '12.8'):
        raise ValueError('Original deterministic GPU environment differs')
    if {p.stem for p in (root/'forecasts').glob('*.json')} != {f'{i:04d}' for i in range(0, 1024, 16)}:
        raise ValueError('All64 original forecasts required')
    for index in range(64):
        f = read(root/'forecasts'/f'{index*16:04d}.json')
        expected = forecast(policy, 64-index, 10, times[:index], [],
                            policy['worker_start_epoch']+f['elapsed_seconds'])
        if f != expected:
            raise ValueError('Original all-observation timing or forecast differs')
    return dict(targets=targets, processed=processed, train_seconds=times,
                state_sha256=sha(root/'checkpoint_1024/state.pt'), full_state_loaded=True)


def decode_record(row, item, job, tokenizer, mapped, special, vocab_size):
    if (item['candidate_id'] != row['candidate_id'] or item['problem_id'] != row['problem_id']
            or item['source_row_sha256'] != row['source_row_sha256']
            or item['prompt_token_ids'] != row['input_ids'] or item['sampling'] != sampling(job)
            or item['output_count'] != 1 or not isinstance(item['backend_text'], str)):
        raise ValueError('Original endpoint request/response identity differs')
    ids = item['token_ids']
    if not ids or len(ids) > 1024 or any(type(t) is not int or not 0 <= t < vocab_size for t in ids):
        raise ValueError('Invalid original model-vocabulary token stream')
    unknown = sorted(set(ids)-mapped)
    if unknown and (len(ids) != 1024 or item['finish_reason'] != 'length'
                    or any(t in (151643, 151645) for t in ids)):
        raise ValueError('Unmapped model token outside preserved no-EOS length cap')
    # Native EOS at the last token can have backend reason=length. The original
    # logical first_stop contract, not that metadata precedence, decides the stop.
    stop = first_stop(ids, lambda x: tokenizer.decode(x, skip_special_tokens=False,
        clean_up_tokenization_spaces=False), 151643, 1024, special)
    return stop, unknown


def verify_endpoint(root, endpoint, policy, run, ledger, training, tokenizer, gold, vocab_size):
    root = Path(root)
    if (len(endpoint) != 500 or len({r['candidate_id'] for r in endpoint}) != 500
            or len({r['problem_id'] for r in endpoint}) != 500
            or set(gold) != {r['problem_id'] for r in endpoint}):
        raise ValueError('Exactly the frozen500 original endpoint questions required')
    validate_observed_engine(read(root/'ENGINE.json'))
    result = read(root/'RESULT.json'); labels = [x[0] for x in evaluation_jobs()]
    if (result['raw_endpoint_count'] != 2500 or result['unique_questions'] != 500
            or result['evaluations'] != labels
            or result.get('endpoint_complete_cycles_include_three_commits_and_ack') is not True
            or result.get('symbolic_scoring_performed') is not False):
        raise ValueError('All five complete500-question endpoints required')
    times = positive(result['eval_batch_seconds'], 10)
    expected_files = {job[0]+f'/{offset:04d}.json' for job in evaluation_jobs() for offset in (0, 256)}
    for directory in ('raw', 'eval_intents', 'eval_acks', 'eval_forecasts'):
        if {p.relative_to(root/directory).as_posix() for p in (root/directory).rglob('*.json')} != expected_files:
            raise ValueError('Missing or extra original evaluation batch: '+directory)
    mapped = set(tokenizer.get_vocab().values()); special = tuple(tokenizer.all_special_ids)
    decoded = []; scoring = []; stops = {label: Counter() for label in labels}; index = 0
    for job in evaluation_jobs():
        for offset in (0, 256):
            unit = job[0]+f'/{offset:04d}'; part = endpoint[offset:offset+256]
            path = root/'raw'/(unit+'.json'); raw = read(path); raw_file_sha256 = sha(path)
            intent = read(root/'eval_intents'/(unit+'.json')); ack = read(root/'eval_acks'/(unit+'.json'))
            if (len(raw) != len(part) or intent['rows'] != part
                    or intent['sampling'] != [sampling(job) for _ in part] or intent['evaluation'] != job[0]
                    or ack != dict(count=len(part), raw_sha256=digest(raw), evaluation=job[0])
                    or ledger['fallback/student/'+run+'/eval/'+unit] != intent
                    or ledger['fallback/student/'+run+'/eval_done/'+unit] != ack):
                raise ValueError('Original full endpoint intent/ack/cloud binding differs')
            f = read(root/'eval_forecasts'/(unit+'.json'))
            if f != forecast(policy, 0, 10-index, training['train_seconds'], times[:index],
                             policy['worker_start_epoch']+f['elapsed_seconds']):
                raise ValueError('Original all-batch forecast differs')
            for row, item in zip(part, raw):
                stop, unknown = decode_record(row, item, job, tokenizer, mapped, special, vocab_size)
                entry = dict(evaluation=job[0], problem_id=row['problem_id'], candidate_id=row['candidate_id'],
                    source_row_sha256=row['source_row_sha256'], raw_file=path.relative_to(root).as_posix(),
                    raw_file_sha256=raw_file_sha256, raw_record_sha256=digest(item), stop=stop,
                    backend_finish_reason=item['finish_reason'], backend_stop_reason=item['stop_reason'],
                    unmapped_model_token_ids=unknown)
                answer = gold[row['problem_id']]['answer']
                if not isinstance(answer, str) or not answer.strip():
                    raise ValueError('Unsupported gold is not an incorrect answer')
                decoded.append(entry); stops[job[0]][stop['stop_reason']] += 1
                scoring.append(dict(id=job[0]+'::'+row['problem_id'], evaluation=job[0],
                    problem_id=row['problem_id'], gold=answer, answer_segment=stop['answer_segment'],
                    stop_reason=stop['stop_reason'], original_gold_row_sha256=digest(gold[row['problem_id']]),
                    original_decoded_record_sha256=digest(entry)))
            index += 1
    return dict(decoded=decoded, scoring_rows=scoring,
                logical_stops={k: dict(v) for k, v in stops.items()}, outputs_decoded=2500,
                technical_unknown=0, symbolic_scoring_performed=False)
