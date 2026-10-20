"""One original E9 n3200-minus-n400 paired analysis; saved labels only."""
from pathlib import Path
import csv
import numpy as np
from experiments.p010.common import read, dump, sha, utc
from analyses.p010_paired_questions import paired_summary
from scripts.analyze_p010_completed_students import checked_table

R = Path('.local/p010_20261019/r1')
P = Path('reports/p010_20261019')
RUNS = ('e9_base_math', 'e9_s17_n400', 'e9_s17_n3200')


def main():
    assert np.__version__ == '2.2.6'
    endpoint = R/'e9_runtime_inputs_r1/MATH_ENDPOINT.json'
    if not endpoint.exists():
        raise ValueError('Original E9 endpoint filename must be read from the input manifest')
    ids = [x['problem_id'] for x in read(endpoint)]
    assert len(ids) == len(set(ids)) == 500
    bindings = {str(endpoint): sha(endpoint)}
    vectors = {}; cells = []
    for run in RUNS:
        packet = P/'e9_results_v1'/run
        s = read(packet/'SUMMARY.json'); g = read(packet/'GENERATION_ORACLE.json')
        q = read(packet/'SCORING_ORACLE.json'); provider = read(packet/'PROVIDER.json')
        assert q['passed'] and g['passed'] and g['technical_unknown'] == 0
        assert q['full_generation_proof_sha256'] == sha(packet/'GENERATION_ORACLE.json')
        assert provider['owned_count'] == 0 and provider['lifecycle']['state'].upper() == 'STOPPED'
        assert s['updates'] == (0 if run == RUNS[0] else 1024)
        assert s['targets'] == (0 if run == RUNS[0] else 2097148)
        values = checked_table(q['endpoints']['greedy']['question_correct'], ids, s['greedy_correct'])
        vectors[run] = dict(complete=True, technical_unknown=0, metric='greedy', question_ids=ids, question_values=values)
        cells.append(dict(run=run, correct=sum(values), total=500, accuracy_percent=sum(values)/5,
                          caps=s['logical_stops']['greedy'].get('length_cap', 0),
                          updates=s['updates'], targets=s['targets'], training_seed=s['training_seed']))
        for f in ('SUMMARY.json','GENERATION_ORACLE.json','SCORING_ORACLE.json','PROVIDER.json','MANIFEST.json'):
            bindings[str(packet/f)] = sha(packet/f)
    contrasts = [dict(name='E9_OLMo_T72_n3200_minus_n400', left=RUNS[2], right=RUNS[1])]
    source_names = [Path(__file__).resolve().relative_to(Path.cwd()), Path('analyses/p010_paired_questions.py'),
                    Path('scripts/analyze_p010_completed_students.py'), Path('experiments/p010/common.py')]
    out = R/'e9_analysis_r1'; out.mkdir(exist_ok=False)
    dump(out/'INTENT.json', dict(utc=utc(), source_files={str(f): sha(f) for f in source_names},
        input_files=bindings, original_D2_scope='original E9 n400/n3200 plus descriptive base',
        contrasts=contrasts, roster_fixed_before_this_computation=True, preregistered=False,
        saved_complete_labels_already_observed=True, no_new_models=True, no_raw_decoding=True,
        no_symbolic_scoring=True, no_state_loading=True, old_C9_or_seed29_analysis_repeated=False))
    try:
        dump(out/'VECTORS.json', vectors)
        result = paired_summary(vectors, contrasts, ids, 'greedy')
        dump(out/'PAIRED.json', result); dump(out/'CELLS.json', cells)
        with (out/'CELLS.csv').open('x', newline='') as f:
            w=csv.DictWriter(f, fieldnames=list(cells[0]), lineterminator='\n'); w.writeheader(); w.writerows(cells)
        with (out/'PAIRED.csv').open('x', newline='') as f:
            names=['name','left','right','difference_pp','ci_low_pp','ci_high_pp','net_correct_count','discordant_questions']
            w=csv.DictWriter(f,fieldnames=names,lineterminator='\n');w.writeheader()
            for x in result['contrasts']:
                w.writerow({k:x[k] for k in names if k not in ('ci_low_pp','ci_high_pp')} |
                           dict(ci_low_pp=x['pointwise_95_ci_pp'][0],ci_high_pp=x['pointwise_95_ci_pp'][1]))
        dump(out/'COMPLETED.json',dict(utc=utc(),passed=True,original_endpoints=3,original_paired_contrasts=1,
            draws=10000,seed=20261019,numpy_version=np.__version__,new_model_calls=0,new_scores=0,
            new_state_loads=0,old_analysis_repeated=False,independent_A3_pending=True,
            interval_scope='conditional_on_observed_models_and_question_resampling',
            training_seed_population=False,familywise=False,equivalence=False))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),preserve_parts=True,automatic_retry=False))
        raise


if __name__ == '__main__': main()
