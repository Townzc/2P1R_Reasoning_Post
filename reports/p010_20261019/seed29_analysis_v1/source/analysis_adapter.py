"""Original Tier3 addendum only; never rerun the completed seed17 analysis."""
from pathlib import Path
import csv
import numpy as np
from experiments.p010.common import read, dump, sha, utc
from analyses.p010_paired_questions import paired_summary
from scripts.analyze_p010_completed_students import load, checked_table

ROOT = Path('reports/p010_20261019')
CELLS = {f'{teacher}_n{n}_k1': f'{teacher}_s29_n{n}_k1'
         for teacher in ('t15', 't72') for n in (400, 3200)}


def main():
    if np.__version__ != '2.2.6':
        raise ValueError('Original formal numpy version required')
    binding = {}
    roster = load(ROOT / 'c9_paired_analysis_preparation_v1/FIXED_COMPARISON_ROSTER.json', binding)
    # Exactly the pre-existing contrasts whose two cells were repeated at seed29.
    contrasts = [c for c in roster['primary_MATH'] if c['left'] in CELLS and c['right'] in CELLS]
    if len(contrasts) != 4 or not roster['Tier3_later_dated_addendum']:
        raise ValueError('The original four Tier3 comparisons must all be retained')
    endpoint = Path('.local/p010_20261019/r1/seed29_inputs_r2/MATH_ENDPOINT.json')
    ids = [r['problem_id'] for r in read(endpoint)]
    binding[str(endpoint)] = dict(bytes=endpoint.stat().st_size, sha256=sha(endpoint))
    if len(ids) != len(set(ids)) or len(ids) != 500:
        raise ValueError('Original complete MATH500 required')
    greedy = {}; sampled = {}; cells = []
    for name, run in CELLS.items():
        packet = ROOT / 'seed29_results_v1' / run
        proof = load(packet / 'SCORING_ORACLE.json', binding)
        generation = load(packet / 'GENERATION_ORACLE.json', binding)
        summary = load(packet / 'SUMMARY.json', binding)
        if (not proof['passed'] or not generation['passed'] or generation['technical_unknown'] != 0
                or summary['training_seed'] != 29 or summary['same_frozen_seed17_training_data'] is not True
                or proof['updates_verified'] != 1024 or proof['targets_verified'] != 2097148
                or proof['full_generation_proof_sha256'] != sha(packet / 'GENERATION_ORACLE.json')
                or generation['reviews']['A1']['scope'] != 'p010-Tier3-seed29-exact-input-and-plan-A1'):
            raise ValueError('Actual complete original same-data seed29 proof required')
        values = checked_table(proof['endpoints']['greedy']['question_correct'], ids,
                               proof['endpoints']['greedy']['correct'])
        draws = [checked_table(proof['endpoints']['sample'+str(i)]['question_correct'], ids,
                              proof['endpoints']['sample'+str(i)]['correct']) for i in range(4)]
        means = [sum(v[k] for v in draws)/4 for k in range(500)]
        if sum(sum(v) for v in draws) != proof['sampled_correct']:
            raise ValueError('All original four samples must be included')
        greedy[name] = dict(complete=True, technical_unknown=0, metric='greedy',
                            question_ids=ids, question_values=values)
        sampled[name] = dict(complete=True, technical_unknown=0, metric='sampled_mean_pass_at_1',
                             question_ids=ids, question_values=means, samples_per_question=4)
        cells.append(dict(cell=name, run=run, seed=29, updates=1024, targets=2097148,
                          greedy_correct=sum(values), greedy_total=500,
                          greedy_caps=proof['logical_stops']['greedy']['length_cap'],
                          sampled_correct=proof['sampled_correct'], sampled_total=2000))
    out = Path('.local/p010_20261019/r1/seed29_analysis_r1')
    out.mkdir(exist_ok=False)
    sources = {str(p): sha(p) for p in (Path(__file__), Path('analyses/p010_paired_questions.py'),
               Path('scripts/analyze_p010_completed_students.py'), Path('experiments/p010/common.py'))}
    dump(out / 'INTENT.json', dict(utc=utc(), input_files=binding, source_files=sources,
        original_contrasts=contrasts, original_seed17_analysis_repeated=False,
        original_source_roster_reused_without_selection=True, new_model_calls=0,
        new_raw_decodes=0, new_symbolic_scores=0, course_report_prose_generated=False))
    try:
        for prefix, vectors, metric in [('GREEDY', greedy, 'greedy'),
                                        ('SAMPLED', sampled, 'sampled_mean_pass_at_1')]:
            dump(out / (prefix+'_VECTORS.json'), vectors)
            result = paired_summary(vectors, contrasts, ids, metric)
            dump(out / (prefix+'_PAIRED.json'), result)
            with (out / (prefix+'_PAIRED.csv')).open('x', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'left', 'right', 'difference_pp',
                    'ci_low_pp', 'ci_high_pp', 'meets_frozen_3pp_and_positive_lower'], lineterminator='\n')
                writer.writeheader()
                for row in result['contrasts']:
                    writer.writerow({k: row[k] for k in writer.fieldnames if k not in ('ci_low_pp', 'ci_high_pp')} |
                                    dict(ci_low_pp=row['pointwise_95_ci_pp'][0], ci_high_pp=row['pointwise_95_ci_pp'][1]))
        dump(out / 'CELLS.json', cells)
        with (out / 'CELLS.csv').open('x', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(cells[0]), lineterminator='\n')
            writer.writeheader(); writer.writerows(cells)
        dump(out / 'COMPLETED.json', dict(utc=utc(), passed=True, original_seed=29,
            original_models=4, original_primary_contrasts=4, original_secondary_contrasts=4,
            draws=10000, bootstrap_seed=20261019, numpy_version=np.__version__,
            old_analysis_repeated=False, new_symbolic_scores=0, independent_A3_pending=True,
            interval_scope='conditional_on_observed_models_and_question_resampling',
            training_seed_population=False, familywise=False, equivalence=False))
    except BaseException as exc:
        dump(out / 'FAILED.json', dict(utc=utc(), type=type(exc).__name__, error=str(exc),
                                      preserve_completed_parts=True, automatic_retry=False))
        raise


if __name__ == '__main__':
    main()
