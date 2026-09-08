"""Recompute saved pilot scores and full-dose accounting without GPU inference."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from src.countdown_smoke import safe_parse, value
from src.evaluation import score_text, summarize
from src.pilot_runtime import load_pilot_inputs, unique_rows
from src.sft_data import read_jsonl, sha256_file


def verify(root):
    def read(name):
        return json.loads((root/name).read_text())
    manifest, receipt, metrics = map(read, ['run_manifest.json', 'resource_receipt.json', 'metrics.json'])
    cfg = manifest['config']
    queue = json.loads(Path('configs/pilot_v1/queue.json').read_text())
    jobs = [j for phase in ('calibration', 'comparison') for j in queue[phase] if j['run_id'] == root.name]
    if len(jobs) != 1 or cfg != json.loads(Path(jobs[0]['config']).read_text()):
        raise ValueError('Run does not match the frozen queue')
    if manifest['model'] != json.loads(Path('configs/models.lock.json').read_text())['main']:
        raise ValueError('Model revision differs')
    if manifest['status'] != 'completed' or receipt['status'] != 'completed' or receipt['run_id'] != root.name:
        raise ValueError('Run has not completed successfully')
    if receipt['charged_seconds'] != math.ceil(receipt['elapsed_seconds']) or receipt['max_seconds'] != jobs[0]['max_seconds']:
        raise ValueError('Receipt accounting differs')
    train, dev, broad, schedule, _ = load_pilot_inputs(cfg)
    history = read_jsonl(root/'train_history.jsonl')
    planned, actual = read('budget_report.json'), read('actual_budget.json')
    if [h['step'] for h in history] != list(range(1, len(schedule)+1)) or metrics['steps'] != cfg['steps']:
        raise ValueError('Incomplete or reordered update history')
    if any(actual[k] != planned[k] for k in actual):
        raise ValueError('Actual exposure accounting differs from the pre-training plan')
    if sum(h['supervised_tokens'] for h in history) != actual['supervised_response_tokens']:
        raise ValueError('History token total differs')
    if any(not math.isfinite(h[k]) for h in history for k in ('response_nll', 'grad_norm', 'seconds')):
        raise ValueError('Nonfinite training history')

    checked = {}
    def check(name, rows, samples, expected, ks=()):
        predictions = read_jsonl(root/name)
        references = {r['problem_id']: r for r in rows}
        counts = Counter(p['problem_id'] for p in predictions)
        if counts != Counter({pid: samples for pid in references}):
            raise ValueError('Wrong evaluation IDs or multiplicities: '+name)
        if len({(p['problem_id'], p['sample_index']) for p in predictions}) != len(predictions):
            raise ValueError('Duplicate sample identity: '+name)
        errors = Counter()
        for p in predictions:
            ref = references[p['problem_id']]
            if any(p[k] != ref[k] for k in ('numbers', 'target', 'prompt')):
                raise ValueError('Prediction prompt differs from frozen data')
            rescored = score_text(p['text'], ref['numbers'], ref['target'])
            if any(p[k] != v for k, v in rescored.items()):
                raise ValueError('Saved score disagrees with generated text')
            if not p['parsed']:
                errors['parse_failure'] += 1
            elif p['correct']:
                errors['correct'] += 1
            else:
                tree = safe_parse(p['expression'])
                def leaves(t):
                    return [t[1]] if t[0] == 'n' else leaves(t[1])+leaves(t[2])
                if Counter(leaves(tree)) != Counter(ref['numbers']):
                    errors['wrong_number_multiset'] += 1
                else:
                    try:
                        value(tree)
                        errors['wrong_target_value'] += 1
                    except ZeroDivisionError:
                        errors['division_by_zero'] += 1
        stats = summarize(predictions, ks)
        # Allow only floating-point library roundoff across Linux/macOS when
        # recomputing entropy; identities, counts and correctness remain exact.
        def agrees(k):
            return (math.isclose(stats[k], expected[k], rel_tol=1e-12, abs_tol=1e-12)
                    if isinstance(stats[k], float) else stats[k] == expected[k])
        if not all(agrees(k) for k in stats):
            raise ValueError('Summary differs from recomputed scores: '+name)
        checked[name] = {'generations': len(predictions), 'sha256': sha256_file(root/name),
                         'counts': dict(errors), 'scores_recomputed_from_text': True}

    for name, rows in [('train_sample16', unique_rows(train, 16)), ('dev', dev), ('dev_broad', broad)]:
        check('final_'+name+'_greedy.jsonl', rows, 1, metrics[name])
    if cfg.get('samples_per_problem'):
        check('final_dev_sampled.jsonl', dev, cfg['samples_per_problem'], metrics['dev_sampled'], cfg['sampled_ks'])
    if cfg['mode'] == 'pilot_calibration':
        for checkpoint in read('checkpoint_metrics.json'):
            check(f"dev_step_{checkpoint['step']:04d}_greedy.jsonl", dev, 1, checkpoint)
        gate = metrics['dev']['accuracy_macro'] >= 4/64 and metrics['dev']['parsing_failure_rate'] <= .1 and metrics['dev']['truncation_rate'] <= .05
        if gate != metrics['pilot_gate']['passed']:
            raise ValueError('Gate does not match the frozen rule')
    return {'run_id': root.name, 'status': 'VERIFIED_ON_CPU', 'training_commit': manifest['git_commit'],
            'steps': len(history), 'supervised_response_tokens': actual['supervised_response_tokens'],
            'planned_actual_accounting_equal': True, 'evaluation': checked,
            'scope': 'Final-expression correctness and recorded exposure accounting; intermediate generated steps are not independently verified. No new model inference or holdout evaluation.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.run)
    with args.out.open('x') as f:
        f.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'run_id': args.run.name, 'status': report['status']}))


if __name__ == '__main__':
    main()
