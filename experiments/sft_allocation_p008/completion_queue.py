"""Owner-authorized finite student successor, without the old 19PDT cutoff.

The original campaign and failed teacher parent remain immutable. Only the
never-attempted student/base/audit slots move, with identical reservations.
Six days is the existing seven-day Dict retention guard's technical envelope,
not a new midpoint deadline or permission for any extra run/retry/spending.
"""
import math
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_midpoint.guard import RunGuard
from .contract import run_roster

ORIGINAL_CAMPAIGN = 'p008-main-20261013-r1'
ORIGINAL_PLAN_SHA256 = 'abd0935222aac96713b9ec4ac18c406d5a7caee39e477f1bd5b07b936c19844e'
CAMPAIGN = 'p008-students-completion-20261013-r1'
LEDGER_LIFETIME_SECONDS = 6 * 24 * 3600
TRANSFER_KEY = 'midpoint/' + ORIGINAL_CAMPAIGN + '/finite_student_successor'


def student_roster():
    return {x['run_id'] for x in run_roster(8, False, 2)} | {'base'}


def validate_owner(owner):
    if (owner.get('authority') != 'Direct human reply in this chat'
            or owner.get('answer') != '学生计算截止延后、跑完为止'
            or owner.get('student_queue_until_complete') is not True
            or owner.get('per_worker_caps_unchanged') is not True
            or owner.get('d2_continuation_deadline_unchanged') is not True
            or owner.get('maximum_student_H100_workers') != 8
            or owner.get('stage_cap_usd') != 250
            or owner.get('hard_reservation_usd') != 249.68
            or owner.get('project_ceiling_usd') != 450
            or owner.get('protected_usd') != 50
            or owner.get('material_freeze_utc') != '2026-10-14T04:00:00Z'):
        raise ValueError('Exact direct finite-completion authority required')


def make_plan(original, owner, created_epoch):
    validate_owner(owner)
    if (digest(original) != ORIGINAL_PLAN_SHA256
            or original['campaign_id'] != ORIGINAL_CAMPAIGN
            or isinstance(created_epoch, bool)
            or not isinstance(created_epoch, (int, float))
            or not math.isfinite(created_epoch)):
        raise ValueError('Frozen original and actual finite creation clock required')
    names = student_roster() | {'audit'}
    slots = {n: original['slots'][n] for n in sorted(names)}
    total = sum(x['reserved_cents'] for x in slots.values())
    plan = dict(campaign_id=CAMPAIGN, created_epoch=created_epoch,
                deadline_epoch=created_epoch + LEDGER_LIFETIME_SECONDS,
                slots=slots, total_cap_cents=total, stage_caps_cents={'main': total})
    RunGuard({}, plan)
    return plan


def validate_plan(plan, original, owner):
    if plan != make_plan(original, owner, plan['created_epoch']):
        raise ValueError('Only unchanged finite slots/reservations may move')
    return plan


def transfer_record(plan, original, owner):
    validate_plan(plan, original, owner)
    return dict(schema='p008_finite_student_successor_v1', original_campaign=ORIGINAL_CAMPAIGN,
                original_plan_sha256=digest(original), successor_campaign=CAMPAIGN,
                successor_plan_sha256=digest(plan), owner_sha256=digest(owner),
                retired_original_slots=sorted(plan['slots']),
                transferred_reservation_cents=sum(x['reserved_cents'] for x in plan['slots'].values()),
                total_p008_reservation_cents=24968, additional_budget_cents=0,
                original_teacher_deadlines_unchanged=True, automatic_retry=False)


def assert_original_absent(records):
    """Full parent-ledger enumeration before the one-time handoff.

    Check the original per-run unit prefixes too, not just claims/terminals.
    The exact transfer key is allowed only when it matches the caller's record.
    """
    prefix = 'midpoint/' + ORIGINAL_CAMPAIGN + '/'
    names = student_roster() | {'audit'}
    for key in records:
        if not key.startswith(prefix):
            continue
        tail = key[len(prefix):].split('/')
        if tail[0] in names or (len(tail) > 1 and tail[1] in names):
            raise ValueError('Original student slot has existing/uncertain work; no transfer')


def require_handoff(store, plan, original, owner, run):
    expected = transfer_record(plan, original, owner)
    if run not in plan['slots'] or store.get(TRANSFER_KEY) != expected:
        raise ValueError('Actual immutable finite-slot handoff missing')
    for kind in ('claim', 'intent', 'terminal'):
        if store.get('midpoint/' + ORIGINAL_CAMPAIGN + '/' + kind + '/' + run) is not None:
            raise ValueError('Original slot attempted; successor must stop without replay')
    return expected
