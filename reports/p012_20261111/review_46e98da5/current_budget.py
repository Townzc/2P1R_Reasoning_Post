"""Current owner-approved caps over the unchanged accounting calculations."""
import sys
sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_accounting import accounting as legacy_accounting, read, sha

POLICY = 'reports/p012_20261111/review_46e98da5/BUDGET_POLICY.json'


def accounting():
    policy = read(POLICY)
    assert policy['owner_approved']
    assert policy['accepted_review_commit'] == '46e98da59753315694ebc4a0699f0b7c6c37a9c5'
    assert (policy['A6_2_cap_usd'], policy['A6_3_cap_usd'], policy['combined_cap_usd']) == (48, 38, 485)
    result = legacy_accounting()
    result['legacy_reported_caps_usd'] = result['caps_usd']
    result['caps_usd'] = {'original_T': 340, 'A6-2': 48, 'A6-3': 38, 'A7': 60, 'combined': 485}
    result['current_budget_policy'] = {'path': POLICY, 'sha256': sha(POLICY)}
    return result
