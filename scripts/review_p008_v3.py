"""Deterministic proposal arithmetic; no model work or admission."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def review(runtime_path):
    p = Path(runtime_path)
    runtime = json.loads(p.read_text())
    train_per_unit = runtime['training_update_gpu_minutes'] / 8 / 60
    other_per_student = (runtime['summed_worker_gpu_hours'] - runtime['training_update_gpu_minutes'] / 60) / 8
    # Counts follow the ordered v3 fallback text, before any student outcomes.
    variants = [
        ('full_8x', 2, 8, True),
        ('drop_lowB_highT_corners', 2, 8, False),
        ('reduce_to_4x', 2, 4, False),
        ('one_draw_4x', 1, 4, False),
    ]
    rows = []
    for name, draws, hi, full_bridge in variants:
        main_n = draws * 2 * 2 * 2
        bridge_n = 4 if full_bridge else 2
        units = draws * 4 * (1 + hi) + (2 * (1 + hi) if full_bridge else 2)
        rows.append(dict(name=name, draws=draws, high_budget_multiplier=hi,
                         main_students=main_n, bridge_students=bridge_n,
                         total_students=main_n+bridge_n, training_units=units,
                         targets_if_T0_524287=units*524287,
                         updates_if_U0_256=units*256,
                         primary_student_outputs=(main_n+bridge_n)*1319,
                         base_outputs_additional=1319,
                         linear_training_gpu_hours=units*train_per_unit,
                         linear_other_worker_gpu_hours=(main_n+bridge_n)*other_per_student,
                         complete_BxT_factorial=full_bridge))
    zsum=1.96+0.84162
    return dict(schema='p008_v3_review_arithmetic_v1', execution_admitted=False, new_model_calls=0,
                input={str(p):hashlib.sha256(p.read_bytes()).hexdigest()},variants=rows,
                teacher_pool=dict(train_total=7473,proposed_dev_holdout=500,remaining=6973,
                                  estimated_outputs_per_draw=14000,estimated_outputs_two_draws=28000,
                                  max_completion_tokens_if_28000_attempts_at_1024=28000*1024,
                                  linear_breadth_purchase_estimate_at_8x=420*8,
                                  fraction_of_remaining_pool=420*8/6973),
                mde_table_reproduction=[dict(s_pp=s,independent_components_example_pp=zsum*math.sqrt(1.1**2+s*s)) for s in (.9,2,3)],
                caveats=[
                    'Runtime is linear extrapolation from eight P007B runs, not measurement of v3, a cost quote or admission.',
                    'Other worker time is not purely evaluation; estimates omit teacher/base/Phase0/final audit/failure/closing.',
                    'The MDE reproduction assumes two independent budget contrasts per draw and two independent draws with no covariance; shared questions and coupled traces violate this simplification in general.',
                    'If s denotes SD of C rather than of each within-budget contrast, the displayed MDE formula is a different model.',
                    'No universal four-percentage-point detectability boundary follows; two draws are exploratory.',
                    'Procurement totals/coverage are estimates, not output allowances or a guarantee of supply.',
                    'T0 and update scaling shown here are proposed numerical bindings, not frozen runnable plans.'
                ])

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--runtime',required=True);a.add_argument('--out',required=True);v=a.parse_args()
    with Path(v.out).open('x') as f: json.dump(review(v.runtime),f,indent=2);f.write('\n')
