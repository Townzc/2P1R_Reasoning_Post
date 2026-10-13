"""Read-only CPU evidence binding for original and replacement student states.

Use the pre-result frozen input bytes. Do not recompute cosine on another host
as an exact-equality provenance test. This helper alone admits no CPU run.
"""
import hashlib
import json
import math
from .audit_lineage_binding import evidence_file_hash
from experiments.sft_allocation_midpoint.common import digest

ORIGINAL_SPEC = 'ab49b0a638090f61dfd39e7391c61e4427a47b6ea94acfe6e0de3c4f606b21ee'
REPLACEMENTS = {
    n + '_replacement_r1': n
    for n in ('d1_b1_p0_breadth_t1', 'd1_b1_p0_depth_t1')
}


def checked_plan(label, recipe):
    """Return the actual frozen plan after exact source-input identity checks.

The surrounding CPU admission still must bind claim, terminal, provider release,
the physical replacement authority, the exact label and the independent oracle.
"""
    cfg = label['config']
    spec = label['original_student_spec']
    physical = label['run_id']
    logical = REPLACEMENTS.get(physical, physical)
    if digest(spec) != ORIGINAL_SPEC or logical not in spec['configs']:
        raise ValueError('Exact original pre-result student admission required')
    science = spec['configs'][logical]
    expected = dict(science)
    if physical in REPLACEMENTS:
        expected.update(run_id=physical, logical_run_id=logical)
    if cfg != expected or cfg['run_id'] != physical or cfg['role'] not in ('main', 'bridge'):
        raise ValueError('Physical/logical science config differs')
    proof = label['frozen_input_bytes']
    raw_manifest, raw_plan = proof['manifest_json'], proof['plan_json']
    metadata = json.loads(raw_manifest)
    if evidence_file_hash(raw_manifest, metadata) != cfg['input_sha256']:
        raise ValueError('Frozen input manifest bytes differ')
    record = metadata['files'][cfg['plan_file']]
    raw = raw_plan.encode('utf-8')
    if len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
        raise ValueError('Frozen per-student schedule/LR bytes differ')
    plan = json.loads(raw_plan)
    run = plan['run']
    if any(run[k] != science[k] for k in run):
        raise ValueError('Frozen schedule belongs to another logical student')
    if (len(plan['updates']) != cfg['updates'] or len(plan['lrs']) != cfg['updates']
            or plan['supervised_targets'] != cfg['targets']
            or plan['targets_are_frozen_before_student_scores'] is not True
            or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in plan['lrs'])):
        raise ValueError('Invalid frozen trajectory')
    identity = recipe['identity']
    if (identity['config'] != science or recipe['schedule'] != plan['updates']
            or recipe['lrs'] != plan['lrs']):
        raise ValueError('Saved state identity/schedule differs from frozen input')
    if physical in REPLACEMENTS:
        if identity.get('physical_run_id') != physical:
            raise ValueError('Replacement state lacks its distinct physical identity')
    elif 'physical_run_id' in identity:
        raise ValueError('Original state unexpectedly carries replacement identity')
    return plan


def check_state_trajectory(state, recipe, plan, step):
    if (state['step'] != step or state['cursor'] != step
            or state['schedule'] != recipe['schedule'] or state['schedule'] != plan['updates']
            or state['lrs'] != plan['lrs']):
        raise ValueError('Full state differs from exact frozen trajectory')
    return True
