"""Fail-closed new extension money/attempt contract, independent of old P011 gates."""
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from experiments.p011.ext4b_contract import OWNER_SHA
from experiments.p011.ext3b_contract import LARGE,SMALL
from experiments.p011.owner_0205_common import read,sha

SPEC='reports/p011_20261020/ext3b_preentry_schema_runtime_v3/SPEC.json'
SCOPE='p011-ext-3B-complete-training-resume-MATH-path-CR'
A2_SCOPE='p011-ext-3B-actual-input-and-numeric-A2-lite'
LOCAL=Path('.local/p011_20261020/r1/ext3b_runs_r1')
INPUTS=Path('.local/p011_20261020/r1/ext3b_inputs_r1')
REMOTE='/evidence/p011-ext-3B-20261022'
STORE='p011-ext-3B-20261022-v1'
JOBS=(LARGE,SMALL)
PAIR_CAP=Decimal('90')
CELL_CAP=Decimal('45')
NONCOMPUTE_PER_CELL=Decimal('5')
STARTUP=600
GRACE=60
HARD_CEILING=50400


def cost_window(rate, prior_compute_upper='0', retained_noncompute='5'):
    """Charge initial+resume together; no forecast can enlarge the money cap.

    Five dollars per cell is a retained noncompute allowance, not measured cost
    or a guarantee. Real observed noncompute above it raises this parameter and
    shrinks the time window. Prior upper bounds can only be narrowed with saved
    actual terminal timing/charge evidence; they are never reset for a resume.
    """
    rate,prior,other=map(Decimal,map(str,(rate,prior_compute_upper,retained_noncompute)))
    if not all(x.is_finite() for x in (rate,prior,other)) or rate<=0 or prior<0 or other<NONCOMPUTE_PER_CELL:
        raise ValueError('Finite rate and retained compute/noncompute accounting required')
    paid_seconds=int(((CELL_CAP-prior-other)*3600/rate).to_integral_value(rounding=ROUND_FLOOR))
    worker=min(HARD_CEILING,paid_seconds-STARTUP-GRACE)
    if worker<=0:raise ValueError('No affordable worker window remains')
    compute=Decimal(worker+STARTUP+GRACE)*rate/3600
    if prior+other+compute>CELL_CAP:raise ValueError('Per-cell hard cost envelope exceeded')
    return {'worker_seconds':worker,'platform_seconds':worker+GRACE,'startup_seconds':STARTUP,
            'hourly_rate_usd':str(rate),'prior_compute_upper_usd':str(prior),
            'retained_noncompute_usd':str(other),'new_compute_upper_usd':str(compute),
            'cumulative_cell_upper_usd':str(prior+other+compute),'cap_usd':'45',
            'maximum_14h_is_not_affordability_guarantee':True,'not_final_invoice':True}


def prepared_spec(spec_path):
    """Exact candidate bytes for metadata only; never source-review acceptance."""
    spec=read(spec_path)
    if (spec['owner_report_sha256']!=OWNER_SHA or spec['jobs']!=list(JOBS)
            or spec['pair_cap_usd']!='90' or spec['per_cell_cap_usd']!='45'
            or spec['large_questions']!=9072 or spec['small_questions']!=3024
            or spec['evaluation_scope']!='MATH500_ONLY_COMPLETE_ENDPOINTS'
            or spec['checkpoint_interval_updates']!=500 or spec['maximum_infrastructure_resumes_per_cell']!=1):
        raise ValueError('Exact amended candidate bounds required')
    amendment=spec['direct_owner_amendment']
    if sha(amendment['path'])!=amendment['sha256']:raise ValueError('Exact direct options2+3 amendment changed')
    for p,h in spec['source_files'].items():
        if sha(p)!=h:raise ValueError('Extension candidate source changed '+p)
    return spec


def actual_origin(spec):
    """Carry exact completed input bytes; never rewrite or re-upload the manifest."""
    binding=spec['unchanged_actual_input_binding']
    if (binding['spec_sha256']!='3a824522f32a5236cc65dc712bc8821f5cfeb86885dd39eaeec1d07d1f313f9e'
            or binding['actual_job_manifest_sha256']!='bf556ba4e18ab52b6613d6e86eec207ec6dedab9937accb2b754f94368453a24'
            or binding['input_manifest_sha256']!='afd5fe1bd7e13d28353d28fe4e7b6e2e296babcbc7752dc5cec843bdb7d17bfc'):
        raise ValueError('Only the exact completed 9072/3024 input manifest may carry forward')
    return binding


def entry_cli_directory(spec,job,attempt):
    if job not in JOBS or attempt not in (1,2):raise ValueError('Exact job/attempt required')
    return 'cli_preentry2' if attempt==1 and job in spec['preentry_schema_failures'] else 'cli'


def review(spec_path, source_review, actual_review=None):
    spec=prepared_spec(spec_path);cr=read(source_review)
    if (cr.get('scope')!=SCOPE or cr.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or cr.get('spec_sha256')!=sha(spec_path) or cr.get('source_files')!=spec['source_files']
            or sha(cr['local_report_path'])!=cr['report_sha256']
            or any(cr.get(k) is not True for k in spec['source_review_flags'])):
        raise ValueError('Exact new full training/resume/closeout CR required')
    if actual_review is not None:
        a2=read(actual_review)
        origin=actual_origin(spec)
        if (a2.get('scope')!=A2_SCOPE or a2.get('decision') not in ('PASS','PASS-WITH-NOTES')
                or a2.get('spec_sha256')!=sha(spec_path)
                or a2.get('input_manifest_sha256')!=sha(INPUTS/'MANIFEST.json')
                or a2.get('actual_job_manifest_sha256')!=origin['actual_job_manifest_sha256']
                or a2.get('unchanged_actual_origin_spec_sha256')!=origin['spec_sha256']
                or sha(a2['local_report_path'])!=a2['report_sha256']
                or any(a2.get(k) is not True for k in spec['actual_review_flags'])):
            raise ValueError('Exact actual input/numeric A2-lite required')
    return spec


def admit_attempt(job, attempt, prior, checkpoint, failure):
    if job not in JOBS or attempt not in (1,2):raise ValueError('Two fixed jobs and at most one resume')
    if attempt==1:
        if prior is not None or checkpoint is not None or failure is not None:raise ValueError('First attempt cannot inherit a fabricated failure')
    else:
        if (not prior or prior.get('job')!=job or prior.get('attempt')!=1
                or not checkpoint or not failure or failure.get('infrastructure_failure_confirmed') is not True
                or failure.get('provider_STOPPED_owned_zero') is not True
                or failure.get('scientific_or_hard_cap_failure') is not False
                or not failure.get('raw_evidence_sha256') or not failure.get('raw_evidence_path')):
            raise ValueError('One exact stopped infrastructure parent and checkpoint required')
        if sha(failure['raw_evidence_path'])!=failure['raw_evidence_sha256']:
            raise ValueError('Failure evidence changed')
    return f'{job}_attempt{attempt}'
