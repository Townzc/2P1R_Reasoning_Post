"""Exact failed-parent, reasoned owner exception and same-category D1 binding."""
from pathlib import Path
from decimal import Decimal,ROUND_CEILING
from collections import Counter
from experiments.p010.common import read,sha,verify,CAPS
from experiments.p010.tier3_dispatch import fixed_review
from experiments.p010.settlement_d1 import settle,gross


def owner_review(spec,owner,audit,spec_file):
    if (owner.get('approved') is not True or owner.get('scope')!='p010-C6-only-unattempted-T72-cell-owner-exception'
            or not isinstance(owner.get('reason'),str) or not owner['reason'].strip()
            or sha(owner['local_evidence_file'])!=owner['evidence_sha256']
            or owner.get('owner_delegation_sha256')!=spec['owner_delegation_sha256']
            or owner.get('proposal_sha256')!=spec['owner_proposal_sha256']
            or owner.get('new_outputs')!=2500 or owner.get('reuse_saved_outputs')!=18871
            or owner.get('no_old_output_regeneration') is not True):
        raise ValueError('Actual explicit reasoned delegated owner exception required')
    clean=fixed_review(audit)
    if (audit.get('scope')!=spec['runtime_review_scope'] or audit.get('spec_sha256')!=sha(spec_file)
            or audit.get('source_files')!=spec['source_files']
            or audit.get('verification_source_files')!=spec['verification_source_files']
            or audit.get('owner_decision_evidence_sha256')!=owner['evidence_sha256']
            or audit.get('failed_parent_manifest_sha256')!=spec['failed_parent_manifest_sha256']
            or audit.get('same_I_D1_coverage_scope_accepted') is not True
            or audit.get('reuse18871_generate2500_only') is not True
            or audit.get('first_paid_measurement_exceptions')!=0):
        raise ValueError('Independent exact full source/input/numeric A2 required')
    return dict(owner={k:v for k,v in owner.items() if k!='local_evidence_file'},runtime_A2=clean)


def validate_I_settlement(spec,fresh):
    p=Path(spec['I_settlement_packet']);verify(p,spec['I_settlement_files'])
    original=read(p/'I_SEARCH_D1_PROPOSAL.json');proof=read(p/'SEARCH_PROVIDER_PROJECTION.json')
    if sha(p/'I_SEARCH_D1_PROPOSAL.json')!=spec['I_settlement_proposal_sha256']:raise ValueError('Exact I proposal differs')
    for n,v in read(p/'SOURCE_BASIS.json').items():
        if Path(n).stat().st_size!=v['bytes'] or sha(n)!=v['sha256']:raise ValueError('Original billing evidence changed')
    private=Path('.local/p010_20261019/r1/cue_search_export_r1/PROVIDER_PRIVATE.json')
    if sha(private)!=proof['original_private_sha256']:raise ValueError('Original stopped-owned0 proof changed')
    old=read(private);life=old['original_info'][0]['lifecycle']
    if old['owned']!=[] or old['app_id']!=proof['app_id'] or any(life[k]!=proof[k] for k in ('state','created_at','stopped_at')):
        raise ValueError('Exact search lifecycle projection differs')
    hourly=read(p/'SEARCH_HOURLY_ROWS.json');history=read(p/'SEARCH_HISTORICAL_ROWS.json');app=proof['app_id']
    item=settle(app,'3.26',proof,hourly,[gross(v,app) for v in history.values()])
    if item!=original['item']:raise ValueError('Original D1 arithmetic differs')
    charge=(max(gross(fresh,app),Decimal(item['observed_gross_max_usd']))*Decimal('1.2')).quantize(Decimal('.01'),rounding=ROUND_CEILING)
    if charge!=Decimal(item['charged_usd']):raise ValueError('Fresh meter changes fixed I charge; no implicit revision')
    return item


def effective_totals(root,records,containers,states,spec,fresh):
    """All immutable reservations counted once; only separately accepted D1 charges replace them."""
    totals={k:Decimal(0) for k in CAPS};apps=[];pending=0
    for path in records:
        b=read(path)['budget'];category=b['category'];amount=Decimal(b['new_reserved_usd'])
        if category not in totals or not amount.is_finite() or amount<0:raise ValueError('Invalid original reservation')
        totals[category]+=amount
        if (path.parent/'SUBMITTED.json').exists():apps.append(read(path.parent/'SUBMITTED.json')['app_id'])
        else:pending+=1
    if len(apps)!=len(set(apps)):raise ValueError('Duplicate app ownership')
    counts=Counter(x.get('app_id') for x in containers);slots=pending
    for app in apps:
        n=counts.pop(app,0);slots+=n if str(states.get(app,'unknown')).lower()=='stopped' else max(1,n)
    slots+=sum(counts.values());effective=dict(totals);eg=None
    if totals['G']==Decimal('55.13'):
        from experiments.p010.e3_settlement_binding import validate_settlement
        es=read(spec['E3_spec_file']);applied=read(Path(root)/'e3_runs/temperature_supply_r1/D1_SETTLEMENT_APPLIED.json')
        review=read(Path(root)/'E3_RUNTIME_A1_A2_ACCEPTED.json');fixed_review(review)
        if (sha(spec['E3_spec_file'])!=spec['E3_spec_sha256'] or applied.get('actual_release_applied') is not True
                or applied['runtime_spec_sha256']!=spec['E3_spec_sha256'] or review['spec_sha256']!=spec['E3_spec_sha256']
                or review['source_files']!=es['source_files'] or review.get('D1_hourly_coverage_scope_accepted') is not True
                or applied['exact_A2_report_sha256']!=review['report_sha256'] or applied['proposal_sha256']!=es['settlement_proposal_sha256']):
            raise ValueError('Previously applied E3 D1 exact proof required')
        eg=validate_settlement(es,fresh);effective['G']=Decimal(eg['proposed_charged_G_usd'])+Decimal('11.13')
    elif totals['G']!=44:raise ValueError('Unrecognized G reservation or settlement state')
    if totals['I']!=Decimal('14.43'):raise ValueError('Only original unattempted C6 remaining slot is allowed')
    si=validate_I_settlement(spec,fresh);effective['I']=totals['I']-Decimal('3.26')+Decimal(si['charged_usd'])
    if any(effective[k]>CAPS[k] for k in CAPS) or sum(effective.values())>240:
        raise ValueError('Actual effective categories exceed frozen caps')
    return totals,effective,slots,dict(I=si,already_applied_E3_G=eg)
