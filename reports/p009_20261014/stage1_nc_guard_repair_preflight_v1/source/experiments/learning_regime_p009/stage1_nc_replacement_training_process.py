# Distinct owner-approved physical replacement; original sources retained unchanged.
"""Prepared isolated NC training process. No launch route, retry or controller.

The future reviewed parent must claim the exact slot, bind inputs/model/timings,
own a whole-worker hard timer and join this process before constructing vLLM.
"""
import os
from pathlib import Path
import time
import traceback

from experiments.sft_allocation_midpoint.common import read, dump, digest, verify
from experiments.sft_allocation_p008.block_journal import BlockTrainingJournal
from experiments.learning_regime_p009.stage1_nc_replacement_contract import forecast, slot


class MeasuredNCJournal(BlockTrainingJournal):
    """Preserve original per-step/block semantics with complete timing checks."""
    def __init__(self, *args, start, stop, prior, stage_remaining_before_cents, **kwargs):
        super().__init__(*args, **kwargs)
        self.worker_start = start; self.worker_stop = stop; self.prior = prior
        self.stage_remaining_before_cents = stage_remaining_before_cents
        self.new_full_blocks = []; self.block_started = None

    def begin(self, name, record):
        if name.startswith('update_') and self.cursor % 16 == 0 and self.active is None:
            self.block_started = time.time()
            f = forecast(time.time()-self.worker_start, (1024-self.cursor)//16, 6,
                self.prior['training_block_seconds']+self.new_full_blocks,
                self.prior['endpoint_batch_seconds'], self.stage_remaining_before_cents)
            dump(self.out/'training_forecasts'/f'{self.cursor//16:03d}.json', f); self.commit()
            if not f['admitted']:
                raise TimeoutError('Measured NC training remainder does not fit its exact cap/budget')
        return super().begin(name, record)

    def end(self, name, record):
        super().end(name, record)
        if name.startswith('update_') and self.cursor % 16 == 0 and self.active is None:
            if self.block_started is None:
                raise ValueError('Missing original complete block start')
            # Commit the complete original block after its immutable remote ACK.
            # Forecast/guard/local fsync/remote ACK/commit are in this interval.
            self.commit()
            elapsed = time.time()-self.block_started
            dump(self.out/'training_timings'/f'{self.cursor//16-1:03d}.json',
                dict(first_step=self.cursor-15, last_step=self.cursor,
                     through_original_block_commit_seconds=elapsed,
                     final_timing_write_in_complete_vector=True))
            self.commit(); self.new_full_blocks.append(time.time()-self.block_started)
            self.block_started = None


def child(connection, paths, plan, claim, identity, prior, stage_remaining_before_cents,
          worker_start, worker_stop):
    """Train once, save the full1024 state, merge once; no endpoint evaluation."""
    checker = None
    out = Path(paths['out'])
    try:
        # Assert before importing torch/initializing CUDA; never silently choose
        # a different deterministic workspace after a runtime has started.
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
            raise ValueError('Future image must bind original deterministic cuBLAS workspace')
        import torch
        torch.set_num_threads(4)
        if (not torch.cuda.is_available() or torch.cuda.device_count() != 1
                or 'H100' not in torch.cuda.get_device_name(0)
                or torch.cuda.get_device_properties(0).total_memory < 75*1024**3):
            raise ValueError('Exactly one real H100-80GB required')
        if paths['base'] != paths['tokenizer']:
            raise ValueError('Original base and tokenizer must use the same verified directory')
        verify(paths['base'], identity['base_files'])
        verify(paths['inputs'], identity['input_files'])
        config = identity['config']; run = identity['run_id']; recipe = slot(run)
        if any(config.get(k) != recipe[k] for k in ('setting', 'seed', 'n', 'updates', 'targets')):
            raise ValueError('Only the exact two NC recipes may enter this process')
        inputs = Path(paths['inputs']); stem = f'nc17_n{recipe["n"]}'
        rows, encoded, training_plan, saved_config = [read(inputs/(stem+'_'+n+'.json'))
                                                    for n in ('rows', 'encoded', 'plan', 'config')]
        if config != saved_config or not worker_start < time.time() < worker_stop-30:
            raise ValueError('Original config or whole-worker window differs')
        import modal
        from experiments.sft_allocation_midpoint.guard import RunGuard
        from experiments.sft_allocation_p008.parallel_guard import ParallelActiveCheck
        from experiments.learning_regime_p009.stage1_training_core import train_and_merge
        volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        volume.reload()
        store = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
        guard = RunGuard(store, plan)
        checker = ParallelActiveCheck(guard, readers=2)
        def deadline():
            if time.time() >= worker_stop-30:
                raise TimeoutError('Original whole-worker NC deadline; no continuation')
        def check():
            deadline()
            checker.check_active(claim, spent_cents=recipe['reserved_cents'])
            deadline()
        check()
        journal = MeasuredNCJournal(out, guard.prefix+run, store, volume.commit, check,
            deadline=deadline, expected_updates=1024, start=worker_start, stop=worker_stop,
            prior=prior, stage_remaining_before_cents=stage_remaining_before_cents)
        dump(out/'TRAINING_PROCESS.json', dict(pid=os.getpid(), threads=torch.get_num_threads(),
            CUBLAS_WORKSPACE_CONFIG=os.environ['CUBLAS_WORKSPACE_CONFIG'],
            gpu=torch.cuda.get_device_name(0), tokenizer_is_verified_base=True,
            automatic_retry=False)); volume.commit()
        result = train_and_merge(paths['base'], rows, encoded, training_plan, out,
                                 paths['merged'], journal, identity)
        if len(journal.new_full_blocks) != 64:
            raise ValueError('All64 original full blocks must have a measured completion')
        result.update(full_block_intervals_seconds=journal.new_full_blocks,
                      identity_sha256=digest(identity), new_generations=0)
        dump(out/'TRAINING_CHILD_RESULT.json', result)
        dump(out/'block_journal_metrics.json', journal.metrics)
        dump(out/'training_guard_metrics.json', checker.metrics); volume.commit()
        connection.send(('trained', result))
    except BaseException:
        connection.send(('error', traceback.format_exc()))
        raise
    finally:
        if checker is not None:checker.close()
        connection.close()
