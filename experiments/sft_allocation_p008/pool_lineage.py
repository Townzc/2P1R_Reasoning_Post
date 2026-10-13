"""True pool completion provenance after D2's separately audited continuation.

The original D2 remains failed. Its child completes only the missing suffix;
the independently decoded merged oracle, not a fabricated parent terminal,
certifies the usable completed draw. Pure validation, no storage or model calls.
"""
import re
from experiments.sft_allocation_midpoint.common import digest

PARENT_CAMPAIGN='p008-main-20261013-r1'
CHILD_CAMPAIGN='p008-d2-continuation-20261013-r1'
CHILD_RUN='pool_d2_remaining'


def _hash(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def validate_pool_lineages(lineages,oracle_hashes):
    if set(lineages)!={'1','2'} or set(oracle_hashes)!={'1','2'}:
        raise ValueError('Both complete draw lineages are required')
    one,two=lineages['1'],lineages['2']
    if one['kind']!='completed_original' or two['kind']!='failed_parent_completed_child':
        raise ValueError('Explicit original/continued provenance required')
    if (one['local_oracle_sha256']!=oracle_hashes['1']
            or two['merged_oracle_sha256']!=oracle_hashes['2']
            or not all(_hash(v) for v in oracle_hashes.values())):
        raise ValueError('Exact both-draw oracle binding differs')
    expected=((one['original'],PARENT_CAMPAIGN,'pool_d1','completed'),
              (two['parent'],PARENT_CAMPAIGN,'pool_d2','failed'),
              (two['child'],CHILD_CAMPAIGN,CHILD_RUN,'completed'))
    records=[]
    for item,campaign,run,status in expected:
        terminal=item['terminal'];claim=item['claim']
        if (item['campaign']!=campaign or item['run_id']!=run
                or terminal['status']!=status or terminal['claim_sha256']!=digest(claim)
                or not _hash(terminal['evidence_sha256'])
                or not _hash(claim['intent_sha256']) or not _hash(claim['plan_sha256'])):
            raise ValueError('Actual pool claim/terminal lineage differs')
        records.append(dict(campaign=campaign,run_id=run,terminal=terminal))
    proof=two['merged_proof']
    if not (proof['parent_plus_child_redecoded'] is True and proof['all_wallets_replayed'] is True
            and proof['parent_status']=='failed' and proof['child_status']=='completed'
            and proof['parent_physical_outputs']==3992
            and proof['physical_outputs']==3992+proof['child_physical_outputs']
            and proof['child_physical_outputs']>0
            and proof['parent_terminal']==two['parent']['terminal']
            and proof['child_terminal']==two['child']['terminal']
            and proof['parent_reconciliation_sha256']==two['parent_reconciliation_sha256']
            and _hash(two['parent_reconciliation_sha256'])
            and proof['passed'] is True):
        raise ValueError('Independent combined raw/wallet proof missing')
    return records
