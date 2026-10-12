"""Analyze all eight verified P007B students, never dispatch or select a checkpoint."""
import argparse
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest

CELLS = ('breadth_p0', 'depth_p0', 'breadth_p4', 'depth_p4')
SEEDS = (17, 23)


def contrasts(predictions):
    """Paired questions, with each resample shared across cells and training seeds."""
    import numpy as np
    expected = {f'{cell}_s{seed}' for cell in CELLS for seed in SEEDS}
    if set(predictions) != expected:
        raise ValueError('All eight fixed students are required')
    ids = sorted(predictions['breadth_p0_s17'])
    if not ids:
        raise ValueError('Empty evaluation roster')
    for values in predictions.values():
        if sorted(values) != ids or any(type(x) is not bool for x in values.values()):
            raise ValueError('Roster mismatch or unknown outcome; do not coerce or drop')
    arrays = {k: np.array([v[q] for q in ids], dtype=float) for k, v in predictions.items()}
    rng = np.random.default_rng(20261013)
    indices = rng.integers(0, len(ids), size=(10000, len(ids)))
    results = {}
    vectors = {}
    for price in (0, 4):
        vectors[f'depth_minus_breadth_p{price}'] = {
            seed: arrays[f'depth_p{price}_s{seed}'] - arrays[f'breadth_p{price}_s{seed}']
            for seed in SEEDS}
    vectors['price_interaction'] = {
        seed: vectors['depth_minus_breadth_p4'][seed] - vectors['depth_minus_breadth_p0'][seed]
        for seed in SEEDS}
    for name, by_seed in vectors.items():
        means = np.mean(list(by_seed.values()), axis=0)
        per_seed = {}
        for seed, differences in by_seed.items():
            entry = dict(difference_pp=float(differences.mean() * 100),
                question_difference_counts={str(int(x)): int((differences == x).sum())
                                            for x in sorted(set(differences))},
                conditional_question_interval_pp=np.quantile(
                    differences[indices].mean(axis=1) * 100, [.025, .975]).tolist())
            if name != 'price_interaction':
                entry.update(gained=int((differences == 1).sum()), lost=int((differences == -1).sum()))
            per_seed[str(seed)] = entry
        results[name] = dict(per_seed=per_seed, mean_difference_pp=float(means.mean() * 100),
            conditional_question_interval_pp=np.quantile(
                means[indices].mean(axis=1) * 100, [.025, .975]).tolist())
    return results


def analyze(root):
    root = Path(root)
    spec = read('reports/sft_allocation_midpoint_20261011/P007B_STUDENT_ADMISSION.json')
    inputs = root / 'student_preparation_r1' / 'inputs'
    if sha(inputs / 'manifest.json') != spec['input_sha256']:
        raise ValueError('Frozen student inputs differ')
    from src.sft_data import read_jsonl
    ids = sorted(r['problem_id'] for r in read_jsonl(inputs / 'gsm8k_test1319.jsonl'))
    if len(ids) != 1319 or len(set(ids)) != 1319:
        raise ValueError('The complete standard benchmark is required')
    predictions, sources, tables = {}, {}, []
    for cell in CELLS:
        audit = read(root / 'exports' / cell / 'LOCAL_ORACLE_AUDIT.json')
        acquisition = read(root / 'exports' / cell / 'result.json')
        envelope = read(root / (cell + '_run_r1') / 'result.json')
        if (audit['unknown'] != 0 or audit['manifest_digest'] != envelope['receipt']['evidence_sha256']
                or acquisition != envelope['result'] or envelope['receipt']['status'] != 'completed'):
            raise ValueError('Acquisition verification differs')
        row = dict(cell=cell, acquisition=audit,
            parents_with_usable=acquisition['acquired_problems'] - acquisition['zero_usable_parents'],
            setup_and_closing_seconds=acquisition['wall_seconds'] - acquisition['active_ns'] / 1e9,
            acquisition_runtime_rate_estimate_usd=acquisition['runtime_rate_estimate_usd'], seeds={})
        for seed in SEEDS:
            run = f'{cell}_s{seed}'
            receipt = root / 'students' / (run + '_run_r1') / 'result.json'
            raw = read(receipt)
            r = raw['result']
            local_file = root / 'student_exports' / run / 'LOCAL_ORACLE_AUDIT.json'
            local = read(local_file)
            if (r['status'] != 'completed' or raw['receipt']['status'] != 'completed'
                    or r['cell'] != cell or r['seed'] != seed or r['committed_updates'] != 256
                    or r['supervised_tokens'] != 524288 or r['physical_generated_outputs'] != 1319
                    or r['endpoint']['n'] != 1319 or sorted(r['endpoint']['question_correct']) != ids
                    or local['run_id'] != run or local['input_sha256'] != spec['input_sha256']
                    or local['artifact_digest'] != digest(raw['artifact_manifest'])
                    or local['artifact_digest'] != raw['receipt']['evidence_sha256']
                    or local['outputs_independently_rescored'] != 1319
                    or local['correct'] != r['endpoint']['correct']):
                raise ValueError('Incomplete, unverified or unequal student run: ' + run)
            qc = r['endpoint']['question_correct']
            if any(type(v) is not bool for v in qc.values()) or sum(qc.values()) != r['endpoint']['correct']:
                raise ValueError('Unknown or inconsistent endpoint')
            predictions[run] = qc
            sources[run] = dict(receipt_sha256=sha(receipt), local_audit_sha256=sha(local_file))
            row['seeds'][str(seed)] = dict(correct=sum(qc.values()), n=1319, accuracy=sum(qc.values()) / 1319,
                parsed=r['endpoint']['parsed'], stop_reasons=r['endpoint']['stop_reasons'],
                train_seconds=r['train_seconds'], wall_seconds=r['wall_seconds'],
                processed_tokens=r['processed_tokens'], runtime_rate_estimate_usd=r['runtime_rate_estimate_usd'])
        row['mean_accuracy'] = sum(v['accuracy'] for v in row['seeds'].values()) / 2
        tables.append(row)
    return dict(schema='p007b_cost_matched_student_results_v1', table=tables, sources=sources,
        contrasts=contrasts(predictions), updates=2048, supervised_targets=4194304, endpoint_outputs=10552,
        bootstrap=dict(replicates=10000, seed=20261013, unit='paired question, shared across all eight students',
                       interpretation='Conditional on these models and one procurement draw, not seed or procurement uncertainty.'),
        limitations=['Hypothetical problem prices and a common acquisition cap, not exactly equal spend or a universal optimum.',
            'Report unused wallets, failures, duplicates, startup/closing and pilot costs; platform meter is separate.',
            'Previously observed official benchmark; model pretraining contamination not ruled out.',
            'Two student seeds on one acquisition draw do not establish procurement robustness.',
            'A positive interaction alone does not establish a policy winner; a non-significant contrast is not equivalence.',
            'Final-answer correctness and distinct text are not proof of correct or diverse reasoning.'])


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    dump(a.out, analyze(a.root))
