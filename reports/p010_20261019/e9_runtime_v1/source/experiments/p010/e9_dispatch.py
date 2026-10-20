"""Only the delegated E9 amendment, with exact A1/A2 and issued original A4."""
from experiments.p010.common import sha
from experiments.p010.e9_contract import RUNS
from experiments.p010.tier3_dispatch import fixed_review,validate_a4,attempted_records,totals_and_slots


def validate_data(spec,run,review):
    b=spec['data_binding']
    if (run not in RUNS or review.get('scope')!='p010-E9-exact-input-and-plan-A1'
            or review.get('target_commit')!=b['target_commit']
            or review.get('basis_sha256')!=b['basis_sha256']
            or review.get('input_archive_sha256')!=b['input_archive_sha256']
            or review.get('source_files')!=b['source_files']):
        raise ValueError('Exact E9 input A1 required')


def validate_owner(spec,owner):
    if (sha(owner['local_report_file'])!=owner['report_sha256']
            or owner['report_sha256']!=spec['owner_D2_report_sha256']
            or owner['D2']['approved'] is not True or owner['D2']['Tier3_replaces']!='E5_Qwen3B'):
        raise ValueError('Actual delegated/owner D2 required; no E5 revival')
    return {k:v for k,v in owner.items() if k!='local_report_file'}
