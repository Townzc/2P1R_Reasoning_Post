"""Prepared finite breadth/depth procurement state, without execution or scores.

The caller must save the exact intent before generating and retain every return.
None usability represents a censored/unknown attempt; it never becomes a success
or a confirmed wrong answer. A lost return cannot be silently resampled.
"""
from dataclasses import dataclass, field


@dataclass
class Policy:
    ordered_ids: list
    target_usable: int
    max_attempts: int = 8
    slots: int = 16
    cursor: int = field(default=0, init=False)
    records: dict = field(default_factory=dict, init=False)
    active: list = field(default_factory=list, init=False)
    pending: dict | None = field(default=None, init=False)
    attempted_batches: set = field(default_factory=set, init=False)

    def __post_init__(self):
        if (not self.ordered_ids or len(set(self.ordered_ids)) != len(self.ordered_ids)
                or any(not isinstance(x, str) or not x for x in self.ordered_ids)):
            raise ValueError('A finite unique preselected pool is required')
        if self.target_usable not in (1, 4) or self.max_attempts != 8 or self.slots != 16:
            raise ValueError('Policy differs from the prepared four-cell design')

    def propose(self, new_count=None):
        if self.pending is not None:
            raise ValueError('Unresolved batch; cannot propose more work')
        room = min(self.slots-len(self.active), len(self.ordered_ids)-self.cursor)
        if new_count is None: new_count = room
        if type(new_count) is not int or not 0 <= new_count <= room:
            raise ValueError('Invalid number of new purchases')
        new_ids = self.ordered_ids[self.cursor:self.cursor+new_count]
        items = [dict(problem_id=p, attempt=len(self.records.get(p, []))+1)
                 for p in self.active+new_ids]
        return dict(cursor=self.cursor, new_problem_ids=new_ids, items=items)

    def begin(self, batch_id, proposal):
        if self.pending is not None or batch_id in self.attempted_batches:
            raise ValueError('Batch already attempted or unresolved')
        if proposal != self.propose(len(proposal['new_problem_ids'])) or not proposal['items']:
            raise ValueError('Proposal changed or has no actual requests')
        for pid in proposal['new_problem_ids']:
            self.records[pid] = []
            self.active.append(pid)
        self.cursor += len(proposal['new_problem_ids'])
        self.pending = dict(batch_id=batch_id, **proposal)
        self.attempted_batches.add(batch_id)

    def complete(self, batch_id, outcomes):
        if self.pending is None or self.pending['batch_id'] != batch_id:
            raise ValueError('Unknown batch')
        expected = [(r['problem_id'], r['attempt']) for r in self.pending['items']]
        if [(r['problem_id'], r['attempt']) for r in outcomes] != expected:
            raise ValueError('Backend roster or ordering differs')
        if any(r['usable'] is not None and type(r['usable']) is not bool for r in outcomes):
            raise ValueError('Usability must preserve true, false, or unknown')
        for row in outcomes:
            self.records[row['problem_id']].append(dict(row))
        self.active = [p for p in self.active if len(self.records[p]) < self.max_attempts
                       and sum(r['usable'] is True for r in self.records[p]) < self.target_usable]
        self.pending = None

    def summary(self):
        return dict(acquired_problems=self.cursor, attempted_candidates=sum(len(v) for v in self.records.values()),
            usable=sum(r['usable'] is True for v in self.records.values() for r in v),
            unknown=sum(r['usable'] is None for v in self.records.values() for r in v),
            zero_usable_parents=sum(not any(r['usable'] is True for r in v) for v in self.records.values()),
            unresolved_batch=self.pending is not None, pool_exhausted=self.cursor == len(self.ordered_ids),
            active_parents=len(self.active), target_usable=self.target_usable)
