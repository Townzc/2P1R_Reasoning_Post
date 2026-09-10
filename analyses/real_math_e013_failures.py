"""Post-hoc CPU description of E013 outputs; frozen scores are never changed."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from scripts.audit_family_matching import verified_tokenizer
from src.real_math_engineering import load_frozen, dump
from src.sft_data import read_jsonl, sha256_file


def common_prefix(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def describe(pred, reference, tokenizer):
    ids = pred['generated_ids']
    ngrams = Counter(tuple(ids[i:i+16]) for i in range(max(0, len(ids)-15)))
    repeated_digits = [len(m[0]) for m in re.finditer(r'(\d)\1{7,}', pred['text'])]
    result = {'problem_id': pred['problem_id'], 'reference_answer': pred['answer'],
        'extracted_answer': pred['score']['extracted_answer'], 'registered_score': pred['score'],
        'generated_tokens': len(ids), 'max_exact_16gram_count': max(ngrams.values(), default=0),
        'longest_repeated_digit_run': max(repeated_digits, default=0)}
    if pred['score']['terminated_correct']:
        category = 'terminated_correct'
    elif pred['score']['truncated'] and pred['score']['parse_status'] == 'missing_final_marker':
        category = 'truncated_without_final_marker'
    elif pred['score']['parse_status'] == 'parsed':
        category = 'wrong_numeric_final'
    else:
        category = 'other_format_or_termination_failure'
    result['category'] = category
    if reference is not None:
        target = reference['input_ids'][reference['n_prompt']:]
        shared = common_prefix(ids, target)
        result.update(reference_supervised_tokens=len(target), exact_prefix_tokens=shared,
            reference_at_first_difference=tokenizer.decode(target[shared:shared+18], skip_special_tokens=False),
            generated_at_first_difference=tokenizer.decode(ids[shared:shared+18], skip_special_tokens=False))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    if Path(a.out).exists():
        raise FileExistsError('Post-hoc analysis output is immutable')
    tokenizer, _ = verified_tokenizer(Path(a.tokenizer_dir))
    cfg, _, train, dev, encoded, _, _ = load_frozen(tokenizer)
    run = Path('runs')/cfg['run_id']
    verification = json.loads((run/'record_verification.json').read_text())
    if verification['status'] != 'passed_record_consistency_checks':
        raise ValueError('Verify original records before interpreting failures')
    metrics = json.loads((run/'metrics.json').read_text())
    table = {}
    for split in ('base_dev', 'final_train', 'final_dev'):
        rows = read_jsonl(run/f'{split}.jsonl')
        references = encoded if split == 'final_train' else [None]*len(dev)
        table[split] = [describe(row, ref, tokenizer) for row, ref in zip(rows, references)]
    counts = {k: dict(Counter(r['category'] for r in rows)) for k, rows in table.items()}
    if counts['final_train'] != {'truncated_without_final_marker': 5, 'terminated_correct': 24, 'wrong_numeric_final': 3}:
        raise ValueError('Unexpected frozen E013 failure accounting')
    failures = [r for r in table['final_train'] if r['category'] != 'terminated_correct']
    dump(a.out, {'phase': 'E013_POSTHOC_CPU_ANALYSIS', 'source_commit_of_model_run':
        json.loads((run/'run_manifest.json').read_text())['source_commit'],
        'analysis_source_sha256': sha256_file(__file__), 'input_files_sha256':
        {p.name: sha256_file(p) for p in [run/'base_dev.jsonl', run/'final_train.jsonl', run/'final_dev.jsonl', run/'metrics.json', run/'record_verification.json']},
        'registered_metrics_unchanged': True, 'model_calls': 0, 'gpu_seconds_added': 0,
        'failure_category_counts': counts, 'failed_training_rows': failures, 'all_rows': table,
        'gate': metrics['engineering_gate'],
        'interpretation': [
            'Five training completions have no final marker and hit the 768-token cap. Three emit a parsed but incorrect final number. These are not merely equivalent-answer formatting rejections.',
            'The base development score is format-limited: 15 missing explicit markers and one unresolved marked suffix. It is not an estimate of zero underlying mathematical ability.',
            'Final development has 11 parsed wrong numeric answers and five truncated completions; no generalization claim follows from n=16.',
            'Reference NLL is teacher-forced and token-averaged. It did not predict stable free generation in this run.',
            'Repeated n-grams, repeated digits and exact-prefix lengths are descriptive diagnostics, not independent proof validation or an established causal explanation.',
            'No generation cap, frozen scorer, checkpoint, training dose or example selection is changed after observing outputs.'
        ]})
    print(json.dumps({'counts': counts, 'failed_training_ids': [r['problem_id'] for r in failures]}))


if __name__ == '__main__':
    main()
