"""CPU-only report from preserved real partial results; never imports torch."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import platform

from src.countdown_smoke import safe_parse, value

ROOT=Path('experiments/thursday_probe_v2')
RUN=Path('runs/thursday_arithmetic_v2_r2')
AUDIT=RUN/'partial_independent_audit'
RELEASE=ROOT/'release_r2'


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,obj):
    with path.open('x') as stream:json.dump(obj,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
def leaves(tree):return [tree[1]] if tree[0]=='n' else leaves(tree[1])+leaves(tree[2])


def build():
    outputs=[ROOT/name for name in ('THURSDAY_BRIEF_v2.md','CALIBRATION_TASK_BREAKDOWN.csv',
        'CALIBRATION_CONSTRUCTION_ERROR_AUDIT.json','ARITHMETIC_V2_PARTIAL_RESULTS.png','PARTIAL_FIGURE_PROVENANCE.json')]
    if any(path.exists() for path in outputs):raise FileExistsError('Do not overwrite report artifacts')
    sources=[RELEASE/'calibration.jsonl',RUN/'C0_calibration.jsonl',RUN/'calibration_calibration.jsonl',
        RUN/'C0_probes.jsonl',RUN/'C0_discovery_greedy.jsonl',RUN/'run_manifest_final.json',RUN/'measured_admission.json',
        AUDIT/'summary.json',AUDIT/'CALIBRATION_RESULTS.json',AUDIT/'C0_PROBE_RESULTS.json',
        AUDIT/'failure_breakdown.json',ROOT/'COST_REPORT_v2.json']
    audit=read(AUDIT/'summary.json');cost=read(ROOT/'COST_REPORT_v2.json');manifest=read(RUN/'run_manifest_final.json')
    if audit['status']!='partial_completed_measurements_independently_verified' or manifest['status']=='completed':
        raise ValueError('Independently audited incomplete phase required')
    if not cost['provider_shutdown_confirmed']:raise ValueError('Close the powered-on window before reporting')
    if any(r['status']!=('completed' if r['state']=='calibration' else 'not_run') for r in manifest['runs']):
        raise ValueError('This brief is specifically the post-E030 resource stop')
    for name,digest in audit['completed_prediction_files_sha256'].items():
        if sha(RUN/(name+'.jsonl'))!=digest:raise ValueError('Audited predictions changed')
    if audit['final_manifest_sha256']!=sha(RUN/'run_manifest_final.json'):
        raise ValueError('Audited manifest changed')
    definitions=rows(RELEASE/'calibration.jsonl')
    before={r['problem_id']:r for r in rows(RUN/'C0_calibration.jsonl')}
    after={r['problem_id']:r for r in rows(RUN/'calibration_calibration.jsonl')}
    if set(before)!=set(after) or set(before)!={r['problem_id'] for r in definitions}:raise ValueError('Paired calibration identities differ')
    table=[]
    for split in ('all','fit','check'):
        for task in ('construct','compute'):
            ids=[r['problem_id'] for r in definitions if r['task']==task and (split=='all' or r['calibration_split']==split)]
            pairs=[(before[pid],after[pid]) for pid in ids]
            record=dict(split=split,task=task,questions=len(ids),
                both_correct=sum(a['score']['correct'] and b['score']['correct'] for a,b in pairs),
                gained_correct=sum(not a['score']['correct'] and b['score']['correct'] for a,b in pairs),
                lost_correct=sum(a['score']['correct'] and not b['score']['correct'] for a,b in pairs),
                neither_correct=sum(not a['score']['correct'] and not b['score']['correct'] for a,b in pairs))
            for label,records in (('before',[a for a,_ in pairs]),('after',[b for _,b in pairs])):
                record[label+'_correct']=sum(r['score']['correct'] for r in records)
                record[label+'_accuracy']=record[label+'_correct']/len(ids)
                record[label+'_parsed']=sum(r['score']['parsed'] for r in records)
                record[label+'_native_eos']=sum(r['stop']['stop_reason']=='native_eos' for r in records)
                record[label+'_length_cap']=sum(r['stop']['stop_reason']=='length_cap' for r in records)
            table.append(record)
    with (ROOT/'CALIBRATION_TASK_BREAKDOWN.csv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,list(table[0]),lineterminator="\n");writer.writeheader();writer.writerows(table)

    construction=[];counts=Counter()
    for problem in sorted(definitions,key=lambda r:r['problem_id']):
        if problem['task']!='construct':continue
        prediction=after[problem['problem_id']];score=prediction['score']
        expression=score['expression'];actual=None;resources=None;target=None
        if not score['parsed']:category='unparsed'
        else:
            tree=safe_parse(expression);actual=value(tree)
            resources=Counter(leaves(tree))==Counter(problem['numbers']);target=actual==problem['target']
            category=('correct' if resources and target else 'wrong_target_only' if resources
                      else 'wrong_resources_only' if target else 'wrong_target_and_resources')
        if (category=='correct')!=score['correct']:raise ValueError('Independent expression classification disagrees')
        counts[category]+=1
        construction.append(dict(problem_id=problem['problem_id'],split=problem['calibration_split'],
            task=problem['task'],numbers=problem['numbers'],target=problem['target'],prompt=problem['prompt'],
            reference_response=problem['response'],answer_segment=prediction['stop']['answer_segment'],
            stop_reason=prediction['stop']['stop_reason'],original_score=score,
            exact_expression_value=str(actual) if actual is not None else None,
            exact_number_multiset_matches=resources,target_value_matches=target,classification=category))
    examples=[r for r in construction if r['classification']!='correct'][:2]
    dump(ROOT/'CALIBRATION_CONSTRUCTION_ERROR_AUDIT.json',dict(
        scope='Post-E030 construct questions only; unchanged final-expression scoring, exact AST/Fraction recomputation.',
        questions=len(construction),error_partition=dict(counts),records=construction,
        example_selection='First two incorrect construct questions in fixed problem_id lexicographic order.',
        fixed_lexicographic_examples=examples,
        trace_caution='A trace_status of inconsistent can reflect disagreement with the requested target; it does not by itself establish an incorrect intermediate arithmetic equation.'))

    cal=read(AUDIT/'CALIBRATION_RESULTS.json');probes=read(AUDIT/'C0_PROBE_RESULTS.json')
    discovery=next(r for r in read(AUDIT/'failure_breakdown.json') if r['evaluation']=='C0_discovery_greedy')
    admission=read(RUN/'measured_admission.json');paired=cal['paired_transition_counts']
    decoded=[rows(RUN/(name+'.jsonl')) for name in audit['completed_evaluations']]
    slowest_decode_rate=max(sum({r['batch_index']:r['batch_seconds'] for r in records}.values())/len(records) for records in decoded)
    window_minutes,window_seconds=divmod(round(cost['whole_window_proxy_seconds']),60)
    original=cal['original_results']['record']
    fit_nll=(original['reference_nll_before']['nll'],original['reference_nll_after']['nll'])
    check_nll=(original['check_reference_nll_before']['nll'],original['check_reference_nll_after']['nll'])
    def result(split,task):return next(r for r in table if r['split']==split and r['task']==task)
    groups=[('fit','construct'),('check','construct'),('fit','compute'),('check','compute')]

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
        'axes.spines.right':False,'savefig.dpi':180,'axes.titleweight':'bold'})
    fig=plt.figure(figsize=(14.4,8.0),facecolor='white')
    fig.text(.06,.945,'PARTIAL — arithmetic engineering calibration',fontsize=21,weight='bold',color='#14243b')
    fig.text(.06,.897,'E030 completed  |  E031–E036 not run  |  No prep or factorial result',fontsize=13,color='#9a3412')
    left=fig.add_axes([.07,.37,.49,.43]);right=fig.add_axes([.67,.37,.28,.43])
    base,trained='#94a3b8','#2563eb';x=np.arange(4);width=.34
    for offset,label,color in ((-width/2,'before',base),(width/2,'after',trained)):
        values=[100*result(s,t)[label+'_accuracy'] for s,t in groups]
        left.bar(x+offset,values,width,color=color,label='C0' if label=='before' else 'E030',zorder=3)
        for pos,(s,t),height in zip(x+offset,groups,values):
            row=result(s,t);left.text(pos,height+2,f"{row[label+'_correct']}/{row['questions']}",ha='center',fontsize=10,color='#14243b')
    left.set(xticks=x,xticklabels=['Construct\nfit','Construct\ncheck','Compute\nfit','Compute\ncheck'],
        ylim=(0,117),yticks=[0,25,50,75,100],ylabel='Correct answers (%)',title='Task separation changes the interpretation')
    left.grid(axis='y',color='#e2e8f0',zorder=0);left.legend(frameon=False,ncol=2,loc='upper left')
    metrics=[('native_eos','Native EOS'),('parsed','Parsed'),('length_caps','Length cap')];x2=np.arange(3)
    for offset,label,color in ((-width/2,'before',base),(width/2,'after',trained)):
        values=[paired['all'][label][key] for key,_ in metrics]
        right.bar(x2+offset,values,width,color=color,zorder=3)
        for pos,height in zip(x2+offset,values):right.text(pos,height+1.2,str(height),ha='center',fontsize=10,color='#14243b')
    right.set(xticks=x2,xticklabels=[label for _,label in metrics],ylim=(0,56),yticks=[0,12,24,36,48],
        ylabel='Outputs out of 48',title='Termination and format improve')
    right.grid(axis='y',color='#e2e8f0',zorder=0)
    right.text(.5,-.22,'Lower is better for length caps.',ha='center',transform=right.transAxes,color='#475569',fontsize=10)
    notes=[(.07,'Reference-answer NLL',f'Fit: {fit_nll[0]:.4f} → {fit_nll[1]:.4f}\nCheck: {check_nll[0]:.4f} → {check_nll[1]:.4f}'),
           (.39,'C0 discovery: construction',f"{int(discovery['pass_at_1']*discovery['questions'])}/{discovery['questions']} correct (greedy)\n{discovery['stop_reasons'].get('length_cap',0)}/{discovery['questions']} reach the length cap"),
           (.70,'Resource forecast stopped the phase',f"{admission['projected_process_seconds']:,.0f} s forecast vs {admission['remaining_process_seconds']:,.0f} s remaining\nFull-grid runtime was not observed.")]
    for xpos,title,body in notes:
        fig.text(xpos,.235,title,fontsize=12,weight='bold',color='#14243b')
        fig.text(xpos,.155,body,fontsize=11,color='#334155',linespacing=1.7)
    fig.text(.07,.052,'One fixed seed. Separate engineering adapter; no generalization claim. All caps and parsing failures remain in the denominators.',
             fontsize=10,color='#475569')
    figure=ROOT/'ARITHMETIC_V2_PARTIAL_RESULTS.png';fig.savefig(figure,facecolor='white');plt.close(fig)

    text=['# Thursday brief — PARTIAL arithmetic v2','',
        '**E030 completed; E031–E036 were not run.** The registered conservative runtime forecast stopped the phase. No prep manipulation or factorial effect was measured. E018 remains failed and was not rerun.','',
        '| Calibration task | C0 correct | E030 correct |','|---|---:|---:|']
    for split,task in groups:
        row=result(split,task);text.append(f"| {task.capitalize()} / {split} | {row['before_correct']}/{row['questions']} | {row['after_correct']}/{row['questions']} |")
    text.extend(['',f"Overall accuracy was {paired['all']['before']['correct']}/48 → {paired['all']['after']['correct']}/48: two fit gains, no losses, and no check-set gains. These mixed-task totals are **not construction accuracy**. Construction improved only from 0/8 to 1/8 on fit; check construction stayed 0/8.",
        '',f"Native EOS increased {paired['all']['before']['native_eos']}/48 → {paired['all']['after']['native_eos']}/48; parsed outputs {paired['all']['before']['parsed']}/48 → {paired['all']['after']['parsed']}/48; caps {paired['all']['before']['length_caps']}/48 → {paired['all']['after']['length_caps']}/48. Fit reference NLL fell {fit_nll[0]:.4f} → {fit_nll[1]:.4f}; check NLL {check_nll[0]:.4f} → {check_nll[1]:.4f}. This supports learning of the reference-answer distribution and termination/format, not successful free construction or generalization. The calibration adapter is independent of the scientific parents.",
        '', '**Construction failures:** '+', '.join(f"{counts.get(key,0)} {label}" for key,label in [('wrong_target_only','target-only errors'),('wrong_resources_only','number-use-only error'),('wrong_target_and_resources','combined errors'),('unparsed','unparsed outputs')])+'. The two fixed lexicographic examples use the required numbers once but evaluate to '+f"{examples[0]['exact_expression_value']} instead of {examples[0]['target']}, and {examples[1]['exact_expression_value']} instead of {examples[1]['target']}.",
        '', '**C0 only:** sampled pass@1 (32 questions/group, n=4) was '+', '.join(f"{r['category']} {100*r['pass_at_1']:.2f}%" for r in probes)+f". Discovery greedy was 0/{discovery['questions']}, with {discovery['stop_reasons']['length_cap']} caps, {discovery['stop_reasons']['new_problem_boundary']} boundary stops and {discovery['stop_reasons']['native_eos']} EOS stops. There is no trained-parent comparison.",
        '',f"**Resource stop:** the forecast was {admission['projected_process_seconds']:,.0f}s versus {admission['remaining_process_seconds']:,.0f}s remaining. It extrapolates the slowest measured base view ({slowest_decode_rate:.6f}s/output) to all remaining generations and adds the registered safety margin. This is not evidence that the grid actually needs {admission['projected_process_seconds']/3600:.1f} hours. There were {cost['actual_generation_attempts']} actual generations: {cost['unique_completed_evaluation_outputs']} unique completed results plus {cost['fault_duplicate_generations']} fault repeats; {cost['unrecoverable_fault_output_records']} interrupted outputs were not recoverable. Charged process time: {cost['phase_process_charged_seconds']:,}s. Provider shutdown: {cost['shutdown_confirmed_by_utc']}; powered-on proxy {window_minutes}m{window_seconds:02d}s, CNY{cost['whole_window_proxy_cost_cny']:.4f}, not an invoice.",
        '', '**Next proposal — resource plan only:** reuse completed evidence; revise the finite resource allowance and stage-specific throughput forecast. Run both fixed prep recipes from the original C0 initialization and measure their prescribed probe throughput, then execute the complete four-cell comparison under a common recipe. Keep resource admission independent of accuracy/significance, and retain export/shutdown reserves. No automatic startup, no E018/E030 rerun, and no inheritance of either calibration adapter.',
        '', '![Partial calibration results](ARITHMETIC_V2_PARTIAL_RESULTS.png)'])
    with (ROOT/'THURSDAY_BRIEF_v2.md').open('x') as stream:stream.write('\n'.join(text)+'\n')
    dump(ROOT/'PARTIAL_FIGURE_PROVENANCE.json',dict(status='actual_partial_results_only',
        generator='experiments/thursday_probe_v2/build_partial_report.py',generator_sha256=sha(Path(__file__)),
        input_files_sha256={str(path):sha(path) for path in sources},
        output_files_sha256={str(path):sha(path) for path in outputs[:-1]},
        python_version=platform.python_version(),matplotlib_version=matplotlib.__version__,numpy_version=np.__version__,
        manual_score_entry=False,new_model_calls=0,confidence_or_significance_claims=False,
        note='Counts recomputed from raw completed predictions; source token/stop/scoring and new batch journals were independently audited. Fault-only outputs are excluded from scientific denominators.'))
    return dict(task_breakdown=table,construction_error_partition=dict(counts),figure=str(figure))


if __name__=='__main__':print(json.dumps(build(),indent=2))
