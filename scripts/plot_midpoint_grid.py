"""Deterministic research figure from the verified table; does not create slides."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(source,out):
    data=json.loads(Path(source).read_text());out=Path(out);out.mkdir(parents=True,exist_ok=False)
    rows=data['table'];colors={'repeat':'#6c7580','solutions':'#007f87','mixed':'#a76a12','breadth':'#3f62a2'}
    plt.rcParams.update({'font.size':11,'font.family':'DejaVu Sans','svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.7),gridspec_kw={'width_ratios':[1.4,1]})
    a,b=axes
    for x,r in enumerate(rows):
        for seed,offset,marker in [('17',-.08,'o'),('23',.08,'s')]:
            y=r['seeds'][seed]['accuracy']*100
            a.plot(x+offset,y,marker=marker,color=colors[r['arm']],ms=7,linestyle='none')
        a.text(x,r['mean_accuracy']*100+1.1,f"{r['mean_accuracy']*100:.2f}%",ha='center',weight='bold',fontsize=10)
    a.set_xticks(range(4),[r['arm'].capitalize() for r in rows]);a.set_ylim(65,90)
    a.set_ylabel('GSM8K development accuracy (%)')
    a.set_title('Fixed student supervision')
    a.plot([],[],marker='o',ls='',color='#414141',label='Seed 17');a.plot([],[],marker='s',ls='',color='#414141',label='Seed 23')
    a.legend(loc='lower right',frameon=False,ncol=2,fontsize=9)
    for y,r in enumerate(data['primary_contrasts']):
        lo,hi=r['conditional_question_interval_pp'];m=r['mean_difference_pp']
        b.errorbar(m,y,xerr=[[m-lo],[hi-m]],fmt='o',capsize=5,color=['#007f87','#3f62a2'][y])
        b.text(m,y+.2,f'{m:+.2f} pp',ha='center',fontsize=10)
    b.axvline(0,color='#777777',ls='--',lw=1)
    b.set_yticks([0,1],['Solutions − Repeat','Breadth − Solutions']);b.set_ylim(1.6,-.55)
    b.set_xlabel('Accuracy difference (percentage points)');b.set_xlim(-6,17)
    b.set_title('Prespecified primary contrasts')
    for ax in axes:
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.18)
    fig.suptitle('P007: four allocation policies, two training seeds',x=.04,ha='left',fontsize=14,weight='bold')
    fig.text(.04,.07,'Each run: 256 updates · 524,288 supervised targets · 431 evaluation questions',fontsize=10)
    fig.text(.04,.025,'95% paired-question bootstrap intervals condition on these models and one procurement draw. Historical acquisition cost unknown.',fontsize=8.3,color='#505050')
    fig.subplots_adjust(left=.07,right=.97,bottom=.22,top=.79,wspace=.63)
    fig.savefig(out/'four_arm_results.png',dpi=180);fig.savefig(out/'four_arm_results.svg')
    (out/'PROVENANCE.json').write_text(json.dumps(dict(source=str(source),source_sha256=__import__('hashlib').sha256(Path(source).read_bytes()).hexdigest(),script='scripts/plot_midpoint_grid.py',generated_by='matplotlib deterministic plotting',model_generated_image=False),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();plot(a.source,a.out)
