"""Independent CPU consistency audit for the isolated E015 terminal-decay run.

This checks preserved records, not the model's original logits or proof validity.
The launcher is imported lazily so synthetic fixtures never load a model.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

from analyses.e014 import audit_predictions, stream_hash, token_hash
from analyses.e014_audit import audit_reference, close, require
from src.real_math_engineering import dump, engineering_gate, summarize
from src.relation_experiment import profile
from src.sft_data import budget_report, read_jsonl, sha256_file

CONFIG = Path('configs/real_math_e015/terminal_decay.json')
RELEASE = Path('configs/real_math_e015/release.json')
INPUTS = Path('reports/real_math_e015_inputs_r1')
ORIGINAL_CHECKPOINT = Path('runs/gsm8k_overfit_e013_r1/checkpoint_manifest.json')
ARTIFACTS = {
    'final_train.jsonl', 'reference_tokens.jsonl', 'train_history.jsonl',
    'throughput.json', 'planned_budget.json', 'actual_budget.json', 'metrics.json',
    'checkpoint_manifest.json', 'phase_timings.json', 'base_reference_nll.json',
}
PHASES = {'base_model_load', 'base_train_nll', 'training', 'final_train_generation',
          'all32_reference_tokens', 'checkpoint_write_and_hash'}
CHECKPOINT_CONFIG = {'model_type': 'qwen2', 'architectures': ['Qwen2ForCausalLM'],
                     'hidden_size': 1536, 'intermediate_size': 8960, 'num_hidden_layers': 28,
                     'num_attention_heads': 12, 'num_key_value_heads': 2,
                     'vocab_size': 151936, 'use_cache': False, 'attention_dropout': 0.0,
                     'tie_word_embeddings': True}


def load_release(tokenizer):
    from analyses.e015 import load_release as read_release
    return read_release(tokenizer)


def finite(value, message, minimum=None):
    require(type(value) in (int, float) and math.isfinite(value), message)
    if minimum is not None:
        require(value >= minimum, message)


def audited_learning_rate(step):
    """Independent, one-based reconstruction of the predeclared intervention."""
    require(type(step) is int and 1 <= step <= 256, 'Invalid optimizer step')
    return 5e-5 if step <= 192 else 5e-5 * (1 + math.cos(math.pi * (step - 192) / 64)) / 2


def audit_all_reference(record, case, vocab_size):
    require(case['selected_for_batch1'] is False, 'E015 has no selected batch1 subpopulation')
    audit_reference(record, case, {}, vocab_size)
    n = len(case['target_ids'])
    keys = ('argmax_log_probability', 'target_minus_argmax_logit', 'target_minus_best_other_logit')
    require(all(len(record[key]) == n for key in keys), 'Missing all-target probability/margin entries')
    for j, target in enumerate(case['target_ids']):
        best = record['argmax_ids'][j]
        target_logp = -record['target_nll'][j]
        best_logp, margin, other_margin = (record[key][j] for key in keys)
        for value in (best_logp, margin, other_margin):
            finite(value, 'Nonfinite target probability or margin')
        require(target_logp <= best_logp <= 0, 'All-target probability ordering differs')
        require(margin <= 0, 'Target-minus-argmax margin must be nonpositive')
        close(margin, target_logp - best_logp, 'All-target argmax margin differs')
        if target == best:
            close(best_logp, target_logp, 'Correct-token probability differs')
            require(margin == 0 and other_margin >= 0, 'Correct-token margin sign differs')
        else:
            require(other_margin <= 0, 'Wrong-token best-other margin sign differs')
            close(other_margin, margin, 'Wrong-token best-other margin differs')
            if margin == 0:
                require(best < target, 'Argmax tie must select the lowest token ID')
        other_logp = target_logp - other_margin
        require(other_logp <= 0, 'Best-other token has invalid log probability')
        require(math.exp(target_logp) + math.exp(other_logp) <= 1 + 1e-5,
                'Two distinct token probabilities exceed one')
    eos = record['queries'][0]
    close(eos['argmax_log_probability'], record['argmax_log_probability'][-1], 'EOS argmax probability differs')
    close(eos['target_minus_argmax_logit'], record['target_minus_argmax_logit'][-1], 'EOS argmax margin differs')
    other = next(item for item in eos['top5'] if item['id'] != case['target_ids'][-1])
    close(record['target_minus_best_other_logit'][-1],
          eos['target_log_probability'] - other['log_probability'], 'EOS best-other margin differs')


def audit_checkpoint(run):
    manifest = json.loads((run / 'checkpoint_manifest.json').read_text())
    require(manifest['kind'] == 'weights_only_not_optimizer_rng_resume', 'Checkpoint kind differs')
    files = manifest['files']
    require(isinstance(files, dict) and files, 'Missing checkpoint file manifest')
    original = json.loads(ORIGINAL_CHECKPOINT.read_text())['files']
    require(set(files) == set(original), 'Checkpoint filename allowlist differs from original model')
    for name, item in files.items():
        require(Path(name).name == name and name not in ('.', '..'), 'Unsafe checkpoint name')
        require(type(item['bytes']) is int and item['bytes'] > 0, 'Invalid checkpoint size')
        require(isinstance(item['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', item['sha256']) is not None,
                'Invalid checkpoint digest')
        if name not in ('config.json', 'generation_config.json'):
            require(item['bytes'] == original[name]['bytes'], 'Checkpoint file size differs from original model')
    folder = run / 'checkpoint_final'
    rehashed = False
    if folder.exists():
        require(folder.is_dir() and not folder.is_symlink(), 'Checkpoint directory must be ordinary')
        require({path.name for path in folder.iterdir()} == set(files), 'Missing or extra checkpoint files')
        for name, item in files.items():
            path = folder / name
            require(path.is_file() and not path.is_symlink(), 'Checkpoint file must be ordinary')
            require(path.stat().st_size == item['bytes'] and stream_hash(path) == item['sha256'],
                    'Checkpoint bytes differ')
        config = json.loads((folder / 'config.json').read_text())
        require(all(config.get(key) == value for key, value in CHECKPOINT_CONFIG.items()),
                'Checkpoint model architecture differs')
        require(config.get('dtype', config.get('torch_dtype')) == 'float32', 'Checkpoint parameter dtype differs')
        rehashed = True
    return {'checkpoint_files': len(files), 'checkpoint_bytes': sum(item['bytes'] for item in files.values()),
            'checkpoint_weights_rehashed': rehashed,
            'independent_checkpoint_backup_verified': False,
            'checkpoint_verification_scope': 'current_run_directory_only; independent backup requires separate evidence'}


def audit(tokenizer, run):
    run = Path(run)
    cfg, old_cfg, train, encoded, schedule, planned, cases = load_release(tokenizer)
    manifest = json.loads((run / 'run_manifest.json').read_text())
    require(manifest['status'] == 'completed' and manifest['phase'] == 'E015' and manifest['config'] == cfg,
            'Incomplete or incorrect E015; preserve partial records separately')
    require(manifest['release_sha256'] == sha256_file(RELEASE), 'Release differs')
    require(manifest['model_execution_performed'] is True and manifest['training_updates'] == 256,
            'Missing original-base training execution record')
    recipe = {'weights': 'fresh_pinned_Qwen2.5_1.5B_base', 'parameter_dtype': 'float32',
              'autocast_dtype': 'bfloat16', 'attention': 'sdpa', 'tf32': False,
              'optimizer': 'AdamW_foreach_false', 'official_test_evaluation': False,
              'development_evaluation': False}
    require(all(manifest.get(key) == value for key, value in recipe.items()), 'Recorded training recipe differs')
    frozen = json.loads((INPUTS / 'manifest.json').read_text())
    require(manifest['source_files_sha256'] == frozen['source_files_sha256'], 'Run source differs from input freeze')
    artifacts = manifest['artifact_sha256']
    require(set(artifacts) == ARTIFACTS, 'Missing or extra completed artifacts')
    for name, digest in artifacts.items():
        require(sha256_file(run / name) == digest, 'Recorded artifact hash differs: ' + name)
    require({path.name for path in run.glob('*.jsonl')} == {
        'final_train.jsonl', 'reference_tokens.jsonl', 'train_history.jsonl'},
        'Unexpected generation or JSONL artifact; no dev/test/baseline decoding is registered')
    require(len(train) == len(encoded) == len(cases) == old_cfg['train_count'], 'Frozen row denominator differs')
    for index, (row, enc, case) in enumerate(zip(train, encoded, cases)):
        prompt, target = enc['input_ids'][:enc['n_prompt']], enc['input_ids'][enc['n_prompt']:]
        require(case['row_index'] == index and case['problem_id'] == row['problem_id'] == enc['problem_id'],
                'Reference case order differs')
        require(case['prompt_ids'] == prompt and case['target_ids'] == target and
                case['prompt_ids_sha256'] == token_hash(prompt) and case['target_ids_sha256'] == token_hash(target),
                'Reference case token identity differs')
        require(target[-1] == tokenizer.eos_token_id and len(target) == enc['n_supervised'],
                'Reference supervision or terminal EOS differs')
    recomputed = json.loads(json.dumps(budget_report(encoded, schedule, old_cfg['microbatch_size'])))
    require(planned == recomputed, 'Frozen token/exposure budget differs')
    for name in ('planned_budget.json', 'actual_budget.json'):
        require(json.loads((run / name).read_text()) == planned, 'Recorded dose differs')
    history = read_jsonl(run / 'train_history.jsonl')
    require(len(history) == len(schedule) == old_cfg['steps'] == 256 and manifest['steps_completed'] == 256,
            'Incomplete optimizer trajectory')
    for step, (record, indices, counts) in enumerate(zip(history, schedule, planned['per_update']), 1):
        require(type(record['step']) is int and record['step'] == step and record['row_indices'] == indices,
                'Optimizer step or row order differs')
        require(all(type(index) is int for index in record['row_indices']), 'Noninteger row index')
        for key in ('supervised_tokens', 'processed_tokens'):
            require(type(record[key]) is int and record[key] == counts[key], 'Per-update token dose differs')
        finite(record['actual_learning_rate'], 'Invalid recorded optimizer learning rate', 0)
        require(math.isclose(record['actual_learning_rate'], audited_learning_rate(step), rel_tol=1e-12, abs_tol=1e-15),
                'Actual optimizer learning-rate schedule differs')
        for key in ('response_nll', 'grad_norm', 'peak_allocated_mib', 'peak_reserved_mib'):
            finite(record[key], 'Invalid training ' + key, 0)
        finite(record['seconds'], 'Invalid update duration', 0)
        require(record['seconds'] > 0, 'Update duration must be positive')
        require(record['peak_reserved_mib'] >= record['peak_allocated_mib'], 'Reserved memory below allocated memory')
    predictions = audit_predictions(run / 'final_train.jsonl', train, tokenizer, old_cfg)
    references = read_jsonl(run / 'reference_tokens.jsonl')
    require(len(references) == len(cases), 'Missing reference rows')
    for record, case in zip(references, cases):
        audit_all_reference(record, case, cfg['model_vocab_size'])
    stats, throughput = summarize(predictions), profile(history, old_cfg)
    require(json.loads((run / 'throughput.json').read_text()) == throughput, 'Recorded throughput differs')
    count = sum(len(case['target_ids']) for case in cases)
    loss = math.fsum(math.fsum(record['target_nll']) for record in references)
    result = json.loads((run / 'metrics.json').read_text())
    require(result['steps'] == 256 and result['train'] == stats and result['throughput'] == throughput,
            'Aggregate training metrics differ')
    nll = result['train_reference_nll']
    require(nll['supervised_tokens'] == count and nll['reference_count'] == len(train), 'Aggregate NLL denominator differs')
    close(nll['response_loss_sum'], loss, 'Aggregate reference loss differs')
    close(nll['nll'], loss / count, 'Aggregate reference NLL differs')
    baseline = json.loads((run / 'base_reference_nll.json').read_text())
    require(baseline['supervised_tokens'] == count and baseline['reference_count'] == len(train),
            'Baseline reference denominator differs')
    finite(baseline['response_loss_sum'], 'Invalid baseline reference loss', 0)
    close(baseline['nll'], baseline['response_loss_sum'] / count, 'Baseline reference NLL differs')
    require(result['reference_top1_correct'] == sum(record['target_top1_correct'] for record in references) and
            result['reference_eos_top1_correct'] == sum(record['eos_is_argmax'] for record in references),
            'Aggregate target/EOS top-one counts differ')
    gate = engineering_gate(old_cfg, len(history), throughput, stats, loss / count)
    require(result['engineering_gate'] == gate, 'Original engineering gate differs')
    lr = result['lr_accounting']
    require(lr['nonzero_lr_updates'] == sum(record['actual_learning_rate'] > 0 for record in history) == 255,
            'Nonzero-LR update accounting differs')
    require(math.isclose(lr['summed_lr'], math.fsum(record['actual_learning_rate'] for record in history),
                        rel_tol=1e-12, abs_tol=1e-15), 'Integrated learning rate differs')
    checkpoint = audit_checkpoint(run)
    timings = json.loads((run / 'phase_timings.json').read_text())
    phases = timings['completed_phases_seconds']
    require(set(phases) == PHASES, 'Missing or extra completed phase profile')
    for duration in phases.values():
        finite(duration, 'Invalid phase duration', 0)
    close(phases['training'], math.fsum(record['seconds'] for record in history), 'Training phase duration differs')
    wall = timings.get('process_wall_seconds', timings.get('wall_seconds'))
    finite(wall, 'Invalid process wall duration', 0)
    require(math.fsum(phases.values()) <= wall + 1e-6, 'Completed phase time exceeds wall time')
    receipt = json.loads((run / 'resource_receipt.json').read_text())
    require(receipt['run_id'] == cfg['run_id'] and receipt['status'] == 'completed' and receipt['exit_code'] == 0,
            'Incomplete resource receipt')
    finite(receipt['elapsed_seconds'], 'Invalid guard wall duration', 0)
    require(receipt['max_seconds'] == cfg['max_seconds'] and
            type(receipt['charged_seconds']) is int and receipt['charged_seconds'] == math.ceil(receipt['elapsed_seconds']) and
            0 < receipt['charged_seconds'] <= cfg['max_seconds'] + cfg['guard_seconds'], 'Resource charge differs')
    require(wall <= receipt['elapsed_seconds'] + 1e-6, 'Worker wall duration exceeds guarded process duration')
    return {'status': 'passed_record_consistency_checks', 'phase': 'E015_CPU_OUTPUT_AUDIT',
            'raw_generation_streams_checked': len(predictions), 'reference_rows_checked': len(references),
            'reference_targets_checked': count, 'updates_checked': len(history), 'engineering_gate': gate,
            'resource_receipt_sha256': sha256_file(run / 'resource_receipt.json'),
            'run_manifest_sha256': sha256_file(run / 'run_manifest.json'), **checkpoint,
            'model_rerun': False, 'logits_independently_recomputed': False,
            'proof_correctness_verified': False, 'scientific_launch_authorized': False,
            'rental_invoice_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer-dir', required=True)
    parser.add_argument('--run-dir')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    from scripts.audit_family_matching import verified_tokenizer
    tokenizer, _ = verified_tokenizer(Path(args.tokenizer_dir))
    cfg = json.loads(CONFIG.read_text())
    result = audit(tokenizer, Path(args.run_dir) if args.run_dir else Path('runs') / cfg['run_id'])
    dump(args.out, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
