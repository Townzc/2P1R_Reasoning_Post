"""Fresh admission for the owner's separate $20 extension probe; no old meter rerun."""
import argparse
from decimal import Decimal
from pathlib import Path
import subprocess
import time
from experiments.p011.forced_answer_ext3b import SPEC,SCOPE,LOCAL,INPUTS,admit,actual,checked_budget
from experiments.p011.owner_0205_common import create,read,sha,utc
from experiments.p011.provider_slots import shared_slots


def main():
    p=argparse.ArgumentParser();p.add_argument('--review',required=True);p.add_argument('--directory',required=True)
    a=p.parse_args();spec=admit(SPEC,a.review,SCOPE);actual(spec)
    if (LOCAL/'cli').exists() or (LOCAL/'ONE_MODEL_ATTEMPT_FENCE.json').exists():raise ValueError('Attempt already consumed')
    out=Path(a.directory);out.resolve().relative_to(LOCAL.resolve());out.mkdir(parents=True,exist_ok=False)
    create(out/'ATTEMPT.json',{'utc':utc(),'total_cap_usd':'20','automatic_retry':False})
    receipts=[];cli='.local/midpoint_20261011/venv/bin/modal'
    try:
        for name,tail in [('rates',['billing','rates']),('apps',['app','list']),('containers',['container','list'])]:
            started=time.time();res=subprocess.run([cli,*tail,'--json'],capture_output=True,text=True,timeout=60)
            (out/(name+'.json')).write_text(res.stdout);(out/(name+'.stderr')).write_text(res.stderr)
            receipts.append({'name':name,'started_epoch':started,'observed_epoch':time.time(),'exit':res.returncode})
            if res.returncode:raise RuntimeError('Fresh admission query failed; preserve receipts')
        create(out/'READ_RECEIPTS.json',receipts)
        rates=read(out/'rates.json')
        rate=Decimal(rates['gpu_hour_cost_h100'])+4*Decimal(rates['cpu_hour_cost'])+32*Decimal(rates['mem_gib_hour_cost'])
        manifest=read(INPUTS/'INPUT_MANIFEST.json');timing=spec['accepted_seven_cell_throughput']
        n=sum(c['count'] for c in manifest['cells'].values())
        prefill=sum(c['prefill_tokens'] for c in manifest['cells'].values())
        # Max of row and prefill scaling, plus the entire observed overhead of
        # two model initializations: conservative relative to all-seven elapsed.
        prediction=timing['worker_seconds']*max(n/timing['rows'],prefill/timing['prefill_tokens'])+120
        value={'observed_epoch':min(x['started_epoch'] for x in receipts),'hourly_rate_usd':str(rate),
            'total_cap_usd':'20','noncompute_allowance_usd':'1.50',
            'active_or_pending_or_unknown_model_slots':shared_slots(read(out/'apps.json'),read(out/'containers.json')),
            'throughput_prediction_seconds':prediction,'selected_rows':n,'prefill_tokens':prefill,
            'throughput_source':timing,'evidence_files':{str(out/n):sha(out/n) for n in ['rates.json','apps.json','containers.json','READ_RECEIPTS.json']},
            'separate_new_owner_authorization':True,'old_tasks_not_recharged_or_restarted':True,'final_invoice_claimed':False}
        value['check']=checked_budget(value,time.time());create(out/'BUDGET.json',value)
        create(out/'COMPLETED.json',{'utc':utc(),'budget_sha256':sha(out/'BUDGET.json')});print(out/'BUDGET.json',flush=True)
    except BaseException as exc:
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'receipts':receipts,'automatic_retry':False});raise

if __name__=='__main__':main()
