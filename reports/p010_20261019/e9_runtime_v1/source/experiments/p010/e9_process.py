"""Original training in a subprocess, with per-block deadline/cost forecasts."""
import os
import time
import traceback
from pathlib import Path
from experiments.p010.common import dump, read, verify
from experiments.p010.e9_contract import forecast
from experiments.sft_allocation_p008.block_journal import BlockTrainingJournal


class MeasuredJournal(BlockTrainingJournal):
    def __init__(self, *args, start, timing, prior, **kwargs):
        super().__init__(*args, **kwargs)
        self.start = start
        self.timing = timing
        self.prior = prior
        self.times = []
        self.tick = None

    def begin(self, name, record):
        if name.startswith('update_') and self.cursor % 16 == 0 and self.active is None:
            self.tick = time.time()
            f = forecast(time.time()-self.start, (1024-self.cursor)//16, 2,
                self.timing['training_seconds']+self.times,
                self.timing['endpoint_seconds'], self.prior)
            dump(self.out/'forecasts'/f'{self.cursor:04d}.json', f)
            self.commit()
        super().begin(name, record)

    def end(self, name, record):
        super().end(name, record)
        if name.startswith('update_') and self.cursor % 16 == 0 and self.active is None:
            self.commit()
            seconds = time.time()-self.tick
            self.times.append(seconds)
            dump(self.out/'timings'/f'{self.cursor:04d}.json', dict(seconds=seconds, updates=16))
            self.commit()


def child(conn, inputs, out, model, identity, claim, start, stop, timing, prior):
    try:
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
            raise ValueError('Frozen deterministic environment differs')
        import modal
        import torch
        from experiments.p010.e9_training import train_and_merge
        torch.set_num_threads(4)
        volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        store = modal.Dict.from_name('p010-once-20261019', create_if_missing=False)
        volume.reload()
        verify(model['remote_path'], model['files'])
        key = 'e9/'+identity['run_id']

        def deadline():
            if time.time() > stop-30:
                raise TimeoutError('Original 4500-second student deadline')

        def check():
            deadline()
            if store.get(key+'/claim') != claim:
                raise RuntimeError('Original once-only claim differs')

        inputs = Path(inputs)
        rows, encoded, plan = [read(inputs/(name+'.json')) for name in ('rows', 'encoded', 'plan')]
        journal = MeasuredJournal(Path(out), key, store, volume.commit, check,
            deadline=deadline, expected_updates=1024, start=start, timing=timing, prior=prior)
        result = train_and_merge(model['remote_path'], rows, encoded, plan,
            Path(out), Path(out)/'merged', journal, identity)
        dump(Path(out)/'TRAINING_PROCESS_RESULT.json', dict(result=result,
            pid=os.getpid(), block_seconds=journal.times))
        volume.commit()
        conn.send(('complete', result, journal.times))
    except BaseException:
        conn.send(('error', traceback.format_exc(), []))
        raise
    finally:
        conn.close()
