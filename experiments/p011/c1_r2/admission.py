"""C1 full-path admission helpers; no provider/model calls or self-admission.

Future outer entry must supply actual fixed reviews, fresh D1 budget evidence,
complete shared P011 attempt ledger and provider state. This module does not
select a timing proxy, set actual limits, release reserves or create approvals.
"""
from collections import Counter
from decimal import Decimal
from pathlib import Path
import math
import re

from experiments.p011.c1_r2 import execution as c1_execution
from experiments.sft_allocation_midpoint.common import read, sha, digest

CAPS={k:Decimal(v) for k,v in {'A':'115','B':'20','C':'12','D':'25','emergency':'8'}.items()}
PLAN='e0dee182972f9910b707fac68800dcb5a3aff2d3'
SCOPE='p011-C1-r2-chunk320-complete-path-CR-A1-A2-lite'


def exact_source(spec,root):
    """Bind every actual file; full closure completeness is independently reviewed."""
    root=Path(root)
    if not spec['source_files']:raise ValueError('Nonempty exact source closure required')
    for name,value in spec['source_files'].items():
        p=Path(name)
        if (p.is_absolute() or '..' in p.parts or (root/p).is_symlink()
                or not re.fullmatch(r'[0-9a-f]{64}',value) or sha(root/p)!=value):
            raise ValueError('Actual full-path source changed or unsafe')


def fixed_report(obj):
    if (obj.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or not re.fullmatch(r'[0-9a-f]{40}',obj.get('target_commit',''))
            or not re.fullmatch(r'[0-9a-f]{64}',obj.get('report_sha256',''))
            or sha(obj['local_report_path'])!=obj['report_sha256']):
        raise ValueError('Real complete fixed independent report required')
    return {k:v for k,v in obj.items() if k!='local_report_path'}


def reviewed_path(spec,spec_file,review):
    c1_execution.validate_spec(spec);public=fixed_report(review)
    expected={'scope':SCOPE,'original_plan_commit':PLAN,'spec_sha256':sha(spec_file),
        'source_files':spec['source_files'],'input_files':spec['input_files'],
        'original_group_binding_sha256':spec['original_group_binding_sha256'],
        'task_inventory_sha256':digest(spec['task_inventory']),
        'timing_sha256':digest(spec['timing']),
        'measurement_exceptions':spec['limits']['measurement_exceptions']}
    if c1_execution.self_calibrating(spec):
        expected['owner_decision_sha256']=c1_execution.SELF_CALIBRATION_OWNER_SHA
        expected['bounded_in_run_self_calibration_accepted']=True
        expected['r2_owner_decision_sha256']=c1_execution.R2_OWNER_SHA
        expected['budget_owner_decision_sha256']=c1_execution.BUDGET_OWNER_SHA
        expected['r1_failed_call_and_reservation_retained']=True
        expected['original_input_upload_reuse_accepted']=True
    flags=('complete_input_A1_accepted','complete_source_closure_accepted',
        'exact_timing_scope_accepted','original_tokens_masks_and_EOS_unchanged',
        'untouched_base_forward_only','full_result_window_and_budget_accepted')
    if (any(review.get(k)!=v for k,v in expected.items())
            or any(review.get(k) is not True for k in flags)):
        raise ValueError('Exact shared C1 CR/input A1/numeric A2-lite not complete')
    return public


def accounting(records,containers,states):
    """Failed/pending/unknown reservations retained, unmatched containers counted.

    records are the full dedicated shared P011 dispatch ledger supplied by the
    outer entry, including local pre-spawn intents. No legacy run is repolled.
    Previously closed P011 apps may use their original saved STOPPED/owned0 proof.
    """
    totals={k:Decimal('0') for k in CAPS};logical=set();apps=[];pending=0
    for record in records:
        b=record['budget'];cat=b['category'];value=Decimal(str(b['new_reserved_usd']))
        if (cat not in CAPS or not value.is_finite() or value<=0
                or record['logical_id'] in logical):
            raise ValueError('Ambiguous logical attempt or invalid reservation')
        logical.add(record['logical_id']);totals[cat]+=value
        app=record.get('app_id')
        if app is None:pending+=1
        elif not isinstance(app,str) or not app.startswith('ap-'):
            raise ValueError('Original actual app identity required')
        else:apps.append(app)
    if len(apps)!=len(set(apps)):raise ValueError('Duplicate app identity')
    if any(totals[k]>CAPS[k] for k in CAPS) or sum(totals.values())>180:
        raise ValueError('Original P011 category/total cap exceeded; no transfers')
    counts=Counter(x.get('app_id') for x in containers);slots=pending
    for app in apps:
        n=counts.pop(app,0)
        slots+=n if str(states.get(app,'unknown')).lower()=='stopped' else max(1,n)
    slots+=sum(counts.values())
    return {k:str(v) for k,v in totals.items()},slots


def fresh_budget(spec,budget,records,containers,states,now,root):
    """No credit/netting shortcut; proof of available floor must precede dispatch."""
    if (type(now) not in (int,float) or not math.isfinite(now)
            or type(budget['observed_epoch']) not in (int,float)
            or not math.isfinite(budget['observed_epoch'])
            or not 0<=now-budget['observed_epoch']<=3600):
        raise ValueError('Actual fresh budget observation required')
    totals,slots=accounting(records,containers,states)
    reserve=Decimal(str(spec['limits']['reserved_usd']))
    if (budget['all_attempted_reservations_usd']!=totals or slots>=4
            or any(x['logical_id']=='C1_original_token_base_forward_r2' for x in records)
            or budget.get('cap_usd')!='12' or budget.get('category')!='C'
            or budget.get('overall_cap_usd')!='180' or budget.get('protected_usd')!='0'
            or budget.get('budget_owner_decision_sha256')!=c1_execution.BUDGET_OWNER_SHA
            or budget.get('reserve_release_used') is not False
            or budget.get('owner_estimate_used_as_balance') is not False
            or budget.get('availability_basis')!='owner_current_balance_minus_retained_P011_reserves_and_meter_growth'
            or not budget['source_evidence_files']):
        raise ValueError('Shared ledger/category/unused-slot/protected budget differs')
    # Fresh private billing/accounting evidence, not just an unchecked flag.
    for name,value in budget['source_evidence_files'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or sha(Path(root)/p)!=value:
            raise ValueError('Fresh exact budget source bytes differ')
    available=Decimal(str(budget['available_after_retained_prior_reserves_usd']))
    gross=Decimal(str(budget['observed_gross_resource_usd']))
    if (not available.is_finite() or not gross.is_finite() or gross<0
            or available-reserve<0 or sum(Decimal(v) for v in totals.values())+reserve>180):
        raise ValueError('Protected balance/total budget unavailable')
    if now+spec['limits']['full_result_window_seconds']>c1_execution.CUTOFF_EPOCH:
        raise ValueError('Whole end-to-end result window misses original cutoff')
    if c1_execution.self_calibrating(spec):
        if Decimal(str(budget.get('usd_per_second','NaN')))!=Decimal(str(spec['limits']['usd_per_second'])):
            raise ValueError('Fresh exact full-resource rate must bind owner bounded reserve')
        initial=c1_execution.initial_admission(spec,0,totals['C'])
    else:
        initial=c1_execution.forecast(spec,0,spec['task_inventory']['journal_chunks'],[],totals['C'])
    return {'category':'C','new_reserved_usd':str(reserve),'prior_reserved_usd':totals['C'],
        'all_attempted_reservations_usd':totals,'provider_slots':slots,
        'initial_forecast':initial,'protected_usd':'0','not_actual_expense':True}
