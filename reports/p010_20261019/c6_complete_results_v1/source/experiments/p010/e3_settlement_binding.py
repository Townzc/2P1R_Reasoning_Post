"""Reconstruct the reviewed D1 evidence without applying a release."""
from pathlib import Path
from decimal import Decimal,ROUND_CEILING
from experiments.p010.common import read,sha,verify
from experiments.p010.settlement_d1 import settle,summary,gross


def validate_settlement(spec, fresh_report=None):
    root=Path(spec['settlement_packet'])
    verify(root,spec['settlement_files'])
    proposal=read(root/'PROPOSAL.json');providers=read(root/'PROVIDER_PROJECTIONS.json')
    hourly=read(root/'HOURLY_ORIGINAL_APP_ROWS.json');history=read(root/'HISTORICAL_APP_ROWS.json')
    for name,binding in read(root/'SOURCE_BASIS.json').items():
        if sha(name)!=binding['sha256'] or Path(name).stat().st_size!=binding['bytes']:
            raise ValueError('Original saved provider/billing/reservation evidence changed')
    if sha(root/'PROPOSAL.json')!=spec['settlement_proposal_sha256']:
        raise ValueError('Exact audited settlement candidate required')
    output=[]
    for original in proposal['items']:
        name=original['original_receipt_directory'];app=original['app_id']
        totals=[gross(rows,app) for rows in history.values() if any(x.get('object_id')==app for x in rows)]
        item=settle(app,original['original_reserved_usd'],providers.get(name),hourly,totals)
        if any(original.get(k)!=v for k,v in item.items()):
            raise ValueError('Audited original D1 per-app arithmetic differs')
        if fresh_report is not None and item['eligible']:
            actual=gross(fresh_report,app)
            newcharge=(max(actual,Decimal(item['observed_gross_max_usd']))*Decimal('1.2')).quantize(Decimal('.01'),rounding=ROUND_CEILING)
            if newcharge!=Decimal(item['charged_usd']):
                raise ValueError('Fresh gross meter changes the fixed candidate charge; preserve and revise explicitly')
        output.append(item)
    result=summary(output)
    if any(proposal.get(k)!=v for k,v in result.items()) or not result['E3_D4_numeric_condition']:
        raise ValueError('Full six-app audited D1/D4 numeric result differs')
    return result
