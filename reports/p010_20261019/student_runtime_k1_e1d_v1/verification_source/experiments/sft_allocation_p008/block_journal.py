"""Unstarted P008 students only: immutable 16-update remote work reservations.

Every actual update retains a local intent/done record, fsynced by dump().
The remote block intent conservatively reserves ALL sixteen updates before any
compute. A partial/unknown block is never replayable. Fencing is observed at
both block boundaries, not inside the block; the local deadline is checked on
every update and the independent process hard timer remains authoritative.
"""
from copy import deepcopy
import time
from experiments.sft_allocation_midpoint.common import dump, digest
from experiments.sft_allocation_midpoint.runtime import Journal

POLICY = dict(schema='p008_training_block_journal_v1', block_updates=16,
              remote_checks='block_start_and_end', local_deadline='every_update',
              evaluation_journal='unchanged_per_batch', automatic_replay=False,
              maximum_unacknowledged_reserved_updates=16)


class BlockTrainingJournal(Journal):
    def __init__(self, *args, deadline, expected_updates, **kwargs):
        super().__init__(*args, **kwargs)
        if expected_updates not in (0, 256, 1024, 2048):
            raise ValueError('Unregistered training horizon')
        self.deadline = deadline
        self.expected_updates = expected_updates
        self.records = None
        self.cursor = 0
        self.active = None
        self.pending = None
        self.failed = False
        self.metrics = dict(policy=deepcopy(POLICY), completed_blocks=0,
                            completed_local_updates=0, configured_updates=0,
                            block_boundary_seconds=0.0, local_step_write_seconds=0.0,
                            block_boundary_calls=0, maximum_block_boundary_seconds=0.0)

    def _boundary(self, operation):
        tick = time.monotonic()
        try:
            return operation()
        finally:
            elapsed = time.monotonic()-tick
            self.metrics['block_boundary_seconds'] += elapsed
            self.metrics['block_boundary_calls'] += 1
            self.metrics['maximum_block_boundary_seconds'] = max(
                self.metrics['maximum_block_boundary_seconds'], elapsed)

    def _step_dump(self, path, record):
        tick = time.monotonic()
        try:
            dump(path, record)
        finally:
            self.metrics['local_step_write_seconds'] += time.monotonic()-tick

    def configure_training(self, encoded, schedule, rates):
        if self.failed or self.records is not None or self.cursor or self.active:
            raise RuntimeError('Training journal cannot be reconfigured')
        if len(schedule) != self.expected_updates or not schedule or len(rates) != len(schedule):
            raise ValueError('Exact full training plan required')
        self.records = [dict(step=i+1, indices=list(indices), lr=rates[i],
                             supervised_tokens=sum(encoded[j]['n_supervised'] for j in indices),
                             processed_tokens=sum(encoded[j]['n_processed'] for j in indices))
                        for i, indices in enumerate(schedule)]
        self.metrics['configured_updates'] = len(schedule)
        dump(self.out/'training_journal_policy.json', POLICY)

    def _usable(self):
        if self.failed:
            raise RuntimeError('Failed journal cannot be reused')
        self.deadline()

    def begin(self, name, record):
        try:
            self._usable()
            if not name.startswith('update_'):
                if self.pending or self.active or self.cursor != self.expected_updates:
                    raise RuntimeError('Evaluation before all training blocks close')
                return super().begin(name, record)
            if (self.records is None or self.pending is not None or
                    name != f'update_{self.cursor+1:04d}' or
                    self.cursor >= len(self.records) or record != self.records[self.cursor]):
                raise ValueError('Foreign, repeated or out-of-order training update')
            if self.active is None:
                if self.cursor % 16:
                    raise RuntimeError('Missing active block')
                group = deepcopy(self.records[self.cursor:self.cursor+16])
                block = f'training_block_{group[0]["step"]:04d}_{group[-1]["step"]:04d}'
                intent = dict(policy=POLICY['schema'], first_step=group[0]['step'],
                              last_step=group[-1]['step'], updates=group,
                              updates_sha256=digest(group))
                # Atomic reservation precedes every local per-step intent and
                # optimizer update. Never reuse a failed/unacknowledged block.
                self._boundary(lambda: Journal.begin(self, block, intent))
                self.active = dict(name=block, intent=intent, completions=[])
            self.deadline()  # also after the full remote read/write boundary
            self._step_dump(self.out/'intents'/(name+'.json'), record)
            self.pending = (name, deepcopy(record))
        except BaseException:
            self.failed = True
            raise

    def end(self, name, record):
        try:
            self._usable()
            if not name.startswith('update_'):
                if self.pending or self.active or self.cursor != self.expected_updates:
                    raise RuntimeError('Evaluation completion during incomplete training')
                return super().end(name, record)
            if (self.pending is None or self.pending[0] != name or
                    any(record.get(k) != v for k, v in self.pending[1].items())):
                raise ValueError('Completion does not match its exact intent')
            self._step_dump(self.out/'completed'/(name+'.json'), record)
            self.active['completions'].append(deepcopy(record))
            self.cursor += 1
            self.pending = None
            self.metrics['completed_local_updates'] = self.cursor
            if self.cursor == self.active['intent']['last_step']:
                # A fence arriving during a block prevents its acknowledgment
                # and all later work, while preserving its completed local rows.
                summary = dict(policy=POLICY['schema'],
                               first_step=self.active['intent']['first_step'],
                               last_step=self.cursor, count=len(self.active['completions']),
                               intent_sha256=digest(self.active['intent']),
                               completions_sha256=digest(self.active['completions']),
                               cumulative_targets=record['cumulative_targets'],
                               cumulative_processed=record['cumulative_processed'])
                def finish():
                    self.check()
                    self.deadline()
                    Journal.end(self, self.active['name'], summary)
                self._boundary(finish)
                # Checkpoints and the terminal envelope commit unchanged. A
                # block-local record is not claimed durable independently of
                # its remote acknowledgment + subsequently verified manifest.
                self.active = None
                self.metrics['completed_blocks'] += 1
        except BaseException:
            self.failed = True
            raise

    def assert_training_complete(self):
        self._usable()
        if self.pending or self.active or self.cursor != self.expected_updates:
            raise RuntimeError('Incomplete training journal')


def verify_training_blocks(intents, done, ledger, prefix, updates):
    """Independent reconstruction from saved per-step records, no model work.

The numerical oracle separately checks every step against the frozen token/LR
plan. This verifies the remote acknowledgment grouping and rejects extra keys.
"""
    step_names = {f'update_{i:04d}' for i in range(1, updates+1)}
    if {x for x in intents if x.startswith('update_')} != step_names:
        raise ValueError('Missing/extra per-update intent')
    if {x for x in done if x.startswith('update_')} != step_names:
        raise ValueError('Missing/extra per-update completion')
    expected_blocks = set()
    for first in range(1, updates+1, 16):
        last = min(first+15, updates)
        name = f'training_block_{first:04d}_{last:04d}'
        expected_blocks.add(name)
        group = [intents[f'update_{i:04d}'] for i in range(first, last+1)]
        completed = [done[f'update_{i:04d}'] for i in range(first, last+1)]
        wanted = dict(policy=POLICY['schema'], first_step=first, last_step=last,
                      updates=group, updates_sha256=digest(group))
        if intents.get(name) != wanted:
            raise ValueError('Block reservation differs from saved step intents')
        ack = dict(policy=POLICY['schema'], first_step=first, last_step=last,
                   count=len(group), intent_sha256=digest(wanted),
                   completions_sha256=digest(completed),
                   cumulative_targets=completed[-1]['cumulative_targets'],
                   cumulative_processed=completed[-1]['cumulative_processed'])
        if done.get(name) != ack:
            raise ValueError('Block completion differs from saved step records')
    for records in (intents, done):
        if {x for x in records if x.startswith('training_block_')} != expected_blocks:
            raise ValueError('Unexpected/missing block')
    for kind, records in (('unit', intents), ('done', done)):
        remote = {k[len(prefix+kind+'/'):]: v for k, v in ledger.items()
                  if k.startswith(prefix+kind+'/')}
        wanted = {k: v for k, v in records.items() if k not in step_names}
        if remote != wanted:
            raise ValueError('Remote block/evaluation roster differs')
    return expected_blocks
