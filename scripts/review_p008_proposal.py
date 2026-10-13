"""Read-only arithmetic checks for a proposal, not a new experiment or power claim."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def check(summary_path, runtime_path):
    summary = json.loads(Path(summary_path).read_text())
    runtime = json.loads(Path(runtime_path).read_text())
    cells = {r['cell']: [r['seeds'][str(s)]['correct'] / 1319 * 100
                         for s in (17, 23)] for r in summary['table']}
    assert len(cells) == 4
    deltas = {c: v[1] - v[0] for c, v in cells.items()}
    pooled_sd = math.sqrt(sum(d*d/2 for d in deltas.values()) / 4)
    interaction = [cells['depth_p4'][i]-cells['breadth_p4'][i]
                   -cells['depth_p0'][i]+cells['breadth_p0'][i] for i in (0, 1)]
    mean = sum(interaction)/2
    training = runtime['training_update_gpu_minutes']
    other = runtime['summed_worker_gpu_hours']-training/60
    return dict(
        schema='p008_v2_design_arithmetic_review_v1', new_model_calls=0,
        inputs={str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest()
                for p in (summary_path, runtime_path)},
        seed23_minus_seed17_pp=deltas,
        pooled_cell_sd_assuming_common_variance=pooled_sd,
        interaction_sd_assuming_independent_cells=2*pooled_sd,
        two_observed_paired_interactions_pp=interaction,
        paired_interaction_sample_sd_df1=abs(interaction[0]-interaction[1])/math.sqrt(2),
        illustrative_normal_n_without_procurement_or_covariance=(1.96+.84162)**2*(2*pooled_sd/mean)**2,
        statistical_limits=[
            'Only two training seeds; neither variance estimate is stable.',
            'Independent-cell/common-variance assumptions are unverified.',
            'The normal n is an illustrative calculation, not an 80%-power guarantee.',
            'Procurement, within-draw clustering, question sampling and selection are not covered.'
        ],
        teacher_pool=dict(problems=7473, attempts_per_problem=8, outputs=7473*8,
                          maximum_completion_tokens=7473*8*1024),
        students=dict(new_models=20, training_base_run_units=4+8*4+8*16,
                      formal_primary_outputs=20*1319, base_outputs_additional=1319,
                      linear_training_gpu_hours=training/8*(4+8*4+8*16)/60,
                      linear_other_worker_gpu_hours=other/8*20,
                      caveat='Conditional linear extrapolation, not a measured runtime or bill; audit/storage/retries/base/teacher/secondary extra.'),
        secondary=dict(old_models=8, new_models=20, answers_per_question=8, questions=1319,
                       outputs_without_optional_D2=28*1319*8,
                       outputs_with_optional_D2=32*1319*8,
                       max_completion_tokens_without_D2_at_cap512=28*1319*8*512,
                       caveat='New temperature-sampled metric; not a variance reduction of the original greedy estimator.'),
        reduced_design_example=dict(status='proposal_not_admitted',
            budget_units=4, training_units=4,
            main_students=2*2*2, unit='2 independent draws x 2 prices x 2 policies x one fixed training seed',
            extra_axis_bridge_students=3, total_students=11, base_evaluation_additional=1,
            training_base_run_units=8*4+1+1+4,
            caveat='Two draws are exploratory and not a high-power or procurement-population guarantee.')
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--summary', required=True)
    p.add_argument('--runtime', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    result = check(a.summary, a.runtime)
    with Path(a.out).open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
