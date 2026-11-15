"""Admit the existing reviewed B/C requests after A and fresh balance/storage reads."""
import copy, datetime, hashlib, json, os, re, subprocess, sys
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0,'.');sys.path.insert(0,'.local/p012_20261111/amendment7_v1')
from a7_ops import publish, lock
from experiments.p012.training_inputs import validate_training_request
L=Path('.local/p012_20261111');P=Path('reports/p012_20261111')
OUT=P/'amendment8_BC_admission_v1'
MODAL='.local/midpoint_20261011/venv/bin/modal'
ENV=dict(os.environ,MODAL_PROFILE='tangzhice')
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,x:Path(p).write_text(json.dumps(x,indent=2)+'\n')


def net_usage(summary):
    # Credits are payment, not a usage discount. Exclude them from net usage.
    return float(Decimal(summary['metered_cost'])+sum((Decimal(v) for k,v in summary['adjustments'].items() if k!='credits'),Decimal(0)))


def main():
    observed=read(Path(sys.argv[1]))
    assert observed['workspace']=='tangzhice' and observed['source']=='authenticated_UI_credit_indicator'
    assert datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(observed['utc']) < datetime.timedelta(minutes=10)
    assert read(L/'amendment8_v1/A_QUEUE.json')['status']=='A_complete_B_C_storage_gate_pending_T_not_started'
    assert sha(Path('experiments/p012/training_config.py'))=='61163c22d2e3d37c0bf2592cf7d95ea5569cf2acf6c5cb24606a14ab87bb7696'
    summary=json.loads(subprocess.check_output([MODAL,'billing','summary','--json'],env=ENV,text=True))
    apps=json.loads(subprocess.check_output([MODAL,'app','list','--json'],env=ENV,text=True))
    assert not [x for x in apps if x['state']!='stopped'], 'A or unknown Modal call still active'
    bills=json.loads(subprocess.check_output([MODAL,'billing','report','--start','2026-11-15','--end','2026-11-16','--show-resources','--json'],env=ENV,text=True))
    costs=[]
    for d in sorted((L/'amendment8_modal_runs_v1').glob('a8_a*')):
        if not (d/'run.log').exists():continue
        ids=set(re.findall(r'ap-[A-Za-z0-9]+',(d/'run.log').read_text(errors='replace')));assert len(ids)==1
        app=ids.pop();rows=[r for r in bills if r['object_id']==app];assert rows, 'No billed rows for '+app
        assert read(d/'result/STATUS.json')['success']
        costs.append({'run_id':d.name,'app_id':app,'billed_usd':sum(float(r['cost']) for r in rows),'billing_rows':rows})
    assert len(costs)==20
    before=read(P/'modal_cleanup_fb5c77bb_v1/tangzhice_MONTHLY_SUMMARY.json')
    initial=read(P/'amendment8_A_admission_v1/ADMISSION.json')['actual_balance_usd']
    new_usage=net_usage(summary)-net_usage(before)
    reflected=initial-observed['balance_usd']
    unsettled=max(0,new_usage-reflected)
    storage=read(P/'modal_cleanup_fb5c77bb_v1/DAILY_STORAGE_RECEIPT_AFTER.json')
    assert storage['observed_after_deletion']
    days=(datetime.date(2026,11,24)-datetime.datetime.now(ZoneInfo("America/Los_Angeles")).date()).days
    assert days>0
    daily=max(storage['workspaces']['tangzhice']['daily_net_usd'].values())
    reserve=daily*days+1
    manifest=read(P/'amendment8_modal_review_v1/CANDIDATE_MANIFEST.json')
    selected=[x for x in manifest['cells'] if x['group'] in ('B','C')]
    rhs=observed['balance_usd']-4
    pruned=[]
    while unsettled+reserve+sum(x['total_forecast_usd'] for x in selected)>rhs:
        c=[x for x in selected if x['group']=='C']
        if not c:raise RuntimeError('Llama B cannot fit original workspace; stop without switching workspace')
        last=max(c,key=lambda x:x['index']);selected.remove(last);pruned.append(last)
    assert len([x for x in selected if x['group']=='B'])==7
    selected.sort(key=lambda x:(x['group'],x['index']))
    with lock('BUDGET_ADMISSION.lock'):
        assert not OUT.exists();OUT.mkdir();(OUT/'requests').mkdir()
        record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'authority_commit':'5e1f9128180f1dcd222fc1e33fe691ec01030f38','accepted_review_commit':'ff567d06ba39fd1052a72c558e69dbe98f09dd24',
            'actual_balance':observed,'protected_usd':4,'monthly_net_usage_increase_since_A_admission_usd':new_usage,
            'usage_reflected_in_balance_usd':reflected,'unsettled_usd':unsettled,
            'unsettled_basis':'max(0, API net usage increase excluding credit payments - UI balance decrease); no active apps',
            'storage_daily_net_usd':daily,'days_to_Nov24':days,'storage_plus_lag_reserve_usd':reserve,
            'storage_receipt':{'path':str(P/'modal_cleanup_fb5c77bb_v1/DAILY_STORAGE_RECEIPT_AFTER.json'),'sha256':sha(P/'modal_cleanup_fb5c77bb_v1/DAILY_STORAGE_RECEIPT_AFTER.json')},
            'next_batch_forecast_usd':sum(x['total_forecast_usd'] for x in selected),
            'hard_lhs_usd':unsettled+reserve+sum(x['total_forecast_usd'] for x in selected),'hard_rhs_usd':rhs,
            'admitted':True,'retained_runs':[x['run_id'] for x in selected],
            'pruned_C_tail':[{'run_id':x['run_id'],'forecast_usd':x['total_forecast_usd']} for x in pruned],
            'total_A_compute_billed_usd':sum(x['billed_usd'] for x in costs),'A_apps':costs,
            'monthly_summary':summary,'active_apps':[],'T_admitted':False,'automatic_retries':False}
        write(OUT/'ADMISSION.json',record)
        for row in selected:
            d=L/'amendment8_modal_runs_v1'/row['run_id'];r=read(d/'request_pending.json')
            assert not (d/'request.json').exists() and not (d/'run.log').exists()
            r['forecast']={'admitted':True,'forecast_usd':row['training_forecast_usd'],
                'reserved_evaluation_usd':row['evaluation_forecast_usd'],'admission_file':str(OUT/'ADMISSION.json'),
                'admission_sha256':sha(OUT/'ADMISSION.json'),'workspace':'tangzhice'}
            validate_training_request(r);write(d/'request.json',r)
            public=copy.deepcopy(r);public['dataset'].pop('jsonl');write(OUT/'requests'/(d.name+'.json'),public)
        write(OUT/'LAUNCH_POLICY.json',{'utc':record['utc'],'ordered_runs':record['retained_runs'],
            'detached':True,'all_failures_stop':True,'R2':'global_step==expected_updates and Num examples==P*K',
            'workspace':'tangzhice','GPU':'H100!','T_started':False})
        (OUT/'README.md').write_text('# A8 B/C admission after A and cleanup\n\n'+
            f"Current balance ${observed['balance_usd']:.2f}, protected $4; unsettled ${unsettled:.6f}; storage reserve ${reserve:.6f}. "
            f"Selected batch forecast ${record['next_batch_forecast_usd']:.6f}; hard gate ${record['hard_lhs_usd']:.6f} <= ${rhs:.6f}. "
            f"A actual compute totals ${record['total_A_compute_billed_usd']:.6f}.\n\n"+
            f"Retained {len(selected)} cells, B01–B07 followed by retained C prefix. Pruned C tail: {[x['run_id'] for x in pruned]}. "
            'Pruning uses the financial gate before any C output. All model/config/data/scoring paths match the accepted22-cell package; R-2 checks remain mandatory, including B07. No workspace, transport, account, or scientific-protocol changes. T remains separately gated.\n')
        commit=publish([OUT],'P012 A8: admit B and funded C prefix after actual A cost and storage reconciliation')
        print(json.dumps({'commit':commit,'admitted_cells':len(selected),'pruned':record['pruned_C_tail'],'hard_lhs':record['hard_lhs_usd'],'hard_rhs':rhs}),flush=True)


if __name__=='__main__':main()
