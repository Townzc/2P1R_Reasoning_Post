"""Pure provisional settlement of stopped failures; never changes original claims."""
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import math

from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps

MIN_DELAY_BUFFER_CENTS = 50
PROPORTIONAL_BUFFER = Decimal('0.20')
MIN_STOPPED_AGE_SECONDS = 900
MAX_SNAPSHOT_AGE_SECONDS = 3600


def money(value):
    if not isinstance(value, str):
        raise ValueError('Use original decimal cost strings, not binary float values')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Invalid original metering value') from exc
    if not result.is_finite() or result < 0:
        raise ValueError('Nonnegative finite metering required; no credit netting')
    return result


def ceil_cents(usd):
    return int((usd*100).to_integral_value(rounding=ROUND_CEILING))


def app_meter(rows, app_id):
    matches = [r for r in rows if r.get('object_id') == app_id]
    if not matches:
        raise ValueError('Missing app metering is unknown, not zero')
    identities = [(r['object_id'], r['environment'], r['interval_start']) for r in matches]
    if len(set(identities)) != len(identities) or any(r['environment'] != 'main' for r in matches):
        raise ValueError('Duplicate or mismatched app metering rows')
    return sum((money(r['cost']) for r in matches), Decimal('0'))


def build_settlement(snapshots, closed, provider, now_epoch, pending_reserved_cents,
                     previous=None, stage_cap_cents=1000):
    """Maximum observed gross app meter plus explicit lag reserve, once per app.

    This is a budgeting overlay, not an invoice or a refund. New and active calls
    keep their full reservation. A later increase consumes released headroom;
    never clamp a reported cost to an old reservation or reduce a prior charge.
    """
    if (type(stage_cap_cents) is not int or stage_cap_cents != 1000
            or type(pending_reserved_cents) is not int or pending_reserved_cents < 0
            or not snapshots or not math.isfinite(now_epoch)):
        raise ValueError('Exact Stage0 cap and nonnegative full pending reserve required')
    epochs = [s['observed_epoch'] for s in snapshots]
    if (any(not math.isfinite(t) or t > now_epoch for t in epochs)
            or len(set(epochs)) != len(epochs)
            or not 0 <= now_epoch-max(epochs) <= MAX_SNAPSHOT_AGE_SECONDS):
        raise ValueError('Fresh original metering snapshot required')
    latest = snapshots[epochs.index(max(epochs))]
    ids = [r['app_id'] for r in closed]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Unique exact closed app roster required')
    validate_stopped_apps(ids, provider['original_app_info'], provider['owned_containers'])
    prior = {} if previous is None else {r['app_id']: r for r in previous['runs']}
    if not set(prior).issubset(ids):
        raise ValueError('No previously settled failed app may disappear')
    settled = []
    for row, info in zip(closed, provider['original_app_info']):
        claim, terminal = row['claim'], row['terminal']
        if (terminal.get('status') != 'failed' or claim.get('run_id') != row['run_id']
                or terminal.get('run_id') != row['run_id']
                or terminal.get('claim_sha256') != digest(claim)
                or terminal.get('attempt_id') != claim.get('attempt_id')
                or type(claim.get('reserved_cents')) is not int or claim['reserved_cents'] < 0
                or not math.isfinite(terminal['finished_epoch'])
                or latest['observed_epoch']-terminal['finished_epoch'] < MIN_STOPPED_AGE_SECONDS):
            raise ValueError('Require original failed claim and adequately aged terminal')
        stopped = datetime.fromisoformat(info['lifecycle']['stopped_at']).timestamp()
        if latest['observed_epoch']-stopped < MIN_STOPPED_AGE_SECONDS:
            raise ValueError('Provider has not been stopped long enough for provisional settlement')
        current = app_meter(latest['rows'], row['app_id'])
        history = [app_meter(s['rows'], row['app_id']) for s in snapshots
                   if any(r.get('object_id') == row['app_id'] for r in s['rows'])]
        old = prior.get(row['app_id'])
        if old is not None:
            if (old['claim_sha256'] != digest(claim)
                    or old['original_reserved_cents'] != claim['reserved_cents']):
                raise ValueError('Previously settled immutable claim changed')
            history.append(money(old['meter_floor_usd']))
        floor = max(history)
        rounded = ceil_cents(floor)
        delay = max(MIN_DELAY_BUFFER_CENTS,
                    int((Decimal(rounded)*PROPORTIONAL_BUFFER).to_integral_value(rounding=ROUND_CEILING)))
        accounted = rounded+delay
        if old is not None:
            accounted = max(accounted, old['accounted_cents'])
        settled.append(dict(app_id=row['app_id'], campaign=row['campaign'], run_id=row['run_id'],
            claim_sha256=digest(claim), terminal_sha256=digest(terminal), original_status='failed',
            original_reserved_cents=claim['reserved_cents'], current_meter_usd=str(current),
            meter_floor_usd=str(floor), rounded_meter_cents=rounded,
            delay_unattributed_allowance_cents=delay, accounted_cents=accounted,
            released_reservation_cents=claim['reserved_cents']-accounted))
    historical = sum(r['original_reserved_cents'] for r in settled)
    charged = sum(r['accounted_cents'] for r in settled)
    return dict(runs=settled, original_reserved_cents=historical, settled_failed_cents=charged,
        released_reservation_cents=historical-charged,
        full_pending_reserved_cents=pending_reserved_cents,
        stage_committed_cents=charged+pending_reserved_cents,
        stage_remaining_cents=stage_cap_cents-charged-pending_reserved_cents,
        stage_cap_cents=stage_cap_cents,
        fits_stage_cap=charged+pending_reserved_cents <= stage_cap_cents,
        metering_is_final_invoice=False, original_claims_mutated=False,
        automatic_replay_authorized=False, runtime_admitted=False,
        formula='ceil(max retained gross app meter in USD * 100) + max(50c, ceil(20% rounded meter cents)); never decrease prior accounted cents',
        limitations='Uncalibrated lag/unattributed allowance; later metering increases consume headroom before a new slot. Missing/ambiguous current app rows refuse settlement. Original claims remain historical ceilings, not duplicate expenses.')
