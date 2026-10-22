"""Necessary new-stage budget capture, only after actual-input A2 approval."""
import argparse
from decimal import Decimal
from pathlib import Path
import json
import subprocess
import time
from experiments.p011.owner_0205_common import admit, checked_metadata, create, read, sha, utc
from experiments.p011.forced_answer import checked_budget

SPEC='reports/p011_20261020/forced_answer_preflight_v1/SPEC.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--review',required=True);p.add_argument('--runtime-review',required=True);p.add_argument('--directory',required=True)
    a=p.parse_args();spec=admit(SPEC,a.review,'p011-forced-answer-complete-path-CR');a2=read(a.runtime_review)
    if (a2.get('scope')!='p011-forced-answer-actual-input-A2-lite' or a2.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or a2.get('spec_sha256')!=sha(SPEC) or a2.get('input_manifest_sha256')!=sha(Path(spec['input_output'])/'INPUT_MANIFEST.json')
            or sha(a2['local_report_path'])!=a2['report_sha256'] or any(a2.get(k) is not True for k in spec['required_A2_flags'])):
        raise ValueError('Actual A2 and complete input first; no speculative meter refresh')
    prior=checked_metadata(spec['terminal_cost_binding']);apps=set(prior['delayed_new_app_charges_usd'])
    if prior['app_ids_without_reported_charge']:raise ValueError('Unknown old accounting must be reconciled')
    for row in prior['all_ten_original_attempts']:
        if row['status'] not in ('failed','completed') or sha(row['terminal_file'])!=row['terminal_sha256']:
            raise ValueError('Exact old terminal receipt required')
    out=Path(a.directory);out.resolve().relative_to(Path(spec['local_root']).resolve());out.mkdir(parents=True,exist_ok=False)
    create(out/'ATTEMPT.json',{'utc':utc(),'purpose':'New forced-answer paid admission','automatic_retry':False})
    cli='.local/midpoint_20261011/venv/bin/modal';receipts=[]
    try:
        for name,tail in [('rates',['billing','rates']),('report',['billing','report','--for','this month','--tag-names','app_id,app_name']),('apps',['app','list']),('containers',['container','list'])]:
            started=time.time();result=subprocess.run([cli,*tail,'--json'],text=True,capture_output=True,timeout=60)
            (out/(name+'.json')).write_text(result.stdout);(out/(name+'.stderr')).write_text(result.stderr)
            receipts.append({'name':name,'started_epoch':started,'observed_epoch':time.time(),'exit':result.returncode})
            if result.returncode:raise RuntimeError('New admission evidence read failed; partial evidence retained')
        create(out/'READ_RECEIPTS.json',receipts)
        rates=read(out/'rates.json');costs={app:None for app in apps}
        for row in read(out/'report.json'):
            if row.get('object_id') in costs:
                app=row['object_id'];cost=Decimal(row['cost'])
                if not cost.is_finite() or cost<0:raise ValueError('Invalid tagged cost')
                costs[app]=str(Decimal(costs[app] or '0')+cost)
        if any(v is None for v in costs.values()):raise ValueError('Missing current tagged meter is not zero')
        # Delayed reports cannot release already observed actual tagged cost.
        total=sum(max(Decimal(v),Decimal(prior['delayed_new_app_charges_usd'][app])) for app,v in costs.items())
        listed=read(out/'apps.json');containers=read(out/'containers.json')
        unknown_active=sum(max(1,int(row['Tasks'])) for row in listed if str(row['State']).lower()!='stopped')
        slots=max(unknown_active,len(containers))
        hourly=Decimal(rates['gpu_hour_cost_h100'])+4*Decimal(rates['cpu_hour_cost'])+32*Decimal(rates['mem_gib_hour_cost'])
        value={'observed_epoch':min(x['started_epoch'] for x in receipts),'hourly_rate_usd':str(hourly),
            'new_epoch_observed_tagged_cost_usd':str(total),'new_epoch_app_reported_costs_usd':costs,
            'prior_unattributed_cost_allowance_usd':'20.02','new_task_reserve_usd':'12',
            'active_or_pending_or_unknown_model_slots':slots,'all_prior_attempts_terminal':True,
            'evidence_files':{str(out/n):sha(out/n) for n in ['rates.json','report.json','apps.json','containers.json','READ_RECEIPTS.json']},
            'final_invoice_claimed':False,'historical_failed_reservations_are_not_expense':True,
            'source_review_sha256':sha(a.review),'actual_A2_sha256':sha(a.runtime_review)}
        value['check']=checked_budget(value,time.time());create(out/'BUDGET.json',value)
        create(out/'COMPLETED.json',{'utc':utc(),'budget_sha256':sha(out/'BUDGET.json')})
        print(out/'BUDGET.json',flush=True)
    except BaseException as exc:
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'receipts':receipts,'automatic_retry':False});raise


if __name__=='__main__':main()
