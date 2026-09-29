"""Build discussion artifacts exclusively from audited measured result tables."""
import argparse
import csv
import json
from pathlib import Path

from experiments.thursday_probe.common import dump
from experiments.thursday_probe_v2.config import ROOT,OUT,STATES
from src.sft_data import sha256_file


def read_csv(name):
    with (ROOT/name).open() as f:return list(csv.DictReader(f))


def build(out=OUT):
    out=Path(out)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    audit=json.loads((out/'independent_audit/summary.json').read_text())
    cost=json.loads((ROOT/'COST_REPORT_v2.json').read_text())
    if audit['status']!='all_raw_streams_independently_verified':raise ValueError('Independent audit required')
    four=read_csv('FOUR_CELL_RESULTS.csv');prep=read_csv('PREP_MANIPULATION_CHECK.csv');sent=read_csv('POST_MAIN_SENTINEL.csv')
    cal=json.loads((ROOT/'ARITH_CALIBRATION_RESULTS.json').read_text())
    def result(state,group='full',view='discovery_sampled',metric='pass_at_1'):
        return next(r for r in four if r['state_or_contrast']==state and r['subgroup']==group and r['view']==view and r['metric']==metric)
    def pct(x):return f'{100*float(x):.2f}%'
    def interval(r):return f"[{100*float(r['question_ci_low']):.2f}, {100*float(r['question_ci_high']):.2f}] pp"
    manip=json.loads((out/'independent_audit/manipulation_contrasts.json').read_text())
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    fig,axes=plt.subplots(1,3,figsize=(15,4.6),layout='constrained')
    cats=('atomic','target','control');colors=('#64748b','#2563eb','#d97706')
    for i,state in enumerate(('C0','C','B')):
        ys=[float(next(r['pass_at_1'] for r in prep if r['state']==state and r['category']==c)) for c in cats]
        axes[0].bar(np.arange(3)+(i-1)*.24,ys,width=.22,label=state,color=colors[i])
    axes[0].set(xticks=np.arange(3),xticklabels=cats,ylim=(0,1),ylabel='Mean per-question pass@1',title='Prep probes: 32 questions/group, n=4')
    axes[0].legend(frameon=False)
    ys=np.array([float(result(s)['estimate']) for s in STATES])
    lows=np.array([float(result(s)['question_ci_low']) for s in STATES]);highs=np.array([float(result(s)['question_ci_high']) for s in STATES])
    axes[1].bar(np.arange(6),ys,color=['#94a3b8','#94a3b8','#2563eb','#60a5fa','#d97706','#fbbf24'])
    axes[1].errorbar(np.arange(6),ys,yerr=[ys-lows,highs-ys],fmt='none',color='#111827',capsize=3)
    axes[1].set(xticks=np.arange(6),xticklabels=STATES,ylim=(0,1),title='Discovery: 96 questions, n=4\n95% paired-question bootstrap intervals')
    for i,cat in enumerate(cats):
        gaps=[]
        for c,b in (('C','B'),('C-S','B-S'),('C-P','B-P')):
            means={s:float(next(r['pass_at_1'] for r in sent if r['state']==s and r['category']==cat)) for s in (c,b)}
            gaps.append(means[b]-means[c])
        axes[2].plot(range(3),gaps,'o-',label=cat,color=colors[i])
    axes[2].axhline(0,color='#94a3b8',lw=1)
    axes[2].set(xticks=range(3),xticklabels=['Prep','After Surface','After Paths'],ylabel='Bridge minus control pass@1',title='Fixed sentinel: 16 questions/group, n=2')
    axes[2].legend(frameon=False)
    fig.suptitle('Arithmetic v2: one fixed seed combination; recipe effects, not an isolated skill mechanism',fontsize=13)
    for ext in ('png','pdf'):
        path=ROOT/('ARITHMETIC_V2_RESULTS.'+ext)
        if path.exists():raise FileExistsError('Do not overwrite a published figure')
        fig.savefig(path)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    for i,group in enumerate(('full','target_nondegenerate','target_degenerate')):
        r=result('interaction',group);mean=float(r['estimate'])*100
        lo,hi=float(r['question_ci_low'])*100,float(r['question_ci_high'])*100
        ax.errorbar(mean,i-.06,xerr=[[mean-lo],[hi-mean]],fmt='o',color='#2563eb',capsize=4,label='Question bootstrap' if i==0 else None)
        if r['cluster_ci_low']:
            lo,hi=float(r['cluster_ci_low'])*100,float(r['cluster_ci_high'])*100
            ax.hlines(i+.08,lo,hi,color='#d97706')
            ax.plot(mean,i+.08,'s',color='#d97706',label='Reference-B template clusters' if i==0 else None)
    ax.axvline(0,color='#94a3b8',lw=1)
    ax.set(yticks=range(3),yticklabels=['Full (96)','Target nondegenerate (79)','Target degenerate (17)'],xlabel='Interaction I (percentage points)',title='Reference-defined subgroups; 95% bootstrap intervals')
    subgroup_path=ROOT/'ARITHMETIC_V2_SUBGROUPS.png'
    if subgroup_path.exists():raise FileExistsError('Do not overwrite a published figure')
    ax.legend(frameon=False);fig.savefig(subgroup_path);plt.close(fig)
    table=['| State | Sampled pass@1 | pass@4 | Greedy |','|---|---:|---:|---:|']
    for s in STATES:
        table.append(f"| {s} | {pct(result(s)['estimate'])} | {pct(result(s,metric='pass_at_4')['estimate'])} | {pct(result(s,view='discovery_greedy')['estimate'])} |")
    lines=['# Thursday discussion — arithmetic v2',
        '', 'All figures below are recalculated from independently audited raw token streams. This is discovery evidence with one seed combination.',
        '', '**Historical E018:** learning and output usability improved, but34/39 retention failed its90% threshold. That result remains unchanged and its adapter was not reused.',
        '', f"**Arithmetic calibration:** fit accuracy {pct(cal['fit_check']['fit']['before']['pass_at_1'])} → {pct(cal['fit_check']['fit']['after']['pass_at_1'])}; check accuracy {pct(cal['fit_check']['check']['before']['pass_at_1'])} → {pct(cal['fit_check']['check']['after']['pass_at_1'])}. Fit reference NLL {cal['reference_nll_before']['nll']:.4f} → {cal['reference_nll_after']['nll']:.4f}. This adapter is separate from both prep parents.",
        '',f"**Prep manipulation:** bridge−control target={100*manip['delta_target']:.2f}pp, control={100*manip['delta_control']:.2f}pp, D={100*manip['D']:.2f}pp. Raw C0/C/B means are in PREP_MANIPULATION_CHECK.csv. D is descriptive; it is not a competence certificate or a cell-selection criterion.",
        '',*table,'',f"**Primary contrasts:** delta_C={100*float(result('delta_C')['estimate']):.2f}pp, delta_B={100*float(result('delta_B')['estimate']):.2f}pp, I={100*float(result('interaction')['estimate']):.2f}pp; I's question-bootstrap interval is {interval(result('interaction'))}. Template-cluster intervals and all paired question gains/losses are also provided.",
        '',f"**Reference subgroup sensitivity:** nondegenerate I={pct(result('interaction','target_nondegenerate')['estimate'])}; degenerate I={pct(result('interaction','target_degenerate')['estimate'])}. These are fixed79/17-question subgroups, not filters chosen from model output.",
        '', '**Limits and next decision:** inspect prep and sentinel separation together before describing students as differently prepared. If separation is weak, retain the factorial result and redesign the intervention/probes. If a candidate interaction persists across both bootstrap views and nondegenerate questions, the next informative experiment is a preregistered complete2×2 replication with a fresh prep/training seed, followed by structure/dose controls. None starts automatically. Fine-structure TV8.98%, prep-token residual2.75%, formatting/stopping changes and single-seed uncertainty limit causal and novelty claims.',
        '',f"**Resources:** {audit['generations']} unique audited evaluation outputs (including reused calibration); actual generation attempts are counted separately in the cost report. Cost/whole-window/process/export/provider facts are recorded in COST_REPORT_v2.json; provider shutdown confirmed={cost.get('provider_shutdown_confirmed','unavailable')}. No optional prefix or n=8 expansion, final-test evaluation or extra machine.",
        '', '![Measured prep, discovery and sentinel results](ARITHMETIC_V2_RESULTS.png)',
        '', '![Reference-subgroup interaction intervals](ARITHMETIC_V2_SUBGROUPS.png)']
    with (ROOT/'THURSDAY_BRIEF_v2.md').open('x') as f:f.write('\n'.join(lines)+'\n')
    dump(ROOT/'FIGURE_PROVENANCE.json',dict(inputs={name:sha256_file(ROOT/name) for name in
        ('FOUR_CELL_RESULTS.csv','PREP_MANIPULATION_CHECK.csv','POST_MAIN_SENTINEL.csv','ARITH_CALIBRATION_RESULTS.json','COST_REPORT_v2.json')},
        generator='experiments.thursday_probe_v2.report',run_directory=str(out),
        audit_summary_sha256=sha256_file(out/'independent_audit/summary.json'),manual_score_entry=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',default=str(OUT))
    args=parser.parse_args();build(args.run_dir)
