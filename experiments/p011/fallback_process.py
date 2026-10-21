"""Original B training in a once-only child with complete-block forecasting."""
import os
import time
import traceback
from pathlib import Path
from experiments.p010.common import dump, read, verify
from experiments.p011.fallback_numeric import forecast
from experiments.sft_allocation_p008.block_journal import BlockTrainingJournal


class CompleteBlockJournal(BlockTrainingJournal):
    def __init__(self, *args, policy, clock=time.time, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy = policy
        self.clock = clock
        self.times = []
        self.tick = None

    def begin(self, name, record):
        if name.startswith('update_') and self.cursor % 16 == 0 and self.active is None:
            if self.tick is not None:
                raise ValueError('Previous complete block interval is open')
            self.tick = self.clock()
            value = forecast(self.policy, (1024-self.cursor)//16, 10, self.times, [], self.tick)
            dump(self.out/'forecasts'/f'{self.cursor:04d}.json', value)
            self.commit()
        super().begin(name, record)

    def end(self, name, record):
        super().end(name, record)
        if name.startswith('update_') and self.cursor % 16 == 0 and self.active is None:
            # Includes both Volume commits and all block begin/done operations.
            # The eventual complete list is written after training; that closing
            # write, terminal checkpoint and merge remain future allowance work.
            self.commit()
            elapsed = self.clock()-self.tick
            if elapsed <= 0:
                raise ValueError('Positive complete-block duration required')
            self.times.append(elapsed)
            self.tick = None


def child(conn, inputs, out, model, identity, claim, policy, stop):
    try:
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
            raise ValueError('Original deterministic environment required')
        import modal
        import torch
        from experiments.p011.fallback_training import train_and_merge
        torch.set_num_threads(4)
        volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        store = modal.Dict.from_name('p011-once-20261020', create_if_missing=False)
        volume.reload()
        verify(model['remote_path'], model['files'])
        key = 'fallback/student/'+identity['run_id']

        def deadline():
            if time.time() >= stop-30:
                raise TimeoutError('Original B student worker deadline')

        def check():
            deadline()
            if store.get(key+'/claim') != claim:
                raise RuntimeError('Original shared B claim differs')

        inputs = Path(inputs)
        rows, encoded, plan = [read(inputs/(n+'.json')) for n in ('rows', 'encoded', 'plan')]
        journal = CompleteBlockJournal(Path(out), key, store, volume.commit, check,
            deadline=deadline, expected_updates=1024, policy=policy)
        value = train_and_merge(model['remote_path'], rows, encoded, plan,
            Path(out), Path(out)/'merged', journal, identity)
        if len(journal.times) != 64 or journal.tick is not None:
            raise ValueError('All64 complete block times required')
        dump(Path(out)/'TRAINING_PROCESS_RESULT.json', dict(result=value,
            pid=os.getpid(), block_seconds=journal.times,
            complete_block_commits_and_remote_ack_included=True,
            checkpoint_merge_and_final_proof_outside_cycles=True))
        volume.commit()
        conn.send(('complete', value, journal.times))
    except BaseException:
        conn.send(('error', traceback.format_exc(), []))
        raise
    finally:
        conn.close()
