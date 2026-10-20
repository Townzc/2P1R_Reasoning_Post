"""Original K1/E1d admission bookkeeping, including failed E4 and later children."""
from pathlib import Path
from decimal import Decimal
from collections import Counter
from experiments.p010.common import read


def original_T_records(root):
    root=Path(root)
    return (list(root.glob('e4_n*_r1/INTENT.json'))
            + list((root/'student_runs').glob('*/INTENT.json'))
            + list((root/'e4_endpoint_only_runs').glob('*/INTENT.json')))


def reserved_and_slots(paths, containers, app_states):
    """Retain every reservation; only real STOPPED releases a submitted slot.

    A callback RESULT/ERROR is not provider termination. Missing provider state,
    a pending submission and unrelated containers all count conservatively.
    """
    total=Decimal('0');submitted_apps=[];unknown=0
    for path in paths:
        item=read(path)['budget']
        if item['category']!='T':raise ValueError('Unexpected reservation category')
        amount=Decimal(item['new_reserved_usd'])
        if not amount.is_finite() or amount<0:raise ValueError('Invalid original reservation')
        total+=amount
        if (path.parent/'SUBMITTED.json').exists():
            submitted_apps.append(read(path.parent/'SUBMITTED.json')['app_id'])
        else:unknown+=1
    if len(set(submitted_apps))!=len(submitted_apps):raise ValueError('Ambiguous duplicate original app binding')
    observed=Counter(x.get('app_id') for x in containers)
    slots=unknown
    for app in submitted_apps:
        count=observed.pop(app,0)
        slots+=count if str(app_states.get(app,'unknown')).lower()=='stopped' else max(1,count)
    slots+=sum(observed.values())
    return total,slots


def validate_data_binding(spec,run,review):
    expected=spec['data_reviews'][run]
    if (review.get('scope')!=expected['scope']
            or review.get('data_manifest_sha256')!=expected['data_manifest_sha256']
            or review.get('target_commit')!=expected['data_fixed_commit']
            or expected['data_cell'] not in review.get('accepted_cells',[])):
        raise ValueError('Exact teacher-specific actual A1 evidence required')
    return True
