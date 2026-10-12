"""Prepared P007B active-time wallet; no provider or model calls.

Integer nanodollars and monotonic nanoseconds avoid optimistic float rounding.
The wallet includes all elapsed active-policy time, including between batches.
Problem prices are explicit scenarios, not measured human acquisition prices.
Reservation permits one bounded batch; a caller must enforce its deadline.
This module does not by itself admit or dispatch a scientific experiment.
"""
from dataclasses import dataclass, field

NS_PER_HOUR = 3_600_000_000_000


def cost_ns(elapsed_ns, hourly_nanodollars):
    if (type(elapsed_ns) is not int or elapsed_ns < 0 or
            type(hourly_nanodollars) is not int or hourly_nanodollars <= 0):
        raise ValueError('Invalid measured interval or rate')
    return (elapsed_ns * hourly_nanodollars + NS_PER_HOUR - 1) // NS_PER_HOUR


@dataclass
class Wallet:
    cap_nanodollars: int
    hourly_nanodollars: int
    problem_nanodollars: int
    start_ns: int
    acquired: set = field(default_factory=set, init=False)
    attempted_batches: set = field(default_factory=set, init=False)
    pending: dict | None = field(default=None, init=False)
    last_ns: int = field(init=False)

    def __post_init__(self):
        if any(type(x) is not int for x in (self.cap_nanodollars,
                self.hourly_nanodollars, self.problem_nanodollars, self.start_ns)):
            raise ValueError('Integer currency and clock required')
        if min(self.cap_nanodollars, self.hourly_nanodollars) <= 0 or min(
                self.problem_nanodollars, self.start_ns) < 0:
            raise ValueError('Invalid wallet')
        self.last_ns = self.start_ns

    def spent(self, now_ns):
        if type(now_ns) is not int or now_ns < self.last_ns:
            raise ValueError('Nonmonotonic clock')
        self.last_ns = now_ns
        return len(self.acquired) * self.problem_nanodollars + cost_ns(
            now_ns - self.start_ns, self.hourly_nanodollars)

    def admit(self, batch_id, new_problem_ids, now_ns, max_action_ns):
        if self.pending is not None:
            raise ValueError('Unresolved batch; never replay ambiguous work')
        if not isinstance(batch_id, str) or not batch_id or batch_id in self.attempted_batches:
            raise ValueError('Missing or previously attempted batch')
        if type(max_action_ns) is not int or max_action_ns <= 0:
            raise ValueError('Finite positive action bound required')
        ids = list(new_problem_ids)
        if (any(not isinstance(x, str) or not x for x in ids) or
                len(set(ids)) != len(ids) or set(ids) & self.acquired):
            raise ValueError('Problem purchase would duplicate a charge')
        spent = self.spent(now_ns)
        purchase = len(ids) * self.problem_nanodollars
        maximum = cost_ns(max_action_ns, self.hourly_nanodollars)
        if spent + purchase + maximum > self.cap_nanodollars:
            return None  # No problem is purchased and no candidate is attempted.
        self.acquired.update(ids)
        self.attempted_batches.add(batch_id)
        self.pending = dict(batch_id=batch_id, new_problem_ids=ids,
            start_ns=now_ns, deadline_ns=now_ns + max_action_ns,
            purchase_nanodollars=purchase, maximum_action_nanodollars=maximum,
            previously_spent_nanodollars=spent)
        return dict(self.pending)

    def settle(self, batch_id, finished_ns):
        if self.pending is None or self.pending['batch_id'] != batch_id:
            raise ValueError('Missing or foreign batch settlement')
        spent = self.spent(finished_ns)
        if finished_ns > self.pending['deadline_ns'] or spent > self.cap_nanodollars:
            # Keep pending intent for reconciliation; do not forgive overrun.
            raise ValueError('Measured action exceeded admitted bound')
        record = dict(self.pending, finished_ns=finished_ns,
            cumulative_spent_nanodollars=spent,
            remaining_nanodollars=self.cap_nanodollars-spent)
        self.pending = None
        return record
