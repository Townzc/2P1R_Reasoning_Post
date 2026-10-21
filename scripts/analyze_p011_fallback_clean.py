"""Once-only new cleanup contrasts; original frozen labels are reused unchanged."""
from pathlib import Path
import argparse,time
from experiments.sft_allocation_midpoint.common import read,dump,sha,manifest,digest
from experiments.p011 import fallback_path as path
ROOT=Path(__file__).resolve().parents[1]
OLD='reports/p010_20261019/c9_complete_students_v1'
def main():
    p=argparse.ArgumentParser();p.add_argument('--review',required=True);args=p.parse_args()
    spec=path.validate(read(ROOT/path.SPEC));path.reviewed(spec,ROOT/path.SPEC,read(args.review));path.published(ROOT,spec)
    out=ROOT/path.LOCAL/'fallback_analysis_r1';out.mkdir(exist_ok=False);dump(out/'ATTEMPT.json',dict(started_epoch=time.time(),old_scoring_and_bootstrap_repeated=False))
    import numpy as np
    from analyses.p010_paired_questions import checked_vector,DRAWS,SEED
    try:
        bindings={};results=[]
        for metric,label in [('greedy','MATH_GREEDY'),('sampled_mean_pass_at_1','MATH_SAMPLED')]:
            oldfile=ROOT/OLD/(label+'_VECTORS.json');meta=read(ROOT/OLD/'MANIFEST.json')[oldfile.name]
            if sha(oldfile)!=meta['sha256']:raise ValueError('Frozen old Boolean vectors changed')
            old=read(oldfile);bindings[str(oldfile.relative_to(ROOT))]=meta
            for n in (400,3200):
                job=spec['jobs'][f'fallback_t72_clean_s17_n{n}_k1_r1'];folder=ROOT/path.LOCAL/'fallback_io_r1/score'/path.logical(job)
                read(folder/'COMPLETED.json');payload=folder/'owned_score/payload';proof=read(payload/'COMPLETED.json');rowsfile=payload/'ALL_SCORED_ROWS.json'
                if proof['technical_unknown']!=0 or sha(rowsfile)!=proof['scored_rows_sha256']:raise ValueError('Exact complete new Boolean labels required')
                binding=read(payload/'INTENT.json')['binding']
                if binding['source_files']!=spec['source_files'] or binding['job_sha256']!=digest(job):raise ValueError('Actual cleaned job/source differs')
                rows=read(rowsfile);table={}
                for row in rows:
                    k=tuple(row['id'].split('::',1));v=row['score']['correct']
                    if k in table or type(v) is not bool:raise ValueError('Repeated/unknown new label')
                    table[k]=v
                ids=old[f't72_n{n}_k1']['question_ids']
                if set(table)!={(e,i) for e in ['greedy','sample0','sample1','sample2','sample3'] for i in ids}:raise ValueError('Original five500 endpoints required')
                values=[table['greedy',i] if metric=='greedy' else sum(table['sample'+str(k),i] for k in range(4))/4 for i in ids]
                newvec=dict(complete=True,technical_unknown=0,question_ids=ids,question_values=values,metric=metric)
                if metric!='greedy':newvec['samples_per_question']=4
                x=checked_vector(newvec,ids,metric);a=checked_vector(old[f't72_n{n}_k1'],ids,metric);b=checked_vector(old[f't15_n{n}_k1'],ids,metric)
                samples=np.random.default_rng(SEED).integers(0,500,size=(DRAWS,500));contrasts=[]
                for name,delta in [('clean_minus_original_T72',x-a),('clean_T72_minus_original_T15',x-b)]:
                    draws=delta[samples].mean(axis=1)*100;lo,hi=np.quantile(draws,[.025,.975],method='linear')
                    contrasts.append(dict(name=name,difference_pp=float(delta.mean()*100),question_paired95_ci_pp=[float(lo),float(hi)]))
                record=dict(nominal_P=n,actual_P_cov=job['config']['P_cov'],metric=metric,clean_accuracy=float(x.mean()),
                    original_T72_accuracy=float(a.mean()),original_T15_accuracy=float(b.mean()),new_contrasts=contrasts,
                    dose_targets=2097148,updates=1024,seed=17,coverage_changed=True,training_seed_population=False,
                    selective_fallback_removal_not_isolated_text_quality_cause=True,mechanism_or_equivalence_proved=False,
                    draws=DRAWS,seed_bootstrap=SEED,numpy_version=np.__version__)
                results.append(record);dump(out/f'{n}_{label}_VECTOR.json',newvec);bindings[str(rowsfile.relative_to(ROOT))]=dict(bytes=rowsfile.stat().st_size,sha256=sha(rowsfile))
        dump(out/'RESULTS.json',results);dump(out/'COMPLETED.json',dict(input_files=bindings,actual_A3_pending=True,old_scores_or_bootstraps_repeated=False));dump(out/'MANIFEST.json',manifest(out))
    except BaseException as exc:dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc)));raise
if __name__=='__main__':main()
