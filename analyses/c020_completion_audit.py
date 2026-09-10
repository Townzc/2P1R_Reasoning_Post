"""Post-hoc saved-stream stop analysis and exact proposed SFT-dose inventory.

CPU/tokenizer only. No new model, server, output rescoring in-place, or training.
Publish the source before generating an immutable output directory.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

from analyses.completion_contract import first_stop, completion_score
from analyses.e014 import audit_predictions
from analyses.e016 import load_release
from analyses.gsm8k_answer_audit import score, summarize
from scripts.audit_family_matching import verified_tokenizer
from src.real_math_engineering import git, load_frozen, dump, write_rows
from src.sft_data import read_jsonl, sha256_file


def audit(tokenizer, out):
    if out.exists():
        raise FileExistsError('Keep C020 outputs immutable')
    if git('status', '--porcelain', '--untracked-files=no') or git('rev-parse', 'HEAD') != git('rev-parse', 'origin/main'):
        raise ValueError('Publish clean source before the immutable audit')
    git('ls-files', '--error-unmatch', 'analyses/c020_completion_audit.py',
        'analyses/completion_contract.py', 'tests/test_completion_contract.py')
    old_cfg, _, _, old_dev, _, _, _ = load_frozen(tokenizer)
    new_cfg, new_dev = load_release(tokenizer)
    inputs = (
        ('e013_base16', 'runs/gsm8k_overfit_e013_r1/base_dev.jsonl', old_dev, old_cfg),
        ('e013_tuned16', 'runs/gsm8k_overfit_e013_r1/final_dev.jsonl', old_dev, old_cfg),
        ('e016_base64', 'runs/gsm8k_capability_e016_r1/base.jsonl', new_dev, new_cfg),
        ('e016_e01564', 'runs/gsm8k_capability_e016_r1/e015.jsonl', new_dev, new_cfg),
    )
    records, summaries = [], {}
    decode = lambda xs: tokenizer.decode(xs, skip_special_tokens=True)
    for name, path, rows, cfg in inputs:
        original = audit_predictions(Path(path), rows, tokenizer, cfg)
        marked, proposed, stops = [], [], []
        for raw in original:
            historical = score(raw, raw['text'], raw['score']['ended_with_eos'], raw['score']['truncated'])
            event = first_stop(raw['generated_ids'], decode, tokenizer.eos_token_id,
                               cfg['max_new_tokens'], tokenizer.all_special_ids)
            result = completion_score(raw, event)
            marked.append(historical); proposed.append(result); stops.append(event)
            records.append({'endpoint': name, 'problem_id': raw['problem_id'],
                'original_generated_tokens': raw['generated_tokens'],
                'original_strict_score': raw['score'], 'original_marked_score': historical,
                'proposed_stop': event, 'saved_prefix_candidate': result,
                'original_text_sha256': hashlib.sha256(raw['text'].encode()).hexdigest()})
        batch = cfg['eval_batch_size']
        summaries[name] = {'n': len(original), 'original_marked': summarize(marked),
            'candidate_stop_reasons': dict(Counter(e['stop_reason'] for e in stops)),
            'saved_prefix_task_answer_correct': sum(r['task_answer_correct'] for r in proposed),
            'original_truncated_with_prior_boundary': sum(
                h['truncated'] and e['stop_reason'] == 'new_problem_boundary' for h, e in zip(marked, stops)),
            'original_generated_tokens': sum(r['generated_tokens'] for r in original),
            'retained_prefix_tokens_including_stop_trigger': sum(e['retained_tokens'] for e in stops),
            'original_batch_maximum_lengths_sum': sum(max(r['generated_tokens'] for r in original[i:i+batch])
                                                     for i in range(0, len(original), batch)),
            'prefix_batch_maximum_lengths_sum': sum(max(e['retained_tokens'] for e in stops[i:i+batch])
                                                   for i in range(0, len(stops), batch))}

    selected_path = Path('reports/real_math_c017_scale_proposal_r1/repeat_rows.jsonl')
    selected = read_jsonl(selected_path)
    assert len(selected) == len({r['problem_id'] for r in selected}) == 253
    order, batches = [], []
    for epoch in range(2):
        ids = list(range(253)); random.Random(17 + epoch).shuffle(ids)
        order.extend(ids)
        batches.extend({'epoch': epoch + 1, 'row_indices': ids[i:i+8],
                        'supervised_tokens': sum(selected[j]['n_supervised'] for j in ids[i:i+8])}
                       for i in range(0, 253, 8))
    assert len(batches) == 64 and set(Counter(order).values()) == {2}
    dose = {'kind': 'review_only_metadata_schedule_not_training_ready', 'nominal_parents': 256,
            'retained_parents': 253, 'unavailable_parents': 3, 'epochs': 2, 'optimizer_updates': 64,
            'batch_size': 8, 'microbatch_size': 1, 'sample_presentations': 506,
            'supervised_tokens': 2 * sum(r['n_supervised'] for r in selected),
            'nonpadding_processed_tokens': 2 * sum(r['n_processed'] for r in selected),
            'right_padded_training_tokens_microbatch1': 2 * sum(r['n_processed'] for r in selected),
            'last_batch_size_each_epoch': 5, 'schedule_uses_full_response_counts': True,
            'selected_rows_sha256': sha256_file(selected_path),
            'limits': 'Uses existing accepted metadata; raw response reconstruction, quality review and token re-verification remain mandatory. Do not interpret this as a checked training release.',
            'updates': batches}
    model_config_path = Path(tokenizer.name_or_path) / 'config.json'
    mc = json.loads(model_config_path.read_text())
    hidden, intermediate = mc['hidden_size'], mc['intermediate_size']
    kv_width = hidden // mc['num_attention_heads'] * mc['num_key_value_heads']
    dimensions = {'q_proj': [hidden, hidden], 'k_proj': [hidden, kv_width],
                  'v_proj': [hidden, kv_width], 'o_proj': [hidden, hidden],
                  'gate_proj': [hidden, intermediate], 'up_proj': [hidden, intermediate],
                  'down_proj': [intermediate, hidden]}
    count = mc['num_hidden_layers'] * 16 * sum(sum(d) for d in dimensions.values())
    dose['proposed_lora_shape_estimate'] = {
        'rank': 16, 'alpha': 32, 'bias': 'none', 'dropout': 0,
        'target_module_dimensions_in_out': dimensions, 'layers': mc['num_hidden_layers'],
        'trainable_adapter_parameters': count, 'float32_tensor_bytes': count * 4,
        'pinned_model_config_sha256': sha256_file(model_config_path),
        'limits': 'Shape arithmetic only; actual PEFT parameter names, count, dtype, optimizer scope and serialized file sizes must be verified before a training release. Metadata and optimizer state are excluded.'}
    report = {'phase': 'C020', 'status': 'post_hoc_saved_stream_diagnostic_only',
              'execution_source_commit': git('rev-parse', 'HEAD'),
              'raw_token_streams_reverified': 160, 'endpoints': summaries,
              'input_hashes': {path: sha256_file(path) for _, path, _, _ in inputs},
              'implementation_hashes': {str(p): sha256_file(p) for p in (
                  Path('analyses/completion_contract.py'), Path('analyses/c020_completion_audit.py'),
                  Path('analyses/gsm8k_answer_audit.py'))},
              'historical_scores_modified': False, 'new_model_calls': 0, 'server_contacted': False,
              'unused_development_parents_opened': 0, 'official_test_evaluation': False,
              'limits': 'Candidate prefix counts are not new GPU results, verified reasoning, benchmark scores, or unbiased confirmation. Batch shape/numerics can change under runtime stopping; token-tail savings do not establish wall-clock speedup.'}
    out.mkdir(parents=True)
    write_rows(out / 'records.jsonl', records)
    dump(out / 'summary.json', report)
    dump(out / 'proposed_training_dose.json', dose)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tokenizer-dir', required=True, type=Path)
    p.add_argument('--out-dir', required=True, type=Path)
    a = p.parse_args()
    tokenizer, _ = verified_tokenizer(a.tokenizer_dir)
    result = audit(tokenizer, a.out_dir)
    print(json.dumps({'status': result['status'], 'streams': 160, 'endpoints': result['endpoints']}, indent=2))


if __name__ == '__main__':
    main()
