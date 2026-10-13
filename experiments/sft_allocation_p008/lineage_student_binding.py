"""Prepared student admission preserving real failed-parent/child provenance.

Original runtime, plans, doses and primary endpoint remain unchanged. This
successor requires a new exact-source/spec G1 review before any student call.
"""
import math
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_midpoint.guard import RunGuard
from .contract import DEADLINE_EPOCH,run_roster
from .main_binding import accepted,RATE_USD_PER_HOUR
from .block_journal import POLICY
from .pool_lineage import validate_pool_lineages

def validate_binding(plan,cfg,release,spec):
    # The published spec and reviews are provenance records, not self-issued PASS.
    RunGuard({},plan)
    if (digest(plan)!=spec['plan_sha256'] or digest(cfg)!=spec['config_sha256'].get(cfg['run_id'])
        or plan['deadline_epoch']!=DEADLINE_EPOCH or plan['total_cap_cents']>23500
        or spec['phase0_cap_cents']!=1500 or spec['stage_cap_cents']!=25000
        or spec['project_ceiling_cents']!=45000 or spec['protected_cents']!=5000):
        raise ValueError('Unadmitted plan/config/budget/deadline')
    if digest(spec)!=release['spec_sha256']:raise ValueError('Spec differs from reviewed release')
    gates=release['gates'];accepted(gates['runtime_review'],'main-runtime',release['source_files'],digest(spec))
    phase=gates['phase0']
    if not (phase['oracle_passed'] is True and phase['four_gpu_verified'] is True and phase['provider_released'] is True
            and len(phase['oracle_sha256'])==64):raise ValueError('Phase0 evidence cannot admit four-way main work')
    if not (gates['upload']['passed'] is True and gates['upload']['input_sha256']==cfg['input_sha256']):
        raise ValueError('Exact input readback missing')
    if not 0<cfg['max_seconds']<=10800:raise ValueError('Finite slot timer missing')
    minimum=math.ceil((cfg['max_seconds']+700)*RATE_USD_PER_HOUR/3600*100)
    if plan['slots'][cfg['run_id']]['reserved_cents']<minimum:raise ValueError('Startup/closing runtime under-reserved')
    if spec['branch'] not in ([8,True,2],[8,False,2],[4,False,2],[4,False,1]):raise ValueError('Unknown branch')
    expected={r['run_id']:r for r in run_roster(*spec['branch'])}
    phase_required={('p008-phase0-20261013-r1',r) for r in ('teacher_calibration','student_smoke','io_probe_a','io_probe_b')}
    if cfg['role']=='pool':
        if cfg['draw'] not in range(1,spec['branch'][2]+1) or cfg['high_multiple']!=spec['branch'][0] or cfg['max_physical_attempts']!=16384:
            raise ValueError('Pool scope differs')
        if cfg['run_id']!=f"pool_d{cfg['draw']}":raise ValueError('Pool slot identity differs')
    elif cfg['role']=='base':
        if cfg['run_id']!='base' or cfg['updates']!=0 or cfg['targets']!=0:raise ValueError('Invalid base')
    else:
        if cfg['run_id'] not in expected:raise ValueError('Unregistered student')
        row=expected[cfg['run_id']]
        for k in ('draw','budget_multiple','price','policy','training_multiple','seed','role','updates'):
            if cfg[k]!=row[k]:raise ValueError('Student recipe differs')
        if cfg['targets']!=spec['common_targets'][str(cfg['training_multiple'])]:raise ValueError('Not a common target')
        if not (gates['joint_plan_gate']['passed'] is True and len(gates['joint_plan_gate']['sha256'])==64):
            raise ValueError('All-draw common plan gate missing')
        review=gates['draw_review']
        if review.get('draw')!=cfg['draw'] or review.get('verdict') not in ('PASS','PASS-WITH-NOTES') or len(review.get('review_commit',''))!=40:
            raise ValueError('This draw has not passed G1')
        if review.get('local_oracle_sha256')!=spec['draw_local_oracle_sha256'][str(cfg['draw'])]:raise ValueError('G1 refers to another pool')
    lineage=spec['pool_lineages']
    pool_records=validate_pool_lineages(lineage,spec['draw_local_oracle_sha256'])
    if gates.get('pool_lineage_sha256')!=digest(lineage) or gates.get('pool_terminals')!=pool_records:
        raise ValueError('Exact original failed parent plus completed child required')
    required={(c,r,'completed') for c,r in phase_required}
    required|={(x['campaign'],x['run_id'],x['terminal']['status']) for x in pool_records}
    got=[(x['campaign'],x['run_id'],x['terminal']['status']) for x in gates['required_terminals']]
    if len(got)!=len(set(got)) or set(got)!=required:
        raise ValueError('Actual phase/original/child terminal roster differs')
    for item in pool_records:
        if item not in gates['required_terminals']:raise ValueError('Changed dependency terminal')
    return True


def validate_student_binding(plan,cfg,release,spec):
    if cfg['role'] not in ('main','bridge','base'):
        raise ValueError('Student-only entry; pool calls are permanently separate')
    validate_binding(plan,cfg,release,spec)
    if spec.get('training_journal_policy') != POLICY:
        raise ValueError('Exact predeclared block journal policy missing')
    gates=release['gates'];joint=gates.get('joint_plan_gate',{})
    if (joint.get('passed') is not True or len(joint.get('sha256',''))!=64
        or joint['sha256']!=spec.get('common_plan_gate_sha256')):
        raise ValueError('Exact all-draw pre-outcome plan evidence missing')
    if cfg['role']!='base':
        review=gates['draw_review']
        if len(review.get('review_report_sha256',''))!=64 or len(review.get('target_commit',''))!=40:
            raise ValueError('G1 must identify its real fixed report and target')
        if review.get('input_sha256')!=cfg['input_sha256'] or review.get('common_plan_gate_sha256')!=joint['sha256']:
            raise ValueError('G1 does not cover exact all-draw plans and input inventory')
    if spec.get('pool_admission_sha256')!=gates.get('pool_admission_sha256') or len(spec.get('pool_admission_sha256',''))!=64:
        raise ValueError('Original immutable pool admission provenance missing')
    return True
