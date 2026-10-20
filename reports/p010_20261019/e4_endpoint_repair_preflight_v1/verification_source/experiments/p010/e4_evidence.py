"""P010 E4 original full-state verification, including failed endpoint parents.

No new training, model generation or checkpoint rewrite. A preserved final
checkpoint remains a complete training artifact even if later evaluation failed;
its original call and terminal remain failed.
"""
from pathlib import Path
import json
from experiments.p010.common import read,sha,digest
from experiments.p010.training import checked_recipe
from experiments.p010.student_evidence import positive
from experiments.sft_allocation_p008.block_journal import verify_training_blocks
from experiments.sft_allocation_midpoint import checkpoint
from scripts.audit_p009_stage1_nc import check_state
from src.sft_data import encode_row

def verify_training(root, inputs, spec, run, identity, ledger, tokenizer):
    root, inputs = Path(root), Path(inputs)
    rows, encoded, plan, config = [read(inputs/('e4_n'+str(identity['config']['n'])+'_'+n+'.json'))
                                  for n in ('rows', 'encoded', 'plan', 'config')]
    recipe = checked_recipe(config, encoded, plan)
    if config != identity['config'] or digest(rows) != config['rows_sha256']:
        raise ValueError('Exact source rows/configuration differ')
    if [encode_row(row, tokenizer, 2048) for row in rows] != encoded:
        raise ValueError('Independent whole-answer encoding differs')
    return verify_training_after_encoding(root, inputs, spec, run, identity, ledger)


def verify_training_after_encoding(root, inputs, spec, run, identity, ledger):
    """Unattempted state/dose tail after a separately bound encoding prefix."""
    root, inputs = Path(root), Path(inputs)
    encoded, plan, config = [read(inputs/('e4_n'+str(identity['config']['n'])+'_'+n+'.json'))
                             for n in ('encoded', 'plan', 'config')]
    # JSON object keys are strings, including budget_report's integer row indices.
    # Match the original serialization exactly, without dropping any field.
    recipe = json.loads(json.dumps(checked_recipe(config, encoded, plan), allow_nan=False))
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
    blocks = verify_training_blocks(attempts, done, ledger, 'e4/'+run+'/', 1024)
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
    trained = child['result']
    times = positive(child['block_seconds'], 64)
    joined = read(root/'TRAINING_EXIT.json'); merge = read(root/'MERGE_PROOF.json')
    if (trained['updates'] != 1024
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
        maximum = max([43.307480978]+times[:index])
        expected = dict(elapsed=f['elapsed'], future_seconds=1.2*(maximum*(64-index)+6*20.412141323+600),
            old_Qwen_proxy=True, max_block=maximum, remaining_blocks=64-index, allowance_calibrated=False)
        if not 0 <= f['elapsed'] or f['elapsed']+expected['future_seconds'] > 4470:
            raise ValueError('Original E4 training forecast exceeded fixed hard window')
        if f != expected or read(root/'timings'/f'{(index+1)*16:04d}.json') != dict(seconds=times[index], updates=16):
            raise ValueError('Original all-observation timing or forecast differs')
    return dict(targets=targets, processed=processed, train_seconds=times,
                state_sha256=sha(root/'checkpoint_1024/state.pt'), full_state_loaded=True)
