"""P008 future student-only admission; no pool or implicit G1 authorization."""
from experiments.sft_allocation_midpoint.common import digest
from .main_binding import validate_binding


def validate_student_binding(plan,cfg,release,spec):
    if cfg['role'] not in ('main','bridge','base'):
        raise ValueError('Student-only entry; pool calls are permanently separate')
    validate_binding(plan,cfg,release,spec)
    gates=release['gates'];joint=gates.get('joint_plan_gate',{})
    if (joint.get('passed') is not True or len(joint.get('sha256',''))!=64
        or joint['sha256']!=spec.get('common_plan_gate_sha256')):
        raise ValueError('Exact all-draw pre-outcome plan evidence missing')
    terminals=gates.get('pool_terminals',[])
    required={(plan['campaign_id'],f'pool_d{d}') for d in range(1,spec['branch'][2]+1)}
    keys=[(x['campaign'],x['run_id']) for x in terminals]
    if set(keys)!=required or len(keys)!=len(required) or any(x['terminal'].get('status')!='completed' for x in terminals):
        raise ValueError('Actual completed pool roster missing')
    if cfg['role']!='base':
        review=gates['draw_review']
        if len(review.get('review_report_sha256',''))!=64 or len(review.get('target_commit',''))!=40:
            raise ValueError('G1 must identify its real fixed report and target')
        if review.get('input_sha256')!=cfg['input_sha256'] or review.get('common_plan_gate_sha256')!=joint['sha256']:
            raise ValueError('G1 does not cover exact all-draw plans and input inventory')
    if spec.get('pool_admission_sha256')!=gates.get('pool_admission_sha256') or len(spec.get('pool_admission_sha256',''))!=64:
        raise ValueError('Original immutable pool admission provenance missing')
    return True
