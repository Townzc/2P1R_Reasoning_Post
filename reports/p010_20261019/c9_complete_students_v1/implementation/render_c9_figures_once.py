from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments.p010.common import dump,sha,utc
r=Path('.local/p010_20261019/r1');src=r/'c9_actual_analysis_r1';out=r/'c9_figures_r1';out.mkdir()
rows={x['cell']:x for x in json.loads((src/'COMPLETE_MATH_CELLS.json').read_text())}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})
colors={'t15':'#0072B2','t7':'#D55E00','t72':'#009E73'};names={'t15':'T1.5','t7':'T7','t72':'T72'}
fig,axes=plt.subplots(2,2,figsize=(12.5,8.5),layout='constrained')
for row,metric,label in [(0,'greedy_percent','Primary: greedy correct (%)'),(1,'sampled_percent','Secondary: mean pass@1 (%)')]:
 ax=axes[row,0]
 for key in colors:
  vals=[rows[f'{key}_n{n}_k1'][metric] for n in (400,3200)]
  ax.plot([0,1],vals,'o-',color=colors[key],label=names[key],lw=2)
  for xx,yy in zip([0,1],vals):ax.annotate(f'{yy:.2f}',(xx,yy),xytext=(5,6),textcoords='offset points',fontsize=9,color=colors[key])
 ax.set(xticks=[0,1],xticklabels=['400','3,200'],xlabel='Distinct questions P (K = 1)',ylabel=label,ylim=(46,58),xlim=(-.12,1.18));ax.grid(axis='y',alpha=.2)
 ax=axes[row,1]
 for key in colors:
  ks=[1,4,8] if key=='t15' else [1]
  vals=[rows[f'{key}_n400_k{k}'][metric] for k in ks]
  ax.plot(ks,vals,'o-' if len(ks)>1 else 'o',color=colors[key],label=names[key],lw=2)
  if key=='t15':
   for xx,yy in zip(ks,vals):ax.annotate(f'{yy:.2f}',(xx,yy),xytext=(5,6),textcoords='offset points',fontsize=9,color=colors[key])
 ax.set(xticks=[1,4,8],xlabel='Answers per question K (P = 400)',ylim=(46,58),xlim=(.5,8.8));ax.grid(axis='y',alpha=.2)
 ax.text(.98,.03,'T7/T72 K4/K8 cancelled by owner;\nno missing value imputation.',transform=ax.transAxes,ha='right',va='bottom',fontsize=9,color='#444444')
axes[0,0].set_title('Axis 1: question coverage',loc='left');axes[0,1].set_title('Axis 2: answers per question',loc='left')
axes[0,0].legend(loc='lower right',frameon=False)
fig.suptitle('P010 F2 · complete MATH-500 cells',fontsize=17,fontweight='bold')
fig.supxlabel('Seed 17; fixed 1,024 updates / 2,097,148 targets. Secondary averages all four samples; no best-of-four.\nObserved models only; independent A3 pending.',fontsize=9)
fig.savefig(out/'F2_MATH_AXES.png',dpi=180);fig.savefig(out/'F2_MATH_AXES.pdf');plt.close(fig)
primary=json.loads((src/'MATH_GREEDY_PAIRED.json').read_text())['contrasts'];e4=json.loads((src/'GSM_E4_PAIRED.json').read_text())['contrasts']
labels=['P: T1.5 (3,200 - 400)','P: T7 (3,200 - 400)','P: T72 (3,200 - 400)','K: T1.5 (4 - 1)','K: T1.5 (8 - 1)','Teacher: T72 - T1.5, P400','Teacher: T72 - T1.5, P3200','Diagonal: T1.5 (400,8) - (3200,1)','Difficulty: E1d - T72 P3200']
fig,(ax,bx)=plt.subplots(2,1,figsize=(11,8),gridspec_kw={'height_ratios':[8,1.7]},layout='constrained')
for i,(x,label) in enumerate(zip(primary,labels)):
 lo,hi=x['pointwise_95_ci_pp'];point=x['difference_pp'];y=len(primary)-1-i
 ax.errorbar(point,y,xerr=[[point-lo],[hi-point]],fmt='o',color='#0072B2',capsize=3)
 ax.text(15,y,f'{point:+.2f} [{lo:+.2f}, {hi:+.2f}]',va='center',fontsize=9)
ax.set(yticks=list(reversed(range(len(primary)))),yticklabels=labels,xlim=(-12,27),xticks=[-10,-5,0,5,10],title='MATH-500 · primary greedy paired differences')
x=e4[0];point=x['difference_pp'];lo,hi=x['pointwise_95_ci_pp'];bx.errorbar(point,0,xerr=[[point-lo],[hi-point]],fmt='o',color='#D55E00',capsize=3);bx.text(15,0,f'{point:+.2f} [{lo:+.2f}, {hi:+.2f}]',va='center',fontsize=9)
bx.set(yticks=[0],yticklabels=['E4: OLMo GSM8K (3,200 - 400)'],xlim=(-12,27),xticks=[-10,-5,0,5,10],ylim=(-1,1),xlabel='Percentage-point difference',title='GSM8K-1319 · separate task and student family')
for a in (ax,bx):a.axvline(0,color='#888888',lw=1);a.grid(axis='x',alpha=.15)
fig.suptitle('Fixed comparisons · all available primary contrasts',fontsize=16,fontweight='bold')
fig.supxlabel('10,000 paired question resamples; seed 20261019; conditional pointwise 95% intervals.\nNot training-seed population, familywise or equivalence intervals. Independent A3 pending.',fontsize=9)
fig.savefig(out/'PRIMARY_PAIRED_INTERVALS.png',dpi=180);fig.savefig(out/'PRIMARY_PAIRED_INTERVALS.pdf');plt.close(fig)
dump(out/'RENDER_PROVENANCE.json',dict(utc=utc(),inputs={str(p):sha(p) for p in [src/'COMPLETE_MATH_CELLS.json',src/'MATH_GREEDY_PAIRED.json',src/'GSM_E4_PAIRED.json']},source_sha256=sha(__file__),new_bootstrap=0,new_scores=0,matplotlib_version=matplotlib.__version__,figures={p.name:sha(p) for p in out.glob('*') if p.suffix in ('.png','.pdf')}))
