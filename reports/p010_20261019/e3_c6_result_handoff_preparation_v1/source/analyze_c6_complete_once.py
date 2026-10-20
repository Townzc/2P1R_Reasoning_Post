"""Original four C6 cue-minus-no-cue comparisons, saved Boolean tables only."""
import csv
import importlib.util
import json
import os
import threading
from pathlib import Path

import numpy as np
from experiments.p010.common import read, dump, sha, utc

R = Path('.local/p010_20261019/r1')
P = Path('reports/p010_20261019')
RUNS = ('base_math', 'base_gsm', 's1_n400_math', 't72_n400_math')
METRICS = ('greedy', 'sampled_mean_pass_at_1')
LABELS = {c+'/'+e for c in ('no_cue','cue') for e in ['greedy']+[f'sample{i}' for i in range(4)]}


def cell_vectors(tables, original_rows, run):
    """Check every original question and all four samples before averaging."""
    if run not in RUNS or not isinstance(tables, dict) or set(tables) != LABELS:
        raise ValueError('Original complete cell and all ten condition tables required')
    ids = list(dict.fromkeys(row['problem_id'] for row in original_rows))
    total = 1319 if run == 'base_gsm' else 500
    if len(ids) != total:
        raise ValueError('Original complete question roster required')
    for table in tables.values():
        if not isinstance(table, dict) or set(table) != set(ids) or any(type(v) is not bool for v in table.values()):
            raise ValueError('Every condition needs exact same original Boolean question table')
    vectors = {metric:{} for metric in METRICS}
    cells = []
    for condition in ('no_cue', 'cue'):
        key = run+'/'+condition
        greedy = [tables[condition+'/greedy'][pid] for pid in ids]
        sampled = [sum(tables[condition+f'/sample{i}'][pid] for i in range(4))/4 for pid in ids]
        for metric, values in zip(METRICS, (greedy, sampled)):
            vector = dict(complete=True, technical_unknown=0, metric=metric,
                          question_ids=ids, question_values=values)
            if metric == METRICS[1]:
                vector['samples_per_question'] = 4
            vectors[metric][key] = vector
        cells.append(dict(run=run, condition=condition, questions=total,
            greedy_correct=sum(greedy), greedy_accuracy_percent=sum(greedy)/total*100,
            sampled_correct=sum(sum(tables[condition+f'/sample{i}'][pid] for pid in ids) for i in range(4)),
            sampled_outputs=total*4, sampled_mean_pass_at_1_percent=sum(sampled)/total*100))
    return ids, vectors, cells


def main():
    if np.__version__ != '2.2.6':
        raise ValueError('Original P010 numpy2.2.6 required')
    packet = P/'c6_complete_results_v1'
    summary = read(packet/'SUMMARY.json')
    proof = read(packet/'COMPLETE_SPLIT_LINEAGE_RAW_ORACLE.json')
    if (not proof['passed'] or proof['technical_unknown'] != 0
            or proof['original_parent_status'] != 'failed'
            or summary['saved_parent_outputs'] != 18871 or summary['new_remaining_outputs'] != 2500
            or summary['publication_new_statistics'] != 0):
        raise ValueError('Complete original split-lineage publication required')
    providers = read(packet/'PROVIDERS.json')
    if any(v['owned_count'] != 0 or v['lifecycle']['state'].upper() != 'STOPPED' for v in providers.values()):
        raise ValueError('Both original apps must be actually STOPPED0')
    original = read(packet/'ORIGINAL_NO_CUE_BOOLEAN_TABLES.json')
    manifest = read(packet/'MANIFEST.json')
    bindings = {}
    by_task = {'math':{metric:{} for metric in METRICS}, 'gsm':{metric:{} for metric in METRICS}}
    ids_by_task, contrasts = {}, {'math':[], 'gsm':[]}
    cells = []
    for run in RUNS:
        cell = packet/'cells'/run
        done = read(cell/'COMPLETED.json')
        tables = read(cell/'QUESTION_CORRECT.json')
        if (done['passed'] is not True or done['technical_unknown'] != 0
                or done['old_scoring_repeated'] != 0 or done['old_generation_repeated'] != 0
                or done['bootstrap_performed'] is not False
                or done['question_correct_sha256'] != sha(cell/'QUESTION_CORRECT.json')
                or done['original_binding']['oracle_sha256'] != sha(packet/'COMPLETE_SPLIT_LINEAGE_RAW_ORACLE.json')
                or proof['cells'][run]['scoring_sha256'] != sha(cell/'SCORING_ROWS.json')):
            raise ValueError('Original completed score/provenance binding differs')
        for label, old_table in original[run].items():
            if tables['no_cue/'+label] != old_table:
                raise ValueError('Reused original no-cue labels changed')
        ids, vectors, values = cell_vectors(tables, read(cell/'SCORING_ROWS.json'), run)
        task = 'gsm' if run == 'base_gsm' else 'math'
        if task in ids_by_task and ids_by_task[task] != ids:
            raise ValueError('Original within-task question order differs')
        ids_by_task[task] = ids
        for metric in METRICS:
            by_task[task][metric].update(vectors[metric])
        contrasts[task].append(dict(name=run+'_cue_minus_no_cue', left=run+'/cue', right=run+'/no_cue'))
        cells.extend(values)
        for name in ('COMPLETED.json','QUESTION_CORRECT.json','SCORING_ROWS.json'):
            file = cell/name
            relative = file.relative_to(packet).as_posix()
            if manifest[relative]['sha256'] != sha(file):
                raise ValueError('Published original member changed')
            bindings[str(file)] = sha(file)
    for name in ('SUMMARY.json','COMPLETE_SPLIT_LINEAGE_RAW_ORACLE.json','PROVIDERS.json',
                 'ORIGINAL_NO_CUE_BOOLEAN_TABLES.json','MANIFEST.json'):
        bindings[str(packet/name)] = sha(packet/name)
    adapter = R/'c6_paired_questions_prepared.py'
    loader = importlib.util.spec_from_file_location('p010_c6_paired_question_adapter', adapter)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    sources = [Path(__file__).resolve().relative_to(Path.cwd()), adapter,
               Path('analyses/p010_paired_questions.py'), Path('experiments/p010/common.py')]
    out = R/'cue_benchmark_analysis_r1'
    out.mkdir(exist_ok=False)
    dump(out/'INTENT.json', dict(utc=utc(), source_files={str(f):sha(f) for f in sources},
        input_files=bindings, contrasts=contrasts, greedy_primary=True, sampled_secondary=True,
        sampled_question_mean_includes_all_four=True,
        roster_fixed_before_this_computation=True, exploratory=True, preregistered=False,
        old_analyses_repeated=False, new_model_calls=0, new_scores=0, new_decodes=0,
        new_state_loads=0, local_seconds=600))
    try:
        dump(out/'VECTORS.json', by_task)
        results = {}
        for task in ('math','gsm'):
            for metric in METRICS:
                label = task+'_'+metric
                results[label] = module.paired_summary(by_task[task][metric], contrasts[task], ids_by_task[task], metric)
                dump(out/(label.upper()+'_PAIRED.json'), results[label])
        dump(out/'CELLS.json', cells)
        with (out/'CELLS.csv').open('x', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(cells[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(cells)
        with (out/'PAIRED.csv').open('x', newline='') as f:
            names = ['task','metric','name','left','right','difference_pp','ci_low_pp','ci_high_pp','questions']
            writer = csv.DictWriter(f, fieldnames=names, lineterminator='\n')
            writer.writeheader()
            for task in ('math','gsm'):
                for metric in METRICS:
                    for item in results[task+'_'+metric]['contrasts']:
                        writer.writerow(dict(task=task, metric=metric,
                            **{k:item[k] for k in ('name','left','right','difference_pp','questions')},
                            ci_low_pp=item['pointwise_95_ci_pp'][0], ci_high_pp=item['pointwise_95_ci_pp'][1]))
        dump(out/'COMPLETED.json', dict(utc=utc(), passed=True, original_cells=4,
            primary_contrasts=4, secondary_contrasts=4, draws=10000, seed=20261019,
            numpy_version=np.__version__, new_scores=0, old_analyses_repeated=False,
            independent_A3_pending=True, training_seed_population=False,
            familywise_intervals=False, equivalence=False, new_scientific_stopping_rule=False))
        print(json.dumps(dict(complete=True, primary_contrasts=4, secondary_contrasts=4, actual_A3_pending=True)))
    except BaseException as exc:
        dump(out/'FAILED.json', dict(utc=utc(), type=type(exc).__name__, error=str(exc),
            partial_preserved=True, automatic_retry=False))
        raise


if __name__ == '__main__':
    timer = threading.Timer(600, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        main()
    finally:
        timer.cancel()
