"""Outcome-blind local admission for the owner-approved eight-H100 ceiling.

All launches use one owner and one canonical filesystem. Pending calls consume
capacity before a claim exists. Provider containers without a matching pending
app consume additional capacity. This does not prove GPU availability.
"""
from contextlib import contextmanager
from pathlib import Path
import fcntl
from experiments.sft_allocation_midpoint.common import digest

MAXIMUM = 8


def validate_quota(spec, gates):
    quota = gates.get('student_quota', {})
    owner = gates.get('student_concurrency_owner', {})
    if (spec.get('maximum_concurrent_gpus') != MAXIMUM
            or owner.get('maximum_student_H100_workers') != MAXIMUM
            or owner.get('authority') != 'Direct human reply in this chat'
            or digest(owner) != spec.get('student_concurrency_owner_sha256')):
        raise ValueError('Exact direct owner concurrency authority missing')
    if (quota.get('confirmed') is not True
            or quota.get('gpu_type') != 'H100'
            or not quota.get('workspace_id')
            or quota.get('workspace_id') != spec.get('provider_workspace_id')
            or type(quota.get('available_quota')) is not int
            or quota['available_quota'] < MAXIMUM
            or len(quota.get('evidence_sha256', '')) != 64
            or not quota.get('observed_utc')
            or digest(quota) != spec.get('student_quota_sha256')):
        raise ValueError('Actual matching-workspace H100 quota evidence missing')
    return MAXIMUM


def occupied_capacity(pending, containers):
    """Union by app, conservatively counting every unmatched container."""
    runs = [x['run_id'] for x in pending]
    apps = [x['provider_app_id'] for x in pending]
    ids = [x['container_id'] for x in containers]
    if (len(set(runs)) != len(runs) or len(set(apps)) != len(apps)
            or len(set(ids)) != len(ids) or any(not x for x in apps + ids)):
        raise ValueError('Ambiguous pending/container identity')
    if any(not x.get('app_id') for x in containers):
        raise ValueError('Provider container app identity missing')
    count = sum(max(1, sum(c['app_id'] == app for c in containers)) for app in apps)
    count += sum(c['app_id'] not in apps for c in containers)
    return count


def require_capacity(pending, containers):
    count = occupied_capacity(pending, containers)
    if count >= MAXIMUM:
        raise ValueError('Eight-GPU ceiling includes queued/uncertain calls and other containers')
    return count


@contextmanager
def dispatch_lock(root):
    """Serialize local checks, intent persistence and spawn across processes."""
    with (Path(root) / '.student_dispatch.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Another local dispatch is in progress; no enqueue') from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
