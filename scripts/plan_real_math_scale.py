"""Construct review-only, whole-response schedules for a small allocation study.

Every selected pair is exposed q or q+1 times. A seeded exact subset supplies
the remainder of the total response-token budget. Updates contain whole rows.
This performs no training and makes no GPU-throughput or performance claim.
"""
import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
import json
from pathlib import Path
import random

from scripts.prepare_real_math_audit import write_json, write_jsonl
from src.sft_data import read_jsonl


def exact_remainder(lengths, target, seed):
    if target == 0:
        return []
    order = list(range(len(lengths)))
    random.Random(seed).shuffle(order)
    reachable, stages = 1, []
    mask = (1 << (target+1))-1
    for i in order:
        stages.append((i, reachable))
        reachable |= (reachable << lengths[i]) & mask
        if (reachable >> target) & 1:
            break
    if not ((reachable >> target) & 1):
        raise ValueError('No balanced exact whole-response remainder; retain failure')
    chosen, left = [], target
    for i, before in reversed(stages):
        if (before >> left) & 1:
            continue
        chosen.append(i)
        left -= lengths[i]
    if left != 0:
        raise AssertionError('Subset reconstruction failed')
    return chosen


def whole_response_schedule(lengths, budget, updates, seed):
    if not lengths or min(lengths) <= 0 or updates <= 0:
        raise ValueError('Positive rows, lengths and update count required')
    q, remainder = divmod(budget, sum(lengths))
    if q < 1:
        raise ValueError('Budget cannot expose every acquired usable pair at least once')
    extra = exact_remainder(lengths, remainder, seed)
    stream = list(range(len(lengths)))*q + extra
    if len(stream) < updates:
        raise ValueError('Not enough whole examples for the requested updates')
    random.Random(seed+1).shuffle(stream)
    prefix = [0]
    for i in stream:
        prefix.append(prefix[-1]+lengths[i])
    if prefix[-1] != budget:
        raise AssertionError('Total supervised tokens differ')
    cuts = [0]
    for step in range(1, updates):
        target = step*budget/updates
        index = bisect_left(prefix, target)
        index = min((index-1, index), key=lambda k: abs(prefix[k]-target))
        cuts.append(max(cuts[-1]+1, min(index, len(stream)-(updates-step))))
    cuts.append(len(stream))
    return [stream[a:b] for a, b in zip(cuts, cuts[1:])]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parents', required=True)
    p.add_argument('--decisions', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    parents = sorted((r for r in read_jsonl(args.parents) if r['dataset'] == 'gsm8k' and r['partition'] == 'audit_draw'),
                     key=lambda r: r['rank'])
    accepted = defaultdict(list)
    for r in read_jsonl(args.decisions):
        if r['dataset'] == 'gsm8k' and r['reason'] == 'accepted':
            accepted[r['problem_id']].append(r)
    arms = [('repeat', 256, 1), ('solutions', 256, 4), ('mixed', 512, 2), ('breadth', 1024, 1)]
    budget, updates, seeds, summary = 524288, 256, (17, 23), []
    for arm, p_count, k in arms:
        pp = parents[:p_count]
        rr = [a for parent in pp for a in accepted[parent['id']][:k]]
        write_jsonl(out/f'{arm}_rows.jsonl', rr)
        for seed in seeds:
            schedule = whole_response_schedule([r['n_supervised'] for r in rr], budget, updates, seed)
            counts = Counter(i for update in schedule for i in update)
            per_update = [sum(rr[i]['n_supervised'] for i in update) for update in schedule]
            processed = sum(rr[i]['n_processed']*n for i,n in counts.items())
            by_parent = Counter()
            for i, n in counts.items():
                by_parent[rr[i]['problem_id']] += n
            result = {'arm': arm, 'seed': seed, 'acquired_p': p_count, 'target_k': k,
                      'trainable_p': len(by_parent), 'unique_pairs': len(rr),
                      'zero_solution_p': p_count-len(by_parent),
                      'target_reached_p': sum(len(accepted[x['id']]) >= k for x in pp),
                      'supervised_response_tokens': sum(per_update), 'optimizer_updates': len(schedule),
                      'processed_nonpadding_tokens': processed, 'presentations': sum(counts.values()),
                      'per_row_exposure_range': [min(counts.values()), max(counts.values())],
                      'per_parent_exposure_range': [min(by_parent.values()), max(by_parent.values())],
                      'per_update_supervised_range': [min(per_update), max(per_update)],
                      'max_sequence_tokens': max(r['n_processed'] for r in rr),
                      'padding_tokens_with_microbatch_one': 0,
                      'status': 'CPU schedule proposal only; no GPU job approved or run'}
            write_json(out/f'{arm}_seed{seed}.json', {'summary': result, 'updates': schedule,
                       'row_exposures': dict(sorted(counts.items())), 'problem_exposures': dict(sorted(by_parent.items()))})
            summary.append(result)
    eng = [accepted[r['id']][0] for r in parents if accepted[r['id']]][:32]
    write_jsonl(out/'engineering_32_rows.jsonl', eng)
    write_json(out/'proposal.json', {
        'status': 'for scientific/compute review after a new real-data engineering profile',
        'primary_student': 'Qwen/Qwen2.5-1.5B base', 'model_revision': '8faed761d45a263340a0528343f099c05c9a4323',
        'first_engineering_stage': '32 available parents selected by frozen rank, one response each; feasibility only. Profile update/runtime/generation cost before any scientific phase.',
        'source': 'same pinned OpenMathInstruct-2 slice; cap16 per acquired parent; zero parents retained in allocation denominators',
        'arms': summary, 'max_context_proposal': 1024, 'max_new_tokens_proposal': 768,
        'matching': 'Exact total supervised response tokens and updates; every selected pair used; whole traces; microbatch1; response-token normalization. Per-update token counts, processed tokens and exposure residuals are disclosed, not equalized.',
        'remainder_caveat': 'Seeded subset-sum gives every pair q or q+1 exposures. The extra-exposure selection depends on lengths; report this residual and use the same algorithm in all arms.',
        'first_paired_seed': 17, 'conditional_replication_seed': 23,
        'total_supervised_tokens_one_seed': budget*len(arms),
        'total_supervised_tokens_two_seeds': budget*len(arms)*len(seeds),
        'math_second_task': 'Retain 512 acquired parents and 21 strata. After reviewing unresolved answer forms and quality, use decisive P/K contrasts (128,4), (256,2), (512,1); no second full grid.',
        'remaining_gpu_process_seconds': 1229, 'gpu_runtime_estimate': None,
        'launchable': False,
        'prelaunch_requirements': ['review this scientific schedule and residuals', 'review reference-quality flags and answer-format limitations',
                                 'new real-data 32-example overfit and measured profile', 'price and authorize the complete bounded phase',
                                 'freeze development scoring; keep official tests untouched']})
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
