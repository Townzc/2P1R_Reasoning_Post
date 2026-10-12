"""One-shot child submission with immutable evidence and non-cancelling waits.

This module never retries a spawn, releases a claim, or reconstructs a lost call.
An interruption after the intent is an operator reconciliation case.
"""
from .common import digest


def validate_replacement(store, plan, binding):
    """Bind a fresh, explicitly costed replacement to its terminal failed parent."""
    if (binding['replacement_campaign'] != plan['campaign_id'] or
            binding['parent_campaign'] == plan['campaign_id'] or
            binding['replacement_count_cap_per_failed_run'] != 1 or
            binding['replacement_is_not_exact_resume'] is not True or
            binding['old_app_stopped'] is not True or binding['old_containers'] != 0 or
            binding['deadline_epoch'] != plan['deadline_epoch']):
        raise ValueError('Replacement binding does not match this finite campaign')
    prefix = 'midpoint/' + binding['parent_campaign'] + '/'
    if store.get(prefix + 'terminal/controller') != binding['old_controller_terminal']:
        raise ValueError('Parent controller evidence changed')
    if binding['old_controller_terminal']['status'] != 'failed':
        raise ValueError('Parent controller must be terminal failed')
    for name in binding['fresh_replacement_runs']:
        record = binding['old_runs'][name]
        if (record['terminal']['status'] != 'failed' or
                store.get(prefix + 'terminal/' + name) != record['terminal']):
            raise ValueError('Failed parent evidence changed: ' + name)
    for name in binding['previously_unattempted_runs']:
        if store.get(prefix + 'claim/' + name) is not None:
            raise ValueError('Previously unattempted parent was claimed: ' + name)
    names = binding['fresh_replacement_runs'] + binding['previously_unattempted_runs']
    if len(names) != len(set(names)) or set(names) != set(plan['slots']) - {'controller'}:
        raise ValueError('Replacement queue differs from reconciled work')


def spawn_once(store, key, function, args, record, persist):
    intent = {**record, 'arguments_sha256': digest(args)}
    if not store.put(key + '/intent', intent, skip_if_exists=True):
        raise RuntimeError('Dispatch already attempted; reconcile: ' + key)
    persist('intent', intent)
    call = function.spawn(*args)
    receipt = {'call_id': call.object_id, 'intent_sha256': digest(intent)}
    if not store.put(key + '/submitted', receipt, skip_if_exists=True):
        raise RuntimeError('Conflicting submission evidence: ' + key)
    persist('submitted', receipt)
    return call


def wait_existing(call, check, failed=lambda: False):
    """Polling an existing call is read-only; an error never spawns another call."""
    while True:
        check()
        try:
            return call.get(timeout=30)
        except TimeoutError:
            # Modal signals a pending FunctionCall with a local TimeoutError.
            # A worker may itself raise builtin TimeoutError. Its immutable
            # failed receipt distinguishes that error from a pending poll.
            if failed():
                raise
            continue
