"""P010 scope, immutable records and category accounting (USD)."""
from decimal import Decimal
from pathlib import Path
import datetime

from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, manifest, verify

PLAN_COMMIT = '4287537f7733f5c3568ddb11695d47b566ef75fa'
CAPS = {'G': Decimal('50'), 'T': Decimal('150'), 'I': Decimal('15'), 'C': Decimal('25')}
MODELS = {
    't15': ('Qwen/Qwen2.5-Math-1.5B-Instruct', 'aafeb0fc6f22cbf0eaeed126eff8be45b0360a35'),
    't7': ('Qwen/Qwen2.5-Math-7B-Instruct', 'ef9926d75ab1d54532f6a30dd5e760355eb9aa4d'),
    't72': ('Qwen/Qwen2.5-Math-72B-Instruct', '8fcf92b1eac8eca48c3d49778ad3dd1b394c9a17'),
    'olmo': ('allenai/OLMo-2-0425-1B', 'a1847dff35000b4271fa70afc5db10fd29fedbdf'),
    'qwen': ('Qwen/Qwen2.5-1.5B', '8faed761d45a263340a0528343f099c05c9a4323'),
    'qwen3b': ('Qwen/Qwen2.5-3B', '3aab1f1954e9cc14eb9509a215f9e5ca08227a9b'),
}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def budget_check(category, prior_reserved, new_reserved, predicted):
    """Never combine a full reservation with its already included actual charge.

    Prior reservations include ended runs until reconciliation; no automatic
    transfer between categories. Amounts are allowances, never invoices.
    """
    values = [Decimal(str(v)) for v in (prior_reserved, new_reserved, predicted)]
    if category not in CAPS or any(not v.is_finite() or v < 0 for v in values):
        raise ValueError('Invalid category or non-finite cost')
    prior, reserve, forecast = values
    remaining = CAPS[category] - prior
    if reserve > remaining or forecast > Decimal('.8') * remaining or forecast > reserve:
        raise ValueError('Forecast/reservation exceeds the frozen category budget')
    return dict(category=category, cap_usd=str(CAPS[category]), prior_reserved_usd=str(prior),
        new_reserved_usd=str(reserve), forecast_usd=str(forecast), remaining_before_usd=str(remaining),
        maximum_forecast_fraction='.8', not_actual_spending=True)


def require_published(repo):
    import subprocess
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/codex/icml-acl-2027'],
        cwd=repo, text=True).split()[0]
    if commit != remote:
        raise ValueError('Publish this execution source before starting')
    changed = subprocess.check_output(['git', 'status', '--porcelain', '--',
        'experiments/p010', 'experiments/sft_allocation_midpoint/common.py'],
        cwd=repo, text=True)
    if changed:
        raise ValueError('Execution source is uncommitted or untracked')
    return commit
