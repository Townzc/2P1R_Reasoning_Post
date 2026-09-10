"""Independent CPU consistency audit of E014 raw outputs (no model rerun)."""
import argparse
import json
import math
from pathlib import Path

from analyses.e014 import CONFIG, INPUTS, ORIGINAL, RELEASE, load_release, token_hash
from scripts.audit_family_matching import verified_tokenizer
from scripts.audit_real_math_engineering_outputs import audit_predictions
from src.real_math_engineering import dump
from src.sft_data import read_jsonl, sha256_file


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(a, b, message, tol=1e-5):
    require(isinstance(a, (int, float)) and not isinstance(a, bool) and math.isfinite(a)
            and math.isclose(a, b, rel_tol=1e-6, abs_tol=tol), message)


def prefix_length(a, b):
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


def checked_difference(record, a, b):
    j = prefix_length(a, b)
    require(record == {'identical': a == b, 'common_prefix_tokens': j,
                      'a_token': a[j] if j < len(a) else None,
                      'b_token': b[j] if j < len(b) else None}, 'Raw comparison differs')


def audit_reference(record, case, streams, vocab_size):
    target, prompt = case['target_ids'], case['prompt_ids']
    require(record['problem_id'] == case['problem_id'] and record['target_ids'] == target,
            'Reference row/target identity differs')
    require(record['prompt_ids_sha256'] == token_hash(prompt), 'Prompt hash differs')
    losses, best = record['target_nll'], record['argmax_ids']
    require(len(losses) == len(best) == len(target) == record['supervised_tokens'], 'Target denominator differs')
    require(all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in losses), 'Invalid token NLL')
    require(all(type(x) is int and 0 <= x < vocab_size for x in best), 'Invalid argmax token')
    close(record['loss_sum'], math.fsum(losses), 'Row loss sum differs')
    close(record['reference_nll'], math.fsum(losses) / len(target), 'Row NLL differs')
    require(record['target_top1_correct'] == sum(x == y for x, y in zip(target, best)), 'Top-one count differs')
    require(record['eos_is_argmax'] == (target[-1] == best[-1]), 'EOS argmax differs')
    wanted = [('reference_eos', len(target) - 1, None)]
    if case['selected_for_batch1']:
        for name, ids in streams.items():
            j = prefix_length(target, ids)
            if j < len(target) and j < len(ids):
                wanted.append((name + '_first_difference', j, ids[j]))
    events = record['queries']
    require(len(events) == len(wanted), 'Missing/extra reference queries')
    for event, (kind, j, alternative) in zip(events, wanted):
        require((event['kind'], event['target_position'], event['alternative_id']) == (kind, j, alternative),
                'Divergence query differs')
        require(event['target_id'] == target[j] and event['argmax_id'] == best[j], 'Query tokens differ')
        require(event['causal_logit_index'] == len(prompt) + j - 1 and
                event['context_token_count'] == len(prompt) + j and
                event['context_ids_sha256'] == token_hash(prompt + target[:j]), 'Causal shift/context differs')
        require(event['conditioning'] == 'reference_prefix_full_forward_use_cache_false', 'Conditioning differs')
        close(event['target_log_probability'], -losses[j], 'Query/token log probability differs')
        require(type(event['target_rank_strict_greater']) is int and
                1 <= event['target_rank_strict_greater'] <= vocab_size, 'Invalid target rank')
        require(event['target_is_argmax'] == (target[j] == best[j]), 'Query top-one flag differs')
        if event['target_is_argmax']:
            require(event['target_rank_strict_greater'] == 1, 'Argmax rank differs')
        require(math.isfinite(event['argmax_log_probability']) and
                event['target_log_probability'] <= event['argmax_log_probability'] <= 0,
                'Invalid top-one probability ordering')
        close(event['target_minus_argmax_logit'], event['target_log_probability'] - event['argmax_log_probability'],
              'Target/argmax margin differs')
        top = event['top5']
        require(len(top) == min(5, vocab_size) and len({x['id'] for x in top}) == len(top), 'Invalid top-five IDs')
        require(all(type(x['id']) is int and 0 <= x['id'] < vocab_size and
                    math.isfinite(x['log_probability']) and x['log_probability'] <= 0 for x in top),
                'Invalid top-five values')
        require(all(x['log_probability'] >= y['log_probability'] for x, y in zip(top, top[1:])),
                'Top-five ordering differs')
        close(top[0]['log_probability'], event['argmax_log_probability'], 'Top-five maximum differs')
        if alternative is None:
            require(event['alternative_log_probability'] is None and event['target_minus_alternative_logit'] is None,
                    'EOS-only query has an alternative')
        else:
            require(math.isfinite(event['alternative_log_probability']) and event['alternative_log_probability'] <= 0,
                    'Invalid alternative probability')
            close(event['target_minus_alternative_logit'],
                  event['target_log_probability'] - event['alternative_log_probability'], 'Alternative margin differs')


def audit(tokenizer, run):
    cfg, state = load_release(tokenizer)
    old_cfg, train, _, _, original, cases = state
    manifest = json.loads((run / 'run_manifest.json').read_text())
    require(manifest['status'] == 'completed' and manifest['phase'] == 'E014' and manifest['config'] == cfg,
            'Incomplete/incorrect E014; preserve partial records separately')
    require(manifest['release_sha256'] == sha256_file(RELEASE) and manifest['training_updates'] == 0,
            'Release or training status differs')
    require(manifest['model_execution_performed'] is True, 'No recorded pretrained model execution')
    frozen = json.loads((INPUTS / 'manifest.json').read_text())
    require(manifest['source_files_sha256'] == frozen['source_files_sha256'], 'Run source differs from freeze')
    require(manifest['checkpoint']['all_files_verified'] is True and
            manifest['checkpoint']['manifest_sha256'] == cfg['checkpoint_manifest_sha256'], 'Checkpoint provenance differs')
    require(manifest['effective_generation_config'] ==
            json.loads((INPUTS / 'cpu_evidence.json').read_text())['effective_generation_config'], 'Effective decoding differs')
    artifacts = manifest['artifact_sha256']
    require(set(artifacts) == {'replay_batch8.jsonl', 'selected_batch1.jsonl', 'reference_tokens.jsonl',
                              'diagnosis.json', 'phase_timings.json'}, 'Missing/extra completed artifacts')
    for name, digest in artifacts.items():
        require(sha256_file(run / name) == digest, 'Recorded artifact hash differs: ' + name)
    replay = audit_predictions(run / 'replay_batch8.jsonl', train, tokenizer, old_cfg)
    selected = [r for r, c in zip(train, cases) if c['selected_for_batch1']]
    singles = audit_predictions(run / 'selected_batch1.jsonl', selected, tokenizer, old_cfg)
    by_replay = {p['problem_id']: p for p in replay}
    by_single = {p['problem_id']: p for p in singles}
    references = read_jsonl(run / 'reference_tokens.jsonl')
    require(len(references) == len(cases), 'Missing reference rows')
    vocab_size = 151936  # Original pinned Qwen2.5-1.5B model vocabulary, including unused IDs.
    for case, record in zip(cases, references):
        streams = {'original_batch8': case['original_generated_ids'],
                   'replay_batch8': by_replay[case['problem_id']]['generated_ids']}
        if case['selected_for_batch1']:
            streams['selected_batch1'] = by_single[case['problem_id']]['generated_ids']
        audit_reference(record, case, streams, vocab_size)
    result = json.loads((run / 'diagnosis.json').read_text())
    require(len(result['comparisons']) == 32, 'Comparison denominator differs')
    matches, changed = 0, 0
    for row, case in zip(result['comparisons'], cases):
        pid = case['problem_id']
        require(row['problem_id'] == pid and row['selection_role'] == case['selection_role'], 'Comparison identity differs')
        r = by_replay[pid]
        checked_difference(row['original_vs_replay'], case['original_generated_ids'], r['generated_ids'])
        matches += case['original_generated_ids'] == r['generated_ids']
        if case['selected_for_batch1']:
            s = by_single[pid]
            checked_difference(row['replay_vs_single'], r['generated_ids'], s['generated_ids'])
            require(row['replay_score'] == r['score'] and row['single_score'] == s['score'], 'Comparison score differs')
            changed += r['generated_ids'] != s['generated_ids']
    expected = {'original_vs_replay_exact': matches, 'replay_denominator': 32,
        'batch_contrast_interpretable': matches == 32, 'selected_batch_sensitive_count': changed,
        'selected_denominator': 10, 'training_updates': 0, 'scientific_launch_authorized': False,
        'selected_single_terminated_correct': sum(p['score']['terminated_correct'] for p in singles),
        'reference_supervised_tokens': sum(len(r['target_ids']) for r in references),
        'reference_top1_correct': sum(r['target_top1_correct'] for r in references),
        'reference_eos_top1_correct': sum(r['eos_is_argmax'] for r in references)}
    require(all(result[k] == v for k, v in expected.items()), 'Aggregate diagnostic counts differ')
    total = math.fsum(math.fsum(r['target_nll']) for r in references)
    close(result['reference_loss_sum'], total, 'Aggregate loss differs')
    close(result['reference_nll'], total / expected['reference_supervised_tokens'], 'Aggregate NLL differs')
    prior = json.loads((ORIGINAL / 'metrics.json').read_text())['train_reference_nll']['nll']
    close(result['absolute_nll_difference_from_e013'], abs(result['reference_nll'] - prior), 'Historical NLL difference differs')
    require(result['reference_nll_agrees_with_e013_within_tolerance'] ==
            (abs(result['reference_nll'] - prior) <= cfg['nll_agreement_abs_tolerance']), 'NLL agreement flag differs')
    timings = json.loads((run / 'phase_timings.json').read_text())
    require(set(timings['completed_phases_seconds']) == {'checkpoint_load', 'original_batch8_replay',
            'selected_batch1', 'all32_reference_tokens'}, 'Incomplete phase profile')
    require(all(math.isfinite(t) and t > 0 for t in timings['completed_phases_seconds'].values()), 'Invalid phase duration')
    require(sum(timings['completed_phases_seconds'].values()) <= timings['wall_seconds'], 'Phase time exceeds wall')
    receipt = json.loads((run / 'resource_receipt.json').read_text())
    require(receipt['run_id'] == cfg['run_id'] and receipt['status'] == 'completed' and receipt['exit_code'] == 0,
            'Incomplete resource receipt')
    require(receipt['max_seconds'] == cfg['max_seconds'] and
            receipt['charged_seconds'] == math.ceil(receipt['elapsed_seconds']) and
            0 < receipt['charged_seconds'] <= cfg['max_seconds'] + cfg['guard_seconds'], 'Resource charge differs')
    return {'status': 'passed_record_consistency_checks', 'phase': 'E014_CPU_OUTPUT_AUDIT',
        'raw_generation_streams_checked': 42, 'reference_rows_checked': 32,
        'reference_targets_checked': expected['reference_supervised_tokens'],
        'resource_receipt_sha256': sha256_file(run / 'resource_receipt.json'),
        'run_manifest_sha256': sha256_file(run / 'run_manifest.json'),
        'model_rerun': False, 'logits_independently_recomputed': False,
        'proof_correctness_verified': False, 'scientific_launch_authorized': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    if Path(a.out).exists():
        raise FileExistsError('Audit output is immutable')
    tokenizer, _ = verified_tokenizer(Path(a.tokenizer_dir))
    cfg = json.loads(CONFIG.read_text())
    result = audit(tokenizer, Path('runs') / cfg['run_id'])
    dump(a.out, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
