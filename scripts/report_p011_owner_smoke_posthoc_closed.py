"""Read saved complete A7/baseline outputs once and apply original §2 post hoc."""
from pathlib import Path
import time
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from experiments.p011 import long_owner_path as path
ROOT=Path(__file__).resolve().parents[1]
def main():
    spec=path.validate(read(ROOT/path.SPEC));path.published(ROOT,spec)
    names=['long_A7_S-F15_s17_owner_r1','long_baseline_S-L15_s17_owner_r1'];saved={};bindings={}
    for name in names:
        folder=ROOT/path.LOCAL/'long_owner_closeout_r1';audit=folder/'audit'/name;score=folder/'score'/name;job=spec['jobs'][name]
        p=read(audit/'COMPLETE_PROOF.json');s=read(score/'COMPLETED.json')
        if p.get('passed') is not True or p['job_sha256']!=digest(job) or p['source_files']!=spec['source_files'] or s['read_only_saved_score_proof']['passed'] is not True:
            raise ValueError('Actual complete original oracle and frozen score required')
        rows=read(audit/'SCORING_ROWS.json');sample=[r for r in rows if r['id'].startswith('math500:') and ':sample:' in r['id']]
        if len(sample)!=2000 or len({r['id'] for r in sample})!=2000:raise ValueError('Exactly2000 original sampled MATH answers')
        saved[name]=dict(sample_native_eos=sum(r['stop_reason']=='native_eos' for r in sample),sample_count=2000,
            sampled_correct=s['read_only_saved_score_proof']['endpoints']['math500_sample']['correct'],
            sampled_total=s['read_only_saved_score_proof']['endpoints']['math500_sample']['total'],technical_unknown=p['endpoint']['technical_unknown'])
        bindings[name]={'oracle_sha256':sha(audit/'COMPLETE_PROOF.json'),'score_sha256':sha(score/'COMPLETED.json'),'rows_sha256':sha(audit/'SCORING_ROWS.json')}
    a,b=[saved[n] for n in names]
    if a['sampled_total']!=2000 or b['sampled_total']!=2000:raise ValueError('Frozen same-size baseline denominator differs')
    checks=dict(native_eos_at_least_70_percent=a['sample_native_eos']*10>=a['sample_count']*7,
        mean_pass1_not_more_than10pp_below_baseline=a['sampled_correct']>=b['sampled_correct']-200,
        no_technical_failure=a['technical_unknown']==b['technical_unknown']==0)
    out=ROOT/path.LOCAL/'owner150_smoke_posthoc_r1';out.mkdir(exist_ok=False)
    dump(out/'RESULT.json',dict(checks=checks,passed=all(checks.values()),observations=saved,bindings=bindings,
        owner_amendment_sha256=spec['owner_amendment_sha256'],posthoc_not_dispatch_gate=True,
        F15_selected_by_direct_owner_before_results=True,three_arm_comparison_not_performed=True,
        other_jobs_were_dispatched_before_smoke_check=True,no_model_score_or_bootstrap_repeated=True,
        producer_sha256=sha(Path(__file__)),recorded_epoch=time.time(),actual_independent_A3_pending=True))
if __name__=='__main__':main()
