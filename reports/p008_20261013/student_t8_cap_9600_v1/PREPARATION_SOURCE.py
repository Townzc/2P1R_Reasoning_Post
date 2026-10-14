from pathlib import Path
import ast,datetime,json
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
r=Path('.local/p008_20261013/main_r1'); p=r/'t8_cap_9600_r1'
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
owner=dict(authority='Direct human reply in this chat',answer='批准 9,600 秒及 $266.44 上限（推荐）',recorded_utc=now,
 old_cap_seconds=9560,new_cap_seconds=9600,additional_reservation_cents=40,old_stage_cap_cents=26604,
 stage_cap_cents=26644,project_ceiling_cents=45000,protected_cents=5000,
 original_eight_T8_only=True,maximum_calls_each=1,automatic_retry=False,maximum_student_H100_workers=8,
 scientific_dose_inputs_and_endpoint_unchanged=True,margin_multiplier=1.2,soft_margin_seconds=30,
 material_freeze_utc='2026-10-14T04:00:00Z',exact_runtime_and_numeric_review_required=True,
 original_N2_failed_retained=True,post_hoc_engineering_deviation=True)
dump(p/'OWNER_T8_CAP_9600.json',owner)
# Separate immutable specification. Original plans, configs and all previous sources remain byte-identical.
old=read('reports/p008_20261013/student_admission_v1/ADMISSION.json')
proposal=read(r/'T8_TIMING_PROPOSAL_REPLACEMENTS.json')
assert digest(old)=='ab49b0a638090f61dfd39e7391c61e4427a47b6ea94acfe6e0de3c4f606b21ee'
assert digest(proposal)=='0fb18e7408e8c6cfef69fc05c3f53dab1ce380591926df91dae4000e0bdde75e'
runs=sorted(n for n,c in old['configs'].items() if c.get('training_multiple')==8)
releases={str(draw):read(r/'student_completion_r1/exports'/n/'evidence/intent.json')['release'] for draw,n in [(1,'d1_b1_p4_breadth_t1'),(2,'d2_b1_p0_breadth_t1')]}
spec=dict(schema='p008_t8_9600_cap_amendment_v1',owner=owner,original_spec=old,original_g1_releases=releases,
 original_spec_sha256=digest(old),plan_sha256=old['plan_sha256'],configs=old['configs'],config_sha256=old['config_sha256'],
 common_plan_gate_sha256=old['common_plan_gate_sha256'],runs=runs,original_failed_timing_proposal=proposal,
 original_proposal_digest=digest(proposal),original_proposal_file_sha256=sha(r/'T8_TIMING_PROPOSAL_REPLACEMENTS.json'),
 original_timing_review_commit='b5c0a754c40e6b5e2037d3e134fb355105ccbe74',
 original_timing_review_sha256=sha(r/'review_b5c0a754/N2_AND_CAP.md'),
 worker_cap_seconds=9600,platform_timeout_seconds=9660,startup_timeout_seconds=600,
 dispatch_window_seconds=10300,soft_margin_seconds=30,margin_multiplier=1.2,
 amended_threshold_seconds=9570,original_criterion_passed=False,
 new_slot_reservation_cents=1258,old_slot_reservation_cents=1253,additional_cents_per_slot=5,
 additional_total_cents=40,stage_cap_cents=26644,project_ceiling_cents=45000,protected_cents=5000,
 project_budget=read('reports/p008_20261013/BILLING_UPDATE_1636.json'),
 registered_plan_unchanged=True,original_claim_key_used=True,new_scientific_calls=0,
 operational_cap_overrides_only_cfg_max_seconds=True,post_hoc_engineering_deviation=True)
dump(p/'AMENDMENT.json',spec)
base=Path('experiments/sft_allocation_p008/student_t8_binding.py').read_text()
a=base.index('def validate_timing_gate');b=base.index('\n\ndef validate_student_binding',a)
method=base[a:b].replace('def validate_timing_gate(cfg, release, spec):','def validate_timing_gate(cfg, release, spec):\n    original = spec["original_spec"]')
method=method.replace("'t8-numeric'","'t8-cap-9600-numeric'").replace("spec['configs']","original['configs']").replace('expected_mapping(spec)','expected_mapping(original)')
method=method.replace("{n: 9560 for n in large}","{n: 9600 for n in large}")
method=method.replace("proposal.get('engineering_criterion_passed') is not True","proposal.get('engineering_criterion_passed') is not False")
method=method.replace("proposal.get('spec_sha256') != digest(spec)","proposal.get('spec_sha256') != digest(original)")
method=method.replace('seconds > 9530','seconds > 9570').replace("p.get('engineering_criterion_passed') is not True","p.get('engineering_criterion_passed') is not False")
method=method.replace("'A reviewed T8 prediction does not fit the original cap'","'Frozen failed prediction does not fit the approved amended cap'")
header='''"""Explicit post-hoc +40s/+5c amendment; original failed criterion stays failed.

Original scientific config and unique RunGuard claim are reused, not migrated.
The immutable supplemental reservation is accounting metadata, no GPU function.
Both new source/spec review and separate amended numerical acceptance are needed.
"""
import math
from decimal import Decimal, ROUND_CEILING
from experiments.sft_allocation_midpoint.common import digest
from .completion_student_binding import validate_student_binding as validate_original
from .student_t8_binding import ORIGINAL, REPLACEMENTS, FAILED, expected_mapping, require_timing_terminals, pending_across_queues
from .main_binding import accepted

ORIGINAL_SPEC = 'ab49b0a638090f61dfd39e7391c61e4427a47b6ea94acfe6e0de3c4f606b21ee'
ORIGINAL_PROPOSAL = '0fb18e7408e8c6cfef69fc05c3f53dab1ce380591926df91dae4000e0bdde75e'
AMENDMENT_KEY = 'midpoint/' + ORIGINAL + '/t8_cap_9600_amendment'


def validate_owner(owner):
    fields = dict(authority='Direct human reply in this chat', answer='批准 9,600 秒及 $266.44 上限（推荐）',
        old_cap_seconds=9560,new_cap_seconds=9600,additional_reservation_cents=40,
        old_stage_cap_cents=26604,stage_cap_cents=26644,project_ceiling_cents=45000,protected_cents=5000,
        original_eight_T8_only=True,maximum_calls_each=1,automatic_retry=False,maximum_student_H100_workers=8,
        scientific_dose_inputs_and_endpoint_unchanged=True,margin_multiplier=1.2,soft_margin_seconds=30,
        material_freeze_utc='2026-10-14T04:00:00Z',exact_runtime_and_numeric_review_required=True,
        original_N2_failed_retained=True,post_hoc_engineering_deviation=True)
    if any(type(owner.get(k)) is not type(v) or owner[k] != v for k,v in fields.items()):
        raise ValueError('Exact direct bounded cap/budget authority required')


def amendment_record(spec):
    return dict(schema='p008_immutable_t8_cap_supplement_v1',spec_sha256=digest(spec),
        owner_sha256=digest(spec['owner']),original_plan_sha256=spec['plan_sha256'],
        original_failed_proposal_digest=ORIGINAL_PROPOSAL,runs=spec['runs'],
        old_reserved_cents_per_slot=1253,additional_cents_per_slot=5,total_additional_cents=40,
        effective_reserved_cents_per_slot=1258,original_run_claims_required=True,
        effective_worker_seconds=9600,original_N2_passed=False,post_hoc_engineering_deviation=True)


def register_amendment(store,spec):
    value=amendment_record(spec)
    if not store.put(AMENDMENT_KEY,value,skip_if_exists=True) and store.get(AMENDMENT_KEY)!=value:
        raise ValueError('Conflicting immutable cap supplement')
    return value


def supplement_key(run):
    return AMENDMENT_KEY+'/reserved/'+run


def reserve_supplement(store,spec,admitted):
    # Must follow the ORIGINAL scientific claim. A competing old/new worker
    # cannot reach this point after losing that claim. Any partial failure burns
    # the slot; it never authorizes another call or claim deletion.
    if admitted.campaign_id!=ORIGINAL or admitted.run_id not in spec['runs']:
        raise ValueError('Foreign scientific slot')
    value=amendment_record(spec)
    if store.get(AMENDMENT_KEY)!=value:
        raise ValueError('Missing immutable global supplement')
    claim=store.get('midpoint/'+ORIGINAL+'/claim/'+admitted.run_id)
    if claim is None or digest(claim)!=admitted.claim_sha256 or claim['attempt_id']!=admitted.attempt_id:
        raise ValueError('Original scientific claim not owned')
    record=dict(run_id=admitted.run_id,original_claim_sha256=admitted.claim_sha256,
                amendment_sha256=digest(value),supplement_reserved_cents=5,
                reservation_not_provider_expense=True)
    if not store.put(supplement_key(admitted.run_id),record,skip_if_exists=True):
        raise ValueError('Supplement already reserved; no replay')
    return record


def verify_supplement(store,spec,run):
    value=amendment_record(spec);claim=store.get('midpoint/'+ORIGINAL+'/claim/'+run)
    record=store.get(supplement_key(run))
    if store.get(AMENDMENT_KEY)!=value or claim is None or record!=dict(run_id=run,
       original_claim_sha256=digest(claim),amendment_sha256=digest(value),
       supplement_reserved_cents=5,reservation_not_provider_expense=True):
        raise ValueError('Original scientific claim and supplementary reservation differ')
    return record


def validate_student_binding(plan,cfg,release,spec):
    validate_owner(spec['owner'])
    original=spec['original_spec'];run=cfg['run_id']
    large=sorted(n for n,c in original['configs'].items() if c.get('training_multiple')==8)
    if (digest(original)!=ORIGINAL_SPEC or spec['original_spec_sha256']!=ORIGINAL_SPEC
        or spec['runs']!=large or len(large)!=8 or run not in large
        or cfg!=original['configs'][run] or spec['configs']!=original['configs']
        or spec['config_sha256']!=original['config_sha256']
        or digest(plan)!=original['plan_sha256'] or spec['plan_sha256']!=digest(plan)
        or spec['common_plan_gate_sha256']!=original['common_plan_gate_sha256']
        or release['spec_sha256']!=digest(spec)):
        raise ValueError('Original scientific plan/config/roster cannot change')
    # These are actual historical source/G1 releases, not fabricated new PASS.
    validate_original(plan,cfg,spec['original_g1_releases'][str(cfg['draw'])],original)
    fixed=dict(worker_cap_seconds=9600,platform_timeout_seconds=9660,startup_timeout_seconds=600,
        dispatch_window_seconds=10300,soft_margin_seconds=30,margin_multiplier=1.2,
        amended_threshold_seconds=9570,original_criterion_passed=False,
        new_slot_reservation_cents=1258,old_slot_reservation_cents=1253,additional_cents_per_slot=5,
        additional_total_cents=40,stage_cap_cents=26644,project_ceiling_cents=45000,protected_cents=5000,
        registered_plan_unchanged=True,original_claim_key_used=True,
        operational_cap_overrides_only_cfg_max_seconds=True,post_hoc_engineering_deviation=True)
    if any(type(spec.get(k)) is not type(v) or spec[k]!=v for k,v in fixed.items()):
        raise ValueError('Only exact finite operational amendment allowed')
    if any(plan['slots'][n]['reserved_cents']!=1253 for n in large):
        raise ValueError('Old registered reservation changed')
    minimum=math.ceil((9600+700)*4.393584/3600*100)
    if minimum!=1258 or 8*(minimum-1253)!=40 or 26604+40!=spec['stage_cap_cents']:
        raise ValueError('Full startup/closing reservation differs')
    budget=spec['project_budget'];meter=Decimal(budget['workspace_metered_usd'])
    if (not meter.is_finite() or meter<0 or int((meter*100).to_integral_value(rounding=ROUND_CEILING))+26644>45000
        or budget['project_ceiling_usd']!='450' or budget['protected_usd']!='50'
        or budget['all_failures_setup_build_storage_retained'] is not True):
        raise ValueError('Conservative full-meter plus entire-stage budget proof fails')
    gates=release['gates']
    if gates['cap_owner']!=spec['owner']:
        raise ValueError('Owner record mismatch')
    accepted(gates['runtime_review'],'t8-cap-9600-runtime',release['source_files'],digest(spec))
    proposal=gates['t8_timing_proposal']
    if (digest(proposal)!=ORIGINAL_PROPOSAL or proposal!=spec['original_failed_timing_proposal']
        or spec['original_proposal_digest']!=ORIGINAL_PROPOSAL
        or gates['t8_numeric_review'].get('original_N2_passed') is not False
        or gates['t8_numeric_review'].get('post_hoc_engineering_deviation') is not True):
        raise ValueError('Original failed timing proposal must remain exact and disclosed')
    validate_timing_gate(cfg,release,spec)
    # Runtime dependency gates must exactly reuse the historical G1 proof.
    old=spec['original_g1_releases'][str(cfg['draw'])]['gates']
    for key in ('required_terminals','pool_terminals','student_completion_owner','student_slot_transfer','upload'):
        if gates[key]!=old[key]:
            raise ValueError('Original data/dependency authority changed')
    return True


'''
Path('experiments/sft_allocation_p008/student_t8_cap_binding.py').write_text(header+method+'\n')
# Same finite function, model code and original scientific claim. Only explicit
# operational policy and supplementary accounting differ.
s=Path('experiments/sft_allocation_p008/modal_students_t8.py').read_text()
s=s.replace('modal_students_t8.py','modal_students_t8_cap.py').replace("SPEC='reports/p008_20261013/student_admission_v1/ADMISSION.json'","SPEC='reports/p008_20261013/student_t8_cap_9600_v1/ADMISSION.json'")
s=s.replace("'p008-eight-original-t8-after-n2'","'p008-eight-t8-owner-cap-9600'")
s=s.replace("'experiments/sft_allocation_p008/provider_release.py']","'experiments/sft_allocation_p008/provider_release.py', 'experiments/sft_allocation_p008/student_t8_cap_binding.py']")
s=s.replace('start+9560','start+9600').replace('timeout=9620','timeout=9660')
s=s.replace('from experiments.sft_allocation_p008.student_t8_binding import validate_student_binding,require_timing_terminals','from experiments.sft_allocation_p008.student_t8_cap_binding import validate_student_binding,require_timing_terminals,register_amendment,reserve_supplement,verify_supplement,supplement_key,AMENDMENT_KEY,amendment_record')
s=s.replace("spec['original_plan']","spec['original_spec']['original_plan']")
s=s.replace("guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())","guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())\n register_amendment(claims,spec)")
s=s.replace("max_runtime_seconds=config['max_seconds']+30)","max_runtime_seconds=9630)\n supplement=reserve_supplement(claims,spec,admitted)")
s=s.replace("reserved_cents=reserve));dump(out/'admission.json',spec)","reserved_cents=reserve,effective_worker_seconds=9600,total_reserved_cents=reserve+5,supplement=supplement));dump(out/'admission.json',spec)")
s=s.replace("reserved_cost_usd=reserve/100","reserved_cost_usd=(reserve+5)/100,registered_slot_reserved_usd=reserve/100,supplement_reserved_usd=.05")
s=s.replace("files=manifest(out);dump(out/'artifact_manifest.json',files)","verify_supplement(claims,spec,run)\n  files=manifest(out);dump(out/'artifact_manifest.json',files)")
s=s.replace("time.time()+cfg['max_seconds']+700","time.time()+9600+700")
s=s.replace("# One lock for original", "if claims.get(supplement_key(run)) is not None:raise ValueError('Existing supplement; no replay')\n  old_amendment=claims.get(AMENDMENT_KEY)\n  if old_amendment is not None and old_amendment!=amendment_record(spec):raise ValueError('Conflicting immutable amendment')\n  # One lock for original")
s=s.replace('Prepared T8-only successor after exact numerical N2 and both-queue checks.','Owner-authorized +40s operational amendment; original failed N2 retained.')
Path('experiments/sft_allocation_p008/modal_students_t8_cap.py').write_text(s)
s=Path('scripts/audit_p008_student_t8.py').read_text().replace('from experiments.sft_allocation_p008.student_t8_binding import validate_student_binding,require_timing_terminals','from experiments.sft_allocation_p008.student_t8_cap_binding import validate_student_binding,require_timing_terminals,verify_supplement')
s=s.replace("require_timing_terminals(db,sent['release']['gates'])","require_timing_terminals(db,sent['release']['gates'])\n supplement=verify_supplement(db,spec,run)\n assert sent['supplement']==supplement and sent['effective_worker_seconds']==9600 and sent['reserved_cents']==1253 and sent['total_reserved_cents']==1258")
s=s.replace("result=read(root/'result.json');assert result==env['result']","result=read(root/'result.json');assert result==env['result']\n assert result['registered_slot_reserved_usd']==12.53 and result['supplement_reserved_usd']==.05 and result['reserved_cost_usd']==12.58\n assert receipt['actual_cost_cents']==1253  # original conservative reservation, not invoice\n assert claim['deadline_epoch']-claim['claimed_epoch']==9630")
s=s.replace("new_model_calls=0,external_review='pending')","new_model_calls=0,external_review='pending',original_N2_passed=False,post_hoc_engineering_deviation=True,\n   effective_worker_seconds=9600,total_reserved_cents=1258,supplement_reserved_cents=5)")
Path('scripts/audit_p008_student_t8_cap.py').write_text(s)
for n in ['experiments/sft_allocation_p008/student_t8_cap_binding.py','experiments/sft_allocation_p008/modal_students_t8_cap.py','scripts/audit_p008_student_t8_cap.py']:
 ast.parse(Path(n).read_text())
print('New sources/spec/owner PREPARED only; zero cloud/old oracle work',now)
