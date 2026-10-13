"""CPU-only final audit admission. Actual completed inputs are required later."""
import re
from experiments.sft_allocation_midpoint.common import digest
from .contract import DEADLINE_EPOCH

SOFT_MARGIN_SECONDS = 120


def check_soft_deadline(now,stop):
    """Leave time for partial-proof/failure persistence; never extend hard stop.

    A blocking filesystem or torch operation can still reach the hard timer.
    Such a run is interrupted, not falsely reported as a recorded soft failure.
    """
    if now>=stop-SOFT_MARGIN_SECONDS:
        raise TimeoutError('Original finite CPU deadline')


def validate(binding,spec,release):
    plan=binding['plan'];cfg=binding['config']
    if cfg!=dict(run_id='audit',role='audit',max_seconds=3300,readers=2,input_directory='audit_inputs'):
        raise ValueError('Unexpected CPU audit limits')
    if plan['deadline_epoch']!=DEADLINE_EPOCH or plan['slots']['audit']['reserved_cents']!=500:
        raise ValueError('Original deadline/reserved audit slot required')
    if spec['status']!='admitted_after_all_local_oracles_and_resource_release' or spec['binding_sha256']!=digest(binding):
        raise ValueError('No exact published final audit admission')
    if release['source_files']!=spec['source_files'] or release['spec_sha256']!=digest(spec):
        raise ValueError('Final audit source/spec differs')
    review=binding['code_review']
    if (review['decision'] not in ('PASS','PASS-WITH-NOTES') or review['scope']!='p008_cpu_integrity_code'
          or review['source_files']!=release['source_files']
          or not re.fullmatch('[0-9a-f]{40}',review['target_commit'])
          or not re.fullmatch('[0-9a-f]{64}',review['report_sha256'])):
        raise ValueError('Real scoped code review binding required')
    expected=set(plan['slots'])-{'audit'}
    if set(binding['labels'])!=expected or set(binding['config_sha256'])!=expected:
        raise ValueError('Final audit must cover every retained source slot')
    if len(expected)!=21 or not {'pool_d1','pool_d2','base'}<=expected:
        raise ValueError('Expected two pools/eighteen students/base')
    if set(binding['input_manifest']['files'])!={r+'.json' for r in expected}:
        raise ValueError('Exact immutable audit input roster required')
    for run,item in binding['labels'].items():
        if item['campaign']!=plan['campaign_id'] or item['run_id']!=run:
            raise ValueError('Foreign source label')
        if item['terminal']['status']!='completed':raise ValueError('Incomplete source terminal')
        if not item['provider_stopped'] or item['owned_containers']!=0:
            raise ValueError('Source resources not released')
    return expected


def validate_label(binding,run,label):
    item=binding['labels'][run]
    if label['campaign']!=item['campaign'] or label['run_id']!=run:
        raise ValueError('Foreign audit input identity')
    if digest(label)!=item['label_sha256'] or digest(label['config'])!=binding['config_sha256'][run]:
        raise ValueError('Exact input/config binding differs')
    if label['envelope']['receipt']!=item['terminal'] or label['local_oracle']['passed'] is not True:
        raise ValueError('Original completed receipt/oracle required')
    files=label['envelope']['artifact_manifest']
    if digest(files)!=item['terminal']['evidence_sha256']:
        raise ValueError('Original manifest digest differs')
    oracle=label['local_oracle']
    if oracle.get('artifact_digest',oracle.get('manifest_digest'))!=digest(files):
        raise ValueError('Local oracle does not bind source artifacts')
    return label
