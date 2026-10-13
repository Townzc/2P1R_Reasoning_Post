"""Pure admission checks for future P008 main calls; no implicit authorization."""
import math
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_midpoint.guard import RunGuard
from .contract import DEADLINE_EPOCH,run_roster

RATE_USD_PER_HOUR=4.393584


def accepted(review,scope,source_files,spec_sha256):
    if (review.get('verdict') not in ('PASS','PASS-WITH-NOTES') or review.get('scope')!=scope
        or len(review.get('review_commit',''))!=40 or len(review.get('review_report_sha256',''))!=64
        or review.get('source_files')!=source_files or review.get('spec_sha256')!=spec_sha256):
        raise ValueError('Exact-scope external review is missing or differs')


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
    required={('p008-phase0-20261013-r1',r) for r in ('teacher_calibration','student_smoke','io_probe_a','io_probe_b')}
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
        required|={(plan['campaign_id'],f'pool_d{d}') for d in range(1,spec['branch'][2]+1)}
    got=[(t['campaign'],t['run_id']) for t in gates['required_terminals']]
    if len(got)!=len(set(got)) or set(got)!=required or any(t['terminal']['status']!='completed' for t in gates['required_terminals']):
        raise ValueError('Required real terminal roster differs')
    return True
