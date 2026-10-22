"""First pair or one explicitly proven infrastructure resume: fresh90USD ledger."""
import argparse
from decimal import Decimal
from pathlib import Path
import subprocess
import time
from experiments.p011.ext4b_runtime_contract import SPEC,LOCAL,JOBS,review,cost_window
from experiments.p011.ext4b_path import ACTUAL
from experiments.p011.owner_0205_common import create,read,sha,utc


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-review',required=True);p.add_argument('--actual-review',required=True);p.add_argument('--directory',required=True);p.add_argument('--resume-json');a=p.parse_args()
    review(SPEC,a.source_review,a.actual_review);actual=read(ACTUAL);a2=read(a.actual_review)
    if a2['actual_job_manifest_sha256']!=sha(ACTUAL):raise ValueError('Real actual job A2 first')
    resume=read(a.resume_json) if a.resume_json else None
    if not resume and any((LOCAL/'dispatch').glob('*/INTENT.json')):raise ValueError('Initial pair admission already consumed')
    requested=[resume['parent_intent']['job']] if resume else list(JOBS)
    out=Path(a.directory);out.resolve().relative_to(LOCAL.resolve());out.mkdir(parents=True,exist_ok=False)
    create(out/'ATTEMPT.json',{'utc':utc(),'new_extension_cap_usd':'90','forced12_and_owner150_separate':True,'purpose':'Necessary first pair or one infrastructure resume admission'})
    cli='.local/midpoint_20261011/venv/bin/modal';receipts=[]
    try:
        for name,args in [('rates',['billing','rates']),('report',['billing','report','--for','this month','--tag-names','app_id,app_name']),('apps',['app','list']),('containers',['container','list'])]:
            started=time.time();ret=subprocess.run([cli,*args,'--json'],capture_output=True,text=True,timeout=60)
            (out/(name+'.json')).write_text(ret.stdout);(out/(name+'.stderr')).write_text(ret.stderr)
            receipts.append({'name':name,'started_epoch':started,'observed_epoch':time.time(),'exit':ret.returncode})
            if ret.returncode:raise RuntimeError('Fresh admission read failed; retained, not rerun automatically')
        create(out/'READ_RECEIPTS.json',receipts);rates=read(out/'rates.json');hourly=Decimal(rates['gpu_hour_cost_h100'])+4*Decimal(rates['cpu_hour_cost'])+96*Decimal(rates['mem_gib_hour_cost'])
        apps=read(out/'apps.json');containers=read(out/'containers.json');slots=max(len(containers),sum(max(1,int(x['Tasks'])) for x in apps if str(x['State']).lower()!='stopped'))
        if slots+len(requested)>8:raise ValueError('Shared active/pending/unknown slots exceed8')
        evidence={str(out/n):sha(out/n) for n in ['rates.json','report.json','apps.json','containers.json','READ_RECEIPTS.json']}
        prior=Decimal('0');costs={};tagged=read(out/'report.json')
        known_cells={j:Decimal('0') for j in JOBS};known_apps=set()
        for intentfile in (LOCAL/'dispatch').glob('*/INTENT.json'):
            old=read(intentfile);app_id=old['app_id']
            if old['job'] not in JOBS or app_id in known_apps:raise ValueError('Duplicate/unknown extension app identity')
            known_apps.add(app_id);charges=[Decimal(str(x['cost'])) for x in tagged if x.get('object_id')==app_id]
            costs[app_id]=str(sum(charges)) if charges else None
            if any(not x.is_finite() or x<0 for x in charges):raise ValueError('Invalid tagged cost')
            known_cells[old['job']]+=sum(charges)
        if any(x>45 for x in known_cells.values()) or sum(known_cells.values())>90:
            raise ValueError('Observed extension charges already exceed a hard cap')
        if resume:
            parent=resume['parent_intent'];app_id=parent['app_id'];matching=[Decimal(str(x['cost'])) for x in tagged if x.get('object_id')==app_id]
            if not matching:raise ValueError('Parent actual tagged cost missing; cannot admit a resume')
            costs[app_id]=str(sum(matching));claim=resume['parent_claim']
            elapsed=Decimal(str(resume['failure']['stopped_observed_epoch']-claim['worker_start_epoch']))
            if elapsed<0:raise ValueError('Negative failure-to-stop interval')
            # All uncertainty remains charged: stopped-observation elapsed + startup/grace.
            prior=max(sum(matching),(elapsed+Decimal(660))*Decimal(parent['budget']['hourly_rate_usd'])/3600)
            evidence[a.resume_json]=sha(a.resume_json)
        for job in requested:
            check=cost_window(hourly,prior,'5')
            # The other cell always retains its entire45USD allowance. No release by completion.
            pair=Decimal(check['cumulative_cell_upper_usd'])+Decimal('45')
            if pair>90:raise ValueError('Two-cell combined hard envelope exceeds90')
            value={'observed_epoch':min(x['started_epoch'] for x in receipts),'requested_job':job,'requested_attempt':2 if resume else 1,
                'pair_cap_usd':'90','per_cell_cap_usd':'45','hourly_rate_usd':str(hourly),'prior_job_compute_upper_usd':str(prior),
                'retained_noncompute_usd':'5','other_cell_retained_upper_usd':'45','pair_total_upper_usd':str(pair),
                'slots_before':slots,'slots_after_requested':slots+len(requested),'evidence_files':evidence,
                'check':check,'all_extension_app_reported_costs':costs,'known_cell_reported_totals':{k:str(v) for k,v in known_cells.items()},'prior_duration_bound_is_not_invoice':True,
                'noncompute_allowance_is_not_zero_or_final_invoice':True,'source_review_sha256':sha(a.source_review),
                'actual_review_sha256':sha(a.actual_review),'actual_job_manifest_sha256':sha(ACTUAL),
                'original_owner150_and_forced12_not_released_or_transferred':True}
            create(out/(job+'_BUDGET.json'),value)
        create(out/'COMPLETED.json',{'utc':utc(),'jobs':requested,'budgets':{j:sha(out/(j+'_BUDGET.json')) for j in requested},'final_invoice_claimed':False})
        print(out,flush=True)
    except BaseException as exc:create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False,'read_receipts':receipts});raise


if __name__=='__main__':main()
