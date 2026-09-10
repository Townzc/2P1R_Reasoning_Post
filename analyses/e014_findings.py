"""Post-hoc descriptive tables from audited E014 records; no model inference."""
import argparse
import json
import math
from pathlib import Path

from analyses.e014 import INPUTS, ORIGINAL
from src.real_math_engineering import dump
from src.sft_data import read_jsonl, sha256_file


def score_counts(records):
    return {'rows': len(records),
            'terminated_correct': sum(r['score']['terminated_correct'] for r in records),
            'truncated': sum(r['score']['truncated'] for r in records),
            'reference_exact_match': sum(r['score']['reference_exact_match'] for r in records),
            'generated_tokens': sum(r['generated_tokens'] for r in records)}


def findings(run):
    verification = json.loads((run / 'record_verification.json').read_text())
    if verification['status'] != 'passed_record_consistency_checks':
        raise ValueError('Require completed raw-record audit first')
    cases = json.loads((INPUTS / 'cases.json').read_text())
    old = read_jsonl(ORIGINAL / 'final_train.jsonl')
    replay = read_jsonl(run / 'replay_batch8.jsonl')
    single = read_jsonl(run / 'selected_batch1.jsonl')
    refs = read_jsonl(run / 'reference_tokens.jsonl')
    streams = {'original_batch8': old, 'replay_batch8': replay, 'selected_batch1': single}
    index = {name: {r['problem_id']: r for r in rows} for name, rows in streams.items()}
    rows = []
    for case, ref in zip(cases, refs):
        pid = case['problem_id']
        if ref['problem_id'] != pid:
            raise ValueError('Case/reference order differs')
        misses = [{'target_position': j, 'target_id': target, 'argmax_id': top, 'target_nll': loss}
                  for j, (target, top, loss) in enumerate(zip(ref['target_ids'], ref['argmax_ids'], ref['target_nll']))
                  if target != top]
        eos = next(q for q in ref['queries'] if q['kind'] == 'reference_eos')
        rows.append({'problem_id': pid, 'selection_role': case['selection_role'],
            'streams': {name: {'score': by_id[pid]['score'],
                              'generated_tokens': by_id[pid]['generated_tokens']}
                        for name, by_id in index.items() if pid in by_id},
            'reference_targets': ref['supervised_tokens'], 'reference_nll': ref['reference_nll'],
            'reference_top1_misses': misses, 'reference_eos_target_probability': math.exp(eos['target_log_probability']),
            'reference_eos_query': eos,
            'first_difference_queries': [q for q in ref['queries'] if q['kind'] != 'reference_eos']})
    selected = {c['problem_id'] for c in cases if c['selected_for_batch1']}
    failed = {c['problem_id'] for c in cases if c['selection_role'] == 'failed'}
    controls = selected - failed
    all_queries = [q for r in rows for q in r['first_difference_queries']]
    return {'phase': 'E014_POST_HOC_DESCRIPTIVE_FINDINGS', 'pretrained_model_calls': 0,
        'inputs_sha256': sha256_file(INPUTS / 'manifest.json'),
        'source_sha256': sha256_file(__file__), 'run_manifest_sha256': sha256_file(run / 'run_manifest.json'),
        'record_verification_sha256': sha256_file(run / 'record_verification.json'),
        'all_available_rows': {k: score_counts(v) for k, v in streams.items()},
        'selected_rows': {k: score_counts([r for r in v if r['problem_id'] in selected]) for k, v in streams.items()},
        'original_failed_rows': {k: score_counts([r for r in v if r['problem_id'] in failed]) for k, v in streams.items()},
        'control_rows': {k: score_counts([r for r in v if r['problem_id'] in controls]) for k, v in streams.items()},
        'reference_rows_with_any_top1_miss': sum(bool(r['reference_top1_misses']) for r in rows),
        'reference_top1_misses': sum(len(r['reference_top1_misses']) for r in rows),
        'reference_eos_top1_misses': sum(not r['reference_eos_query']['target_is_argmax'] for r in rows),
        'first_difference_query_count': len(all_queries),
        'first_difference_queries_reference_target_is_argmax': sum(q['target_is_argmax'] for q in all_queries),
        'first_difference_queries_generated_alternative_is_argmax': sum(q['alternative_id'] == q['argmax_id'] for q in all_queries),
        'rows': rows,
        'limitations': ['Post-hoc selected ten-case contrast is not an all32 batch1 evaluation.',
            'Full-reference argmax is not cached generation under the same kernel.',
            'Reference EOS probabilities do not measure termination on diverged generated prefixes.',
            'This descriptive analysis neither changes E013 scoring nor establishes a causal bug.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=Path('runs/gsm8k_generation_e014_r1'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = findings(args.run)
    dump(args.out, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
