"""New paid-stage evidence only after exact relaunch CR; original cost is retained."""
import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import json
import subprocess
import time
from experiments.p011.forced_answer_relaunch import SPEC, SCOPE, LOCAL, PARENT, admit, checked_budget
from experiments.p011.owner_0205_common import checked_metadata, create, read, sha, utc


def main():
    p=argparse.ArgumentParser();p.add_argument('--review',required=True);p.add_argument('--directory',required=True)
    a=p.parse_args();spec=admit(SPEC,a.review,SCOPE)
    prior=checked_metadata(spec['terminal_cost_binding'])
    apps=set(prior['delayed_new_app_charges_usd'])
    parent_app=spec['relaunch_spec']['parent_app_id']
    if parent_app in apps or prior['app_ids_without_reported_charge']:
        raise ValueError('Exact separate original epoch and failed forced app accounting required')
    for row in prior['all_ten_original_attempts']:
        if row['status'] not in ('failed','completed') or sha(row['terminal_file'])!=row['terminal_sha256']:
            raise ValueError('All original epoch attempts must remain terminal')
    if (PARENT/'ONE_DELEGATED_RELAUNCH_FENCE.json').exists():
        raise ValueError('The one delegated relaunch was already consumed')
    out=Path(a.directory);out.resolve().relative_to(LOCAL.resolve());out.mkdir(parents=True,exist_ok=False)
    create(out/'ATTEMPT.json',{'utc':utc(),'purpose':'Explicit one forced relaunch, cumulative12 total','automatic_retry':False})
    receipts=[];cli='.local/midpoint_20261011/venv/bin/modal'
    try:
        for name,tail in [('rates',['billing','rates']),('report',['billing','report','--for','this month','--tag-names','app_id,app_name']),('apps',['app','list']),('containers',['container','list'])]:
            started=time.time();res=subprocess.run([cli,*tail,'--json'],capture_output=True,text=True,timeout=60)
            (out/(name+'.json')).write_text(res.stdout);(out/(name+'.stderr')).write_text(res.stderr)
            receipts.append({'name':name,'started_epoch':started,'observed_epoch':time.time(),'exit':res.returncode})
            if res.returncode:raise RuntimeError('Fresh admission query failed; retain partial receipts')
        create(out/'READ_RECEIPTS.json',receipts)
        costs={app:None for app in apps|{parent_app}}
        for row in read(out/'report.json'):
            if row.get('object_id') in costs:
                value=Decimal(row['cost'])
                if not value.is_finite() or value<0:raise ValueError('Invalid tagged charge')
                key=row['object_id'];costs[key]=str(Decimal(costs[key] or '0')+value)
        if any(x is None for x in costs.values()):raise ValueError('Missing app charge is not zero')
        old_total=sum(max(Decimal(costs[k]),Decimal(prior['delayed_new_app_charges_usd'][k])) for k in apps)
        rates=read(out/'rates.json')
        rate=Decimal(rates['gpu_hour_cost_h100'])+4*Decimal(rates['cpu_hour_cost'])+32*Decimal(rates['mem_gib_hour_cost'])
        parent_intent=read(PARENT/'dispatch/INTENT.json')
        parent_exit=read('.local/p011_20261020/r1/FORCED_V3_ORIGINAL_GPU_RUN_CLI_EXIT.json')
        elapsed=Decimal(str(datetime.fromisoformat(parent_exit['finished_utc']).timestamp()-datetime.fromisoformat(parent_exit['started_utc']).timestamp()))
        if elapsed<0 or parent_exit['exit_code']!=1:raise ValueError('Exact original failed CLI interval required')
        # Full original wrapper interval includes image build/import; use the
        # larger of rates plus60s conservative grace, never call this an invoice.
        failed_upper=max(Decimal(costs[parent_app]),
                         max(rate,Decimal(parent_intent['budget']['hourly_rate_usd']))*(elapsed+60)/3600)
        listed=read(out/'apps.json');containers=read(out/'containers.json')
        slots=max(sum(max(1,int(x['Tasks'])) for x in listed if str(x['State']).lower()!='stopped'),len(containers))
        value={'observed_epoch':min(x['started_epoch'] for x in receipts),'hourly_rate_usd':str(rate),
            'original_epoch_prior_nonforced_tagged_usd':str(old_total),
            'current_reported_app_costs_usd':costs,'failed_first_app_id':parent_app,
            'failed_first_reported_tagged_usd':costs[parent_app],
            'failed_first_compute_upper_usd':str(failed_upper),'failed_first_wrapper_seconds':str(elapsed),
            'prior_unattributed_cost_allowance_usd':'20.02','total_forced_task_cap_usd':'12',
            'original_noncompute_allowance_usd':'1.50','new_noncompute_allowance_usd':'1.50',
            'active_or_pending_or_unknown_model_slots':slots,'all_original_attempts_terminal':True,
            'evidence_files':{str(out/n):sha(out/n) for n in ['rates.json','report.json','apps.json','containers.json','READ_RECEIPTS.json']},
            'relaunch_review_sha256':sha(a.review),'original_parent_interval_is_upper_not_invoice':True,
            'separate_90_dollar_training_extension_not_charged_to_original150':True,'final_invoice_claimed':False}
        value['check']=checked_budget(value,time.time());create(out/'BUDGET.json',value)
        create(out/'COMPLETED.json',{'utc':utc(),'budget_sha256':sha(out/'BUDGET.json')});print(out/'BUDGET.json',flush=True)
    except BaseException as exc:
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'receipts':receipts,'automatic_retry':False});raise


if __name__=='__main__':main()
