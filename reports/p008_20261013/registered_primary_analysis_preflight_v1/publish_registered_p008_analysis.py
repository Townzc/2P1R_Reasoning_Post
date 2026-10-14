"""PREPARED: publish complete registered tables and plots, pending external G3.

Requires the new all-cell local analysis and all eight complete T8 G3 packets.
No scoring, new confidence procedure, model calls, or immutable packet changes.
"""
from pathlib import Path
import csv, json, shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments.sft_allocation_midpoint.common import read, dump, sha, manifest

r = Path(__file__).resolve().parent
source = r/'registered_analysis_r1/RESULTS.json'
data = read(source)
out = Path('reports/p008_20261013/registered_primary_results_v1')
assert not out.exists(), 'Existing immutable publication; preserve and reconcile'
assert len(data['cells']) == 19 and data['registered_main_contrasts'] == 18
assert data['bootstrap']['draws'] == 10000 and data['bootstrap']['seed'] == 20261013
assert data['external_review'] == 'pending' and data['original_N2_passed'] is False
for row in data['cells']:
    if row.get('training_multiple') == 8:
        packet = Path('reports/p008_20261013/t8_results_v1')/row['logical_run_id']
        published = read(packet/'SUMMARY.json')
        assert published['correct'] == row['correct'] and published['state_sha256']
        assert published['local_oracle_passed'] and published['provider_released']
        assert (packet/'MANIFEST.json').is_file()
out.mkdir(exist_ok=False)
shutil.copyfile(source,out/'RESULTS.json')
for name in ('prepare_registered_p008_analysis.py','publish_registered_p008_analysis.py'):
    shutil.copyfile(r/name,out/name)
shutil.copyfile('scripts/p008_paired_question_analysis.py',out/'p008_paired_question_analysis.py')
cells = data['cells']
with (out/'ALL_CELLS.csv').open('x',newline='') as f:
    columns = list(dict.fromkeys(k for row in cells for k in row))
    writer = csv.DictWriter(f,fieldnames=columns)
    writer.writeheader();writer.writerows(cells)
with (out/'ALL_CONTRASTS.csv').open('x',newline='') as f:
    fields = ('name','kind','draw','estimate_pp','CI95_low_pp','CI95_high_pp','observed_draw_range_pp')
    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
    for row in data['contrasts']:
        a={k:row[k] for k in fields[:4]}
        a['CI95_low_pp'],a['CI95_high_pp']=row['conditional_question_percentile_CI95_pp']
        a['observed_draw_range_pp']=json.dumps(row.get('observed_draw_range_pp'))
        writer.writerow(a)
lookup={x['name']:x for x in data['contrasts']}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.hashsalt':'p008-registered-primary-v1'})
colors={1:'#246b9e',2:'#b36527'}
def finish(fig,stem):
    fig.savefig(out/(stem+'.png'),dpi=180)
    fig.savefig(out/(stem+'.svg'),metadata={'Date':None})
    plt.close(fig)
def style(ax):
    ax.axhline(0,color='#89949d',linewidth=1)
    ax.grid(axis='y',color='#e7ebef',linewidth=.8);ax.set_axisbelow(True)
    for side in ('top','right'):ax.spines[side].set_visible(False)
def interval(ax,x,item,color,marker):
    low,high=item['conditional_question_percentile_CI95_pp']
    ax.vlines(x,low,high,color=color,linewidth=1.5)
    ax.hlines([low,high],x-.025,x+.025,color=color,linewidth=1.5)
    ax.plot(x,item['estimate_pp'],marker=marker,color=color,markersize=7)

fig,axes=plt.subplots(1,2,figsize=(11,6.2),sharey=True)
fig.subplots_adjust(left=.095,right=.975,top=.78,bottom=.29,wspace=.12)
for ax,p in zip(axes,(0,4)):
    style(ax)
    for d in (1,2):
        items=[lookup[f'D{d}_Delta_p{p}_B{b}'] for b in (1,8)]
        xs=[i+(-.045 if d==1 else .045) for i in (0,1)]
        ax.plot(xs,[v['estimate_pp'] for v in items],color=colors[d],alpha=.6,linewidth=1)
        for x,item in zip(xs,items):interval(ax,x,item,colors[d],'o' if d==1 else 's')
    ax.set_title('Problem price '+('0' if p==0 else '4m'))
    ax.set_xticks([0,1],['B1 / T1','B8 / T8']);ax.set_xlim(-.3,1.3)
axes[0].set_ylabel('Depth minus breadth (percentage points)')
fig.suptitle('P008: allocation preference along the joint scaling path',fontsize=17,y=.95)
fig.text(.5,.885,'Same acquisition cap within each comparison; B and T increase together between columns.',ha='center',fontsize=10)
handles=[plt.Line2D([0],[0],marker='o' if d==1 else 's',color=colors[d],label=f'Draw {d}') for d in (1,2)]
fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.18),ncol=2,frameon=False)
fig.text(.05,.14,'95% pointwise paired-question bootstrap intervals: 10,000 resamples, seed 20261013.',fontsize=10)
fig.text(.05,.10,'Conditional on these models and pools; not uncertainty across training seeds or a procurement population.',fontsize=10)
fig.text(.05,.06,'Both draws use initialization seed 17. All results and interval signs retained. External G3 pending.',fontsize=10)
finish(fig,'allocation_joint_scaling')

fig,axes=plt.subplots(1,2,figsize=(11,6),sharey=True)
fig.subplots_adjust(left=.09,right=.975,top=.8,bottom=.29,wspace=.12)
for ax,d in zip(axes,(1,2)):
    style(ax)
    selected=[lookup[f'D{d}_C_p0'],lookup[f'D{d}_C_p4'],lookup[f'D{d}_I_high_minus_low']]
    for i,item in enumerate(selected):interval(ax,i,item,colors[d],'o')
    ax.set_title(f'Draw {d}');ax.set_xticks([0,1,2],['C at price 0','C at price 4m','I(B8) - I(B1)']);ax.set_xlim(-.35,2.35)
axes[0].set_ylabel('Registered contrast (percentage points)')
fig.suptitle('Changes in policy gaps and price interaction',fontsize=17,y=.95)
fig.text(.05,.15,'C = policy gap at B8/T8 minus policy gap at B1/T1. I = price-4m gap minus price-0 gap.',fontsize=10)
fig.text(.05,.10,'Pointwise 95% paired-question intervals; no familywise or procurement-population coverage claim.',fontsize=10)
fig.text(.05,.055,'ALL_CONTRASTS.csv includes every registered per-draw contrast, plus observed draw means and ranges.',fontsize=10)
finish(fig,'registered_interactions')

fig,ax=plt.subplots(figsize=(11,5.6))
fig.subplots_adjust(left=.09,right=.975,top=.8,bottom=.34)
style(ax)
bridge=[lookup[f'D1_p0_{p}_{which}'] for p in ('breadth','depth')
        for which in ('B8_minus_B1_at_T1','T8_minus_T1_at_B8')]
for i,item in enumerate(bridge):interval(ax,i,item,'#246b9e' if i<2 else '#b36527','o')
ax.set_xticks(range(4),['Breadth\nB8-B1 at T1','Breadth\nT8-T1 at B8','Depth\nB8-B1 at T1','Depth\nT8-T1 at B8'])
ax.set_xlim(-.35,3.35);ax.set_ylabel('Conditional accuracy change (pp)')
fig.suptitle('D1 / zero problem price: the retained bridge',fontsize=17,y=.95)
fig.text(.05,.16,'Each point changes one factor while holding the other fixed; 95% paired-question intervals.',fontsize=10)
fig.text(.05,.11,'The B1/T8 corners were removed before student outcomes. The full B x T interaction and J are unavailable.',fontsize=10)
fig.text(.05,.06,'These conditional changes are not a unique attribution of improvement to data versus training.',fontsize=10)
finish(fig,'conditional_bridge')

lines=['# P008 complete primary endpoint tables — external review pending','',
       '18 logical students plus base have complete local raw/dose/state verification and stopped providers. '
       'This publication does not itself claim final CPU completion or independent G3 acceptance.','',
       '## All cells','',
       '| Logical cell | Correct / 1319 | Accuracy | Length caps | Updates | Targets |',
       '|---|---:|---:|---:|---:|---:|']
for row in cells:
    lines.append(f"| {row['logical_run_id']} | {row['correct']} / 1319 | {100*row['accuracy']:.3f}% | {row['length_caps']} | {row['updates']} | {row['targets']} |")
lines+=['','## All contrasts','',
        '| Contrast | Estimate (pp) | Conditional pointwise 95% interval (pp) |',
        '|---|---:|---:|']
for row in data['contrasts']:
    lo,hi=row['conditional_question_percentile_CI95_pp']
    lines.append(f"| {row['name']} | {row['estimate_pp']:+.3f} | [{lo:+.3f}, {hi:+.3f}] |")
lines+=['','## Interpretation and limits','',
        '- Main comparisons condition on a common hypothetical acquisition cap and training contract. They do not establish equal actual platform dollars or a universal optimum.',
        '- Changes between B1/T1 and B8/T8 follow a joint data and training path. The retained bridge supplies only four conditional effects in D1/price0; no complete interaction or unique attribution is available.',
        '- Paired-question intervals are conditional on these fixed models, corpora, parser and seen benchmark. Only two procurement draws and one common initialization seed are available; data also changes the training path.',
        '- No difference detected does not establish equivalence. All registered contrasts and signs are reported, with pointwise intervals and no multiplicity-adjusted significance claim.',
        '- The original timing gate failed. Before any T8 outcome, the owner and independent reviewer approved 9600 seconds per original slot and the 9570-second admission line. This post-hoc engineering deviation remains disclosed.',
        '- The two original zero-update T1 failures, failed D2 parent, continuation and independent replacements remain separate physical sources. All failure/setup/storage costs remain in the cost record.',
        '- Length caps remain incorrect in the 1319 denominator. Correct final answers do not prove valid reasoning. The test set was previously seen by researchers.',
        '- Unified secondary-parser sensitivity remains pending a separately reviewed rule applied to every cell. Primary scores are unchanged.',
        '- ALL_CELLS.csv includes acquired/exposed answers and parents, zero exposure and balanced-exposure metadata. Complete procurement charges, failed/duplicate attempts and unused caps remain in the independently audited pool packets.',
        '- Public checkpoint hashes do not imply external access to binary states. Final CPU integrity and independent contrast/figure review have separate status.','',
        '## Evidence','',
        '- T1: student_t1_eight_v1 and student_t1_replacements_v1; base_v1.',
        '- T8: t8_results_v1, each original run with an immutable compact evidence packet.',
        '- Procurement: pool_d1_v1 and pool_d2_merged_v1; failed parent retained in pool_d2_reconciliation_v1.',
        '- Runtime and amended numeric review: student_t8_cap_9600_v1 and t8_cap_9600_accepted_v1.',
        '- Cost snapshots are delayed metering, never reservations presented as invoices. A current freeze-time cost statement is maintained separately.','']
(out/'FACTS_AND_LIMITS.md').write_text('\n'.join(lines))
dump(out/'FIGURE_BINDING.json',dict(result_file_sha256=sha(out/'RESULTS.json'),
     primary_analysis_unchanged=True,external_review='pending',visual_inspection_required=True,
     source_sha256={n:sha(out/n) for n in ('prepare_registered_p008_analysis.py','publish_registered_p008_analysis.py','p008_paired_question_analysis.py')}))
dump(out/'MANIFEST.json',manifest(out))
print(json.dumps(dict(packet=str(out),external_review='pending',visual_inspection_required=True)))
