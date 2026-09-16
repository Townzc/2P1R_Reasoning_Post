"""Build the Thursday decision packet from real, locally verified artifacts."""
from collections import Counter
from datetime import datetime
from fractions import Fraction
import csv
import json
from pathlib import Path
import shutil
import subprocess

from experiments.thursday_probe.common import ROOT,dump,stamp,ALIASES
from src.sft_data import read_jsonl,sha256_file


def build():
    source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    a=json.loads((ROOT/'e018_audit_r1/independent_audit.json').read_text())
    run=Path('runs')/ALIASES['E018'];m=json.loads((run/'metrics.json').read_text())
    provider=json.loads((ROOT/'PROVIDER_CLOSEOUT.json').read_text())
    if a['passed'] or provider['provider_power_state']!='stopped':
        raise ValueError('This closeout is specifically the stopped E018 gate failure')
    candidate=[]
    for name in ('data_r1','data_candidate2_r1','data_candidate3_r1'):
        folder=ROOT/name;d=json.loads((folder/'DATA_AUDIT.json').read_text())
        rows=read_jsonl(folder/'train_problems.jsonl')
        count=Counter(r['reason'] for r in csv.DictReader((folder/'DATA_EXCLUSIONS.csv').open()))
        fine=json.loads((ROOT/(name+'_fine_balance.json')).read_text())
        candidate.append({'folder':str(folder),'manifest_sha256':sha256_file(folder/'manifest.json'),
            'motif':d['target_motif'],'rank':d['candidate_index']+1,'split_counts':d['split_counts'],
            'main_token_residual_fraction':d['main_token_residual_fraction'],
            'prep_token_residual_fraction':d['prep_token_residual_fraction'],'prefix_questions':d['prefix_questions'],
            'train_targets_above40':sum(r['target']>40 for r in rows),'target_range':[min(r['target'] for r in rows),max(r['target'] for r in rows)],
            'train_identity_path_counts':{f:sum(p['paths'][f]['identity_operations']>0 for p in rows) for f in 'AB'},
            'fine_global_total_variation':{k:v['total_variation'] for k,v in fine.items()},
            'exclusion_reasons_all_preallocated_groups':dict(count),'dose':d['dose'],
            'model_calibration_done':False,'source_audit':str(folder/'DATA_AUDIT.json')})
    primary=candidate[0]
    prep={}
    for arm in ('prep_control','prep_bridge'):
        rows=read_jsonl(ROOT/'data_r1'/(arm+'.jsonl'))
        vals=[Fraction(r['answer']) for r in rows]
        prep[arm]={'rows':len(rows),'operator_counts':dict(sum((Counter(r['operators']) for r in rows),Counter())),
            'input_digit_counts':dict(Counter(str(len(str(n))) for r in rows for n in r['numbers'])),
            'answer_min':str(min(vals)),'answer_max':str(max(vals)),
            'integer_answers':sum(v.denominator==1 for v in vals),'negative_answers':sum(v<0 for v in vals),
            'number_groups':len({r['number_group_hash'] for r in rows})}
    audit={'status':'CPU_AUDIT_COMPLETE_MODEL_CALIBRATION_NOT_RUN','source_commit':source,
           'candidates':candidate,'primary_candidate_rank':1,'primary_prep_distribution':prep,
           'primary_common_atomic_rows':128,'historical_group_hashes_excluded':8192,
           'all_candidate_main_calibration_discovery_number_groups_disjoint':True,
           'reserved_question_contents_read':False,'official_test_read':False,
           'limits':['Operator syntax is a proxy, not cognitive strategy equivalence.',
                     'Within-question path selection minimizes length residual; no whole-question common-length filter.',
                     'Identity operations remain; detailed counts are disclosed, not filtered post-outcome.',
                     'Fine structure distributions are not exactly equal; global A/B and rendering counts are equal.',
                     'No candidate has been demonstrated nonsaturated or manipulable in the model.']}
    dump(ROOT/'DATA_AUDIT.json',audit)
    if (ROOT/'DATA_EXCLUSIONS.csv').exists():raise FileExistsError('No exclusion overwrite')
    shutil.copyfile(ROOT/'data_r1/DATA_EXCLUSIONS.csv',ROOT/'DATA_EXCLUSIONS.csv')
    budget={'phase_status':'closed_after_E018_retention_failure','planned_core_generations':7360,
            'calibration_reserve':640,'core_plus_reserve_cap':8000,'optional_repeat_cap':2032,
            'absolute_optional_cap':10032,'actual_generations':160,'actual_E018_generations':160,
            'actual_arithmetic_calibration_generations':0,'actual_probe_generations':0,
            'actual_discovery_generations':0,'actual_conditional_generations':0,
            'unused_is_not_permission_for_automatic_retry':True,'teacher_calls':0,'new_base_model_loads':1,
            'raw_prediction_files':[str(run/n) for n in ('base.jsonl','final.jsonl','final_train.jsonl')]}
    dump(ROOT/'GENERATION_BUDGET.json',budget)
    seconds=(datetime.fromisoformat(provider['shutdown_confirmed_by_utc'])-datetime.fromisoformat(provider['power_on_proxy_utc'])).total_seconds()
    timing=json.loads((run/'phase_timings.json').read_text())
    cost={'status':'closed_provider_shutdown_verified','currency':'CNY','provider_rate_per_hour':7.98,
          'power_on_proxy_utc':provider['power_on_proxy_utc'],'shutdown_confirmed_by_utc':provider['shutdown_confirmed_by_utc'],
          'whole_window_proxy_seconds':seconds,'whole_window_proxy_cost':seconds/3600*7.98,
          'proxy_is_invoice':False,'actual_invoice_reconciled':False,
          'setup_calibration_window_cap_seconds':2700,'window_planned_cost_cap':5.985,
          'charged_model_process_seconds':a['receipt']['charged_seconds'],'measured_model_process_wall_seconds':a['receipt']['wall_seconds'],
          'training_seconds':timing['phases_seconds']['training'],'peak_allocated_bytes':timing['peak_allocated_bytes'],
          'historical_phase_authorized_seconds':7200,'historical_phase_charged_seconds':7001,
          'historical_ledger_sha256':a['receipt']['old_ledger_sha256'],'historical_ledger_unchanged':True,
          'new_phase_authorized_seconds':915,'new_phase_charged_seconds':a['receipt']['charged_seconds'],
          'total_receipts_across_phases':22,'total_charged_process_seconds_across_phases':7001+a['receipt']['charged_seconds'],
          'reservations':0,'overall_shared_monetary_ceiling':3000,'historical_actual_spend_and_remaining_ceiling_unknown':True,
          'no_additional_instance_or_paid_teacher_API':True,'independent_adapter_bytes':a['checkpoint_bytes'],
          'provider_state':'stopped','E015_independent_full_weights_backup_still_incomplete':True}
    dump(ROOT/'COST_REPORT.json',cost)
    dump(ROOT/'PHASE_LEDGER.json',{'phase':'Thursday_E018','closed':True,'historical_ledger_sha256':a['receipt']['old_ledger_sha256'],
         'historical_receipts':21,'historical_used_seconds':7001,'new_allowance_seconds':915,'receipts':[a['receipt']],
         'total_receipts_across_phases':22,'total_charged_seconds_across_phases':7372,'reservations':0})
    actual=json.loads((run/'run_manifest_final.json').read_text())
    missing={'PREP_MANIPULATION_CHECK.csv':'No prep model or probe generation: E018 retention gate failed.',
             'FOUR_CELL_RESULTS.csv':'Four children were not trained; no interaction estimate.',
             'PER_PROBLEM_RESULTS.jsonl':'No arithmetic discovery outputs. E018 observed-dev pairs are in e018_audit_r1/per_problem.jsonl.'}
    manifest={'status':'STOPPED_AT_PRESPECIFIED_E018_GATE','built_from_source_commit':source,
              'execution_source_commit':actual['source_commit'],'aliases':ALIASES,
              'model':actual['model'],'adapter':actual['adapter'],'seeds':{'training':17,'data':20260916,'bootstrap':17020},
              'completed':['C021 CPU candidate audit','E018 one fixed learning/retention calibration','independent160-stream audit','complete E018 adapter export','provider shutdown'],
              'not_executed':['arithmetic model calibration','both preps','four main cells','optional Repeat','single-C0 fallback'],
              'not_executed_reason':'E018 retained34/39 original successes; fixed90% screen requires at least36/39.',
              'source_quality_disposition':'E018_QUALITY_REVIEW.json','raw_run_directory':str(run),
              'full_runtime_manifest':str(run/'run_manifest_final.json'),'parent':'Original pinned base, not E015',
              'optimizer_reset':True,'updates':64,'supervised_tokens':77192,'free_generations':160,
              'actual_gated_result':a,'missing_planned_artifacts':missing,
              'entrypoint_command':'PYTHONPATH=.local/thu_deps PINNED_PYTHON -m experiments.thursday_probe.e018 launch --snapshot PINNED_MODEL_SNAPSHOT --ledger HISTORICAL_LEDGER --power-on-at-utc 2026-09-16T18:16:00Z'}
    dump(ROOT/'RUN_MANIFEST.json',manifest)
    with (ROOT/'FAILURE_BREAKDOWN.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['scope','endpoint','kind','value','count']);writer.writeheader()
        for r in csv.DictReader((ROOT/'e018_audit_r1/failure_breakdown.csv').open()):
            writer.writerow({'scope':'E018_observed_GSM8K_dev',**r})
    bc=read_jsonl(run/'base.jsonl');fc=read_jsonl(run/'final.jsonl')
    gained=[x for x,y in zip(bc,fc) if not x['task_score']['task_answer_correct'] and y['task_score']['task_answer_correct']]
    gp=Counter(x['task_score']['marked']['status'] for x in gained)
    dump(ROOT/'E018_GAIN_BREAKDOWN.json',{'gained_questions':len(gained),'baseline_parse_status':dict(gp),
        'interpretation':'11/17 gains began with missing/unresolved marked answers; this suggests format is a component, not a causal decomposition or proof all11 had correct reasoning.'})
    plots(a,m,candidate)
    brief=f'''# Thursday decision brief — September17, 2026

Execution ended at the prespecified E018 retention gate. The four-cell arithmetic
experiment was not run; there is no interaction or familiarity result.

| E018 measure | Original base | Final LoRA |
|---|---:|---:|
| Correct, observed development | {a['base_correct']}/64 | {a['adapter_correct']}/64 |
| Parsed final answer | 49/64 | 64/64 |
| Native EOS | 47/64 | 64/64 |
| Actual length cap | 1/64 | 0/64 |
| Reference NLL,253 anchors | {a['before_nll']:.6f} | {a['after_nll']:.6f} |

There are{a['gained']} gained,{a['lost']} lost,{a['both_correct']} both-correct and8 both-wrong
questions. Net change is{100*a['paired_accuracy_difference']:.2f} percentage points
(paired-question bootstrap95% interval{100*a['paired_accuracy_difference_CI95'][0]:.2f}
to{100*a['paired_accuracy_difference_CI95'][1]:.2f}). Retention is
{a['both_correct']}/39={100*a['retained_fraction']:.2f}%, below90%; at least36 retained
successes were required. This is an operational failed screen, not a statistical
proof of population-level harm. Its descriptive retention interval spans
{100*a['retained_fraction_CI95'][0]:.2f}–{100*a['retained_fraction_CI95'][1]:.2f}%.

Reference NLL fell{100*a['nll_reduction_fraction']:.2f}%. Base parameter bytes were
unchanged; the18,464,768-parameter adapter changed and was saved/reloaded exactly
in CPU tests and independently preserved after GPU training. All160 raw streams
pass local audits, and all64 zero-adapter base streams match E017. All five lost
outputs have valid EOS/parse and substantive quantity/arithmetic errors. Among
17 gains,11 had missing/unresolved base answer markers; do not label the full
net gain a reasoning improvement. The fixed32 training-quality audit also found
one erroneous speed/time reference, disclosed and retained without backfill.

## Data readiness

All three prespecified candidate interfaces support256 train,16 construction
calibration and96 discovery problems, plus independent96 probes and32 prefix
pairs. Primary subtraction-to-multiplication main tokens are265,744 Surface
versus265,664 Paths (residual{100*primary['main_token_residual_fraction']:.3f}%);
prep tokens differ{100*primary['prep_token_residual_fraction']:.2f}%, approximately
matched. Targets range{primary['target_range'][0]}–{primary['target_range'][1]},
including{primary['train_targets_above40']}/256 above40. No common-length question
filter or reserved-question read occurred. Fine structure total variation is
{100*primary['fine_global_total_variation']['structures']:.2f}%; A/B identity-operation
paths occur on{primary['train_identity_path_counts']['A']}/{primary['train_identity_path_counts']['B']}
questions. These residuals remain interpretation limits. Model nonsaturation and
the prep manipulation have not been tested.

## Decision for the next revision

Keep the failed screen and avoid a same-run retry or post-hoc threshold change.
If the original preservation requirement remains the priority, propose one new
bounded calibration changing only LoRA peak LR from1e-4 to5e-5, retaining the
same fixed corpus/dose and recording the known label defect. Do not combine an
LR change with data corrections, extra epochs or another model. This is a
proposal, not an executed experiment or a promise the gate will pass.

Alternatively, the owner may explicitly revise the next protocol toward a
task-matched arithmetic calibration before the two prep models. That would be
a changed decision rule and must not relabel E018 as passed. Freeze treatment
of identity paths and fine-structure imbalance before any discovery outcomes.
The one-seed2×2, if later run, remains an exploratory decision experiment.

## Preservation and cost

Training took{cost['training_seconds']:.1f}s; the guarded process charged
{cost['charged_model_process_seconds']}s. The historical21-receipt ledger stays
unchanged;22 receipts across phases now total7,372 process seconds. Whole-rental
proxy is{seconds/60:.1f}minutes/about CNY{cost['whole_window_proxy_cost']:.2f} at
CNY7.98/hour, including setup/export; it is not an invoice. Provider shutdown
is verified. All18 output/checkpoint files are independently copied, including
the complete73.92MB adapter package. E015's incomplete independent full-weight
backup remains a separate preservation obligation; its instance was not deleted.

Not generated: PREP_MANIPULATION_CHECK.csv, FOUR_CELL_RESULTS.csv and arithmetic
PER_PROBLEM_RESULTS.jsonl, because their runs did not occur. Actual E018 pairs:
[per_problem.jsonl](e018_audit_r1/per_problem.jsonl). Supporting records:
[run manifest](RUN_MANIFEST.json), [data audit](DATA_AUDIT.json),
[cost](COST_REPORT.json), [lost-case review](E018_LOST_CASE_REVIEW.json).

![E018 calibration](E018_CALIBRATION.png)
'''
    with (ROOT/'THURSDAY_BRIEF.md').open('x') as f:f.write(brief)
    return {'status':manifest['status'],'gate_passed':a['passed'],'figures':2,'estimated_rental_proxy_cny':cost['whole_window_proxy_cost']}


def plots(a,m,candidates):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(1,3,figsize=(12,3.8),layout='constrained')
    ax[0].bar(['Base','LoRA'],[a['base_correct'],a['adapter_correct']],color=['#6A7B8C','#237E9E'])
    ax[0].set_ylim(0,64);ax[0].set_ylabel('Correct / 64 observed dev questions');ax[0].set_title('Net gain: +18.75 percentage points')
    for i,v in enumerate([a['base_correct'],a['adapter_correct']]):ax[0].text(i,v+1,str(v),ha='center')
    vals=[a['both_correct'],a['gained'],a['lost'],m['both_wrong']]
    ax[1].bar(['Both correct','Gained','Lost','Both wrong'],vals,color=['#237E9E','#4C9C72','#CB605A','#9A9EA3'])
    ax[1].tick_params(axis='x',rotation=22);ax[1].set_ylim(0,40)
    ax[1].set_title('Retention 34/39 = 87.2%; gate 90%')
    for i,v in enumerate(vals):ax[1].text(i,v+.6,str(v),ha='center')
    ax[2].bar(['Before','After'],[a['before_nll'],a['after_nll']],color=['#6A7B8C','#237E9E'])
    ax[2].set_ylabel('Reference NLL / supervised token');ax[2].set_ylim(0,.6);ax[2].set_title('Reference loss fell 45.9%')
    for i,v in enumerate([a['before_nll'],a['after_nll']]):ax[2].text(i,v+.012,f'{v:.3f}',ha='center')
    fig.suptitle('E018: learning observed; preservation screen failed',fontsize=14)
    fig.savefig(ROOT/'E018_CALIBRATION.png',dpi=180);plt.close(fig)
    ps=read_jsonl(ROOT/'data_r1/train_problems.jsonl');hist=Counter((r['target']//10)*10 for r in ps)
    fig,ax=plt.subplots(figsize=(7.4,3.3),layout='constrained')
    xs=list(range(10,101,10));ys=[hist[x] for x in xs]
    ax.bar([str(x)+'–'+str(x+9) if x<100 else '100' for x in xs],ys,color='#237E9E')
    ax.tick_params(axis='x',rotation=25);ax.set_ylabel('Training questions');ax.set_xlabel('Target value')
    ax.set_title('C021 primary pool: 256 questions; no common-length question filter')
    for i,v in enumerate(ys):ax.text(i,v+.3,str(v),ha='center',fontsize=9)
    fig.savefig(ROOT/'DATA_COVERAGE.png',dpi=180);plt.close(fig)


if __name__=='__main__':print(json.dumps(build(),indent=2))
