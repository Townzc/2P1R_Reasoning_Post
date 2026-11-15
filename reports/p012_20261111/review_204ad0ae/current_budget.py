"""Add the four reserved A8 T arms to the unchanged original/A6/A7 ledger."""
import importlib.util
import json
from pathlib import Path

ROOT = Path('.local/p012_20261111')
PUBLIC = Path('reports/p012_20261111')
spec = importlib.util.spec_from_file_location('p012_pre_a8_budget', PUBLIC / 'review_46e98da5/current_budget.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
read = lambda p: json.loads(Path(p).read_text())


def accounting():
    before = prior.accounting()
    admission = PUBLIC / 'amendment8_T_admission_v1/ADMISSION.json'
    components = []
    if admission.exists():
        for row in read(admission)['arms']:
            tr = ROOT / 'amendment8_tinker_runs_v1' / row['run_id']
            ev = tr.with_name(tr.name.replace('_s17_', '_s17_greedy_'))
            for d, kind, reserved in [(tr, 'training', row['training_buffered_usd']),
                                      (ev, 'evaluation', row['reserved_greedy_usd'])]:
                complete = (d / 'result/COMPLETE.json').exists()
                if complete:
                    assert read(d / 'result/COMPLETE.json')['success']
                    value = read(d / 'result/USAGE.json')['upper_token_cost_usd'] + (0.1 if kind == 'training' else 0)
                else:
                    # A failed or unfinished call keeps its entire reservation until resolved.
                    value = reserved
                components.append({'run_id': d.name, 'kind': kind, 'complete': complete,
                                   'usd': value, 'original_reservation_usd': reserved,
                                   'partial_usage_present': (d / 'result/PARTIAL_USAGE.json').exists()})
    total = sum(x['usd'] for x in components)
    return {**before, 'pre_A8_accounted_and_reserved_usd': before['combined_reserved_usd'],
            'A8_components': components, 'A8_accounted_and_reserved_usd': total,
            'combined_reserved_usd': before['combined_reserved_usd'] + total,
            'caps_usd': {**before['caps_usd'], 'A8': 40},
            'canonical_budget_helper': 'reports/p012_20261111/review_204ad0ae/current_budget.py',
            'legacy_queue_bound': 'Existing GSM queue is already fully reserved in the original T ledger. '
                'Its historical all_tracks snapshots exclude A8; this overlay includes A8 exactly once.',
            'global_paid_storage_reserve_usd_included_once_in_original_T': 30}


def enforce(snapshot):
    for field, cap in [('original_T_accounted_and_reserved_usd', 340),
                       ('A6_2_accounted_and_reserved_usd', 48), ('A6_3_accounted_and_reserved_usd', 38),
                       ('A7_accounted_and_reserved_usd', 60), ('A8_accounted_and_reserved_usd', 40),
                       ('combined_reserved_usd', 485)]:
        assert snapshot[field] <= cap, (field, snapshot[field], cap)
