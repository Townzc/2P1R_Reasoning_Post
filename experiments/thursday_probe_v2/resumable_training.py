"""Canonical, bounded training segments using the frozen v2 optimizer recipe.

Recovery is the commit point for scientific dose. Append-only attempt journals
retain completed physical work even when a crash leaves it beyond that point.
Only this module's obsolete rolling recovery files are reclaimed.
"""
import json
import math
import os
from pathlib import Path
import random
import time
import uuid

from experiments.thursday_probe.common import digest, stamp
from experiments.thursday_probe.lora import parameter_digest, save_adapter
from experiments.thursday_probe_v2.training import adapter_state, cpu_tree, new_optimizer
from src.relation_experiment import accumulate_gradients
from src.sft_data import sha256_file


SCHEMA = 1
SOFT_RESERVE_SECONDS = 30


def _fsync_dir(path):
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _json(path, record, *, replace=False):
    path = Path(path)
    if path.exists() and not replace:
        raise FileExistsError(path)
    temporary = path.with_name(path.name + '.pending_' + uuid.uuid4().hex)
    with temporary.open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    _fsync_dir(path.parent)


def capture_rng(device):
    import numpy as np
    import torch
    numpy = np.random.get_state()
    # Plain lists avoid unsafe numpy reconstruction with torch weights_only.
    return dict(python=random.getstate(), numpy=dict(kind=numpy[0],
        keys=numpy[1].tolist(), position=numpy[2], has_gauss=numpy[3], cached_gaussian=numpy[4]),
        torch=torch.get_rng_state().clone(),
        cuda=[x.clone() for x in torch.cuda.get_rng_state_all()] if str(device).startswith('cuda') else [])


def restore_rng(state, device):
    import numpy as np
    import torch
    random.setstate(state['python'])
    numpy = state['numpy']
    np.random.set_state((numpy['kind'], np.asarray(numpy['keys'], dtype=np.uint32),
        numpy['position'], numpy['has_gauss'], numpy['cached_gaussian']))
    torch.set_rng_state(state['torch'])
    if str(device).startswith('cuda'):
        if len(state['cuda']) != torch.cuda.device_count():
            raise ValueError('Recovery CUDA device/RNG count differs')
        torch.cuda.set_rng_state_all(state['cuda'])


def _checkpoint_identity(path):
    path = Path(path)
    record = json.loads((path / 'checkpoint_identity.json').read_text())
    for name, expected in record['files_sha256'].items():
        if Path(name).name != name or sha256_file(path / name) != expected:
            raise ValueError('Scientific checkpoint bytes changed')
    return record


def _checkpoint(model, out, step):
    from safetensors.torch import load_file
    path = out / f'checkpoint_{step}'
    expected = parameter_digest(model, True)
    if path.exists():
        record = _checkpoint_identity(path)
    else:
        temporary = out / f'.checkpoint_{step}.pending_{uuid.uuid4().hex}'
        record = save_adapter(model, temporary)
        _checkpoint_identity(temporary)
        for file in temporary.iterdir():
            if file.is_file():
                with file.open('rb') as stream:
                    os.fsync(stream.fileno())
        _fsync_dir(temporary)
        temporary.rename(path)
        _fsync_dir(out)
    if record['parameter_digest'] != expected:
        raise ValueError('Existing checkpoint differs from this absolute step')
    if not _same_tree(load_file(str(path / 'adapter_model.safetensors')), adapter_state(model)):
        raise ValueError('Scientific checkpoint tensors differ from this absolute step')
    return record


def _verify_history(out, history):
    journals = {}
    for expected_step, row in enumerate(history, 1):
        if row['step'] != expected_step:
            raise ValueError('Committed scientific history is not contiguous')
        name = row['segment_file']
        if Path(name).name != name or not name.startswith('segment_'):
            raise ValueError('Invalid training history identity')
        if name not in journals:
            # A crashed final line is retained as evidence, never parsed as work.
            lines = (out / 'segments' / name).read_bytes().splitlines()
            journals[name] = lines
        line = row['segment_line']
        if type(line) is not int or line < 0 or line >= len(journals[name]):
            raise ValueError('Committed training journal is incomplete')
        if json.loads(journals[name][line]) != row:
            raise ValueError('Committed training journal changed')


def _discarded_history(out, history):
    committed = {(r['segment_file'], r['segment_line']) for r in history}
    discarded = []
    for path in sorted((out / 'segments').glob('segment_*.jsonl')):
        for line, raw in enumerate(path.read_bytes().splitlines()):
            if (path.name, line) in committed:
                continue
            try:
                row = json.loads(raw)
                discarded.append(dict(segment_file=path.name, segment_line=line,
                    step=row.get('step'), seconds=row.get('seconds'), reason='beyond_committed_recovery'))
            except (ValueError, TypeError):
                discarded.append(dict(segment_file=path.name, segment_line=line,
                    step=None, seconds=None, reason='interrupted_journal_line'))
    return discarded


def _read_recovery(out, fingerprint):
    import torch
    folder = out / 'recovery'
    pointer = json.loads((folder / 'latest.json').read_text())
    name = pointer['file']
    if Path(name).name != name or not name.startswith('rolling_step_') or not name.endswith('.pt'):
        raise ValueError('Invalid rolling recovery path')
    path = folder / name
    if pointer['fingerprint'] != fingerprint or sha256_file(path) != pointer['sha256']:
        raise ValueError('Recovery identity/hash mismatch')
    state = torch.load(path, map_location='cpu', weights_only=True)
    if (state['schema'] != SCHEMA or state['fingerprint'] != fingerprint or digest(state['protocol']) != fingerprint or
            state['step'] != pointer['step'] or state['step'] != len(state['history'])):
        raise ValueError('Recovery step/config/history mismatch')
    _verify_history(out, state['history'])
    for step, expected in state['checkpoints'].items():
        if _checkpoint_identity(out / f'checkpoint_{step}') != expected:
            raise ValueError('Committed scientific checkpoint identity changed')
    return state


def _same_tree(left, right):
    import torch
    if isinstance(left, torch.Tensor):
        return isinstance(right, torch.Tensor) and left.dtype == right.dtype and torch.equal(left, right)
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same_tree(left[k], right[k]) for k in left)
    if isinstance(left, (tuple, list)):
        return len(left) == len(right) and all(_same_tree(a, b) for a, b in zip(left, right))
    return left == right


def _prune_recoveries(folder, keep):
    for previous in folder.glob('rolling_step_*.pt'):
        if previous.name != keep:
            previous.unlink()
    _fsync_dir(folder)


def _save_recovery(model, optimizer, out, state, device):
    import torch
    folder = out / 'recovery'
    folder.mkdir(exist_ok=True)
    record = {**state, 'schema': SCHEMA, 'adapter': adapter_state(model),
              'optimizer': cpu_tree(optimizer.state_dict()), 'rng': capture_rng(device),
              'adapter_digest': parameter_digest(model, True)}
    if any(not torch.isfinite(value).all() for value in record['adapter'].values()):
        raise FloatingPointError('Nonfinite adapter cannot replace committed recovery')
    path = folder / f"rolling_step_{state['step']:06d}_{uuid.uuid4().hex}.pt"
    with path.open('xb') as stream:
        torch.save(record, stream); stream.flush(); os.fsync(stream.fileno())
    expected_hash = sha256_file(path)
    verified = torch.load(path, map_location='cpu', weights_only=True)
    if not _same_tree(verified, record):
        raise ValueError('New recovery failed independent readback')
    _json(folder / 'latest.json', dict(file=path.name, sha256=expected_hash,
        bytes=path.stat().st_size, step=state['step'], fingerprint=state['fingerprint'],
        created_at_utc=stamp()), replace=True)
    # Read through the committed pointer before pruning only our rolling files.
    _read_recovery(out, state['fingerprint'])
    _prune_recoveries(folder, path.name)
    return record


def _load_into_model(model, optimizer, state, device):
    import torch
    from peft import get_peft_model_state_dict, set_peft_model_state_dict
    current = get_peft_model_state_dict(model)
    if (set(current) != set(state['adapter']) or any(
            current[k].shape != value.shape or current[k].dtype != value.dtype or
            not torch.isfinite(value).all() for k, value in state['adapter'].items())):
        raise ValueError('Recovery adapter capacity/dtype/finite contract differs')
    set_peft_model_state_dict(model, state['adapter'])
    if parameter_digest(model, True) != state['adapter_digest']:
        raise ValueError('Recovery adapter tensors did not restore exactly')
    optimizer.load_state_dict(state['optimizer'])
    restore_rng(state['rng'], device)


def train_segment(model, encoded, schedule, lrs, tokenizer, out, *, identity,
                  end_step, deadline, device='cuda'):
    """Advance one logical run to an absolute boundary, preserving frozen dose.

    The caller restores the registered parent only on the first invocation. Later
    invocations load this run's adapter AND optimizer/RNG, regardless of the
    caller's current adapter. No midpoint evaluation runs inside training.
    """
    import numpy as np
    import torch
    started = time.monotonic()
    out = Path(out)
    total = len(schedule)
    if (not total or total != len(lrs) or any(not math.isfinite(x) or x <= 0 for x in lrs) or
            type(end_step) is not int or not 0 <= end_step <= total):
        raise ValueError('Invalid frozen dose, LR vector, or absolute segment boundary')
    if deadline is not None and not math.isfinite(deadline):
        raise ValueError('A finite deadline is required when specified')
    if any(not indices or any(type(i) is not int or not 0 <= i < len(encoded) for i in indices)
           for indices in schedule):
        raise ValueError('Invalid frozen training schedule')
    if str(device).startswith('cuda') and (total not in (32, 256) or any(len(x) != 16 for x in schedule)):
        raise ValueError('Production training requires registered 32/256 updates and effective batch16')
    if any(p.requires_grad != ('lora_' in n) or p.dtype != torch.float32 for n, p in model.named_parameters()):
        raise ValueError('Frozen FP32 base and LoRA-only trainable scope required')
    protocol = dict(identity=identity, identity_sha256=digest(identity), schedule_sha256=digest(schedule),
        lr_vector_sha256=digest(lrs), encoded_rows_sha256=digest([digest(r) for r in encoded]),
        total_updates=total, microbatch=1, clip=1., optimizer='AdamW(.9,.999,1e-8,0)',
        training_seed=17, checkpoint_steps=[0, 32] if total == 32 else
            sorted({0, total} | {s for s in (64, 128, 256) if s <= total}))
    fingerprint = digest(protocol)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'segments').mkdir(exist_ok=True)
    initial_path = out / 'training_identity.json'
    optimizer = new_optimizer(model, lrs[0])
    pointer = out / 'recovery' / 'latest.json'
    if initial_path.exists():
        initial = json.loads(initial_path.read_text())
        if initial['fingerprint'] != fingerprint or initial['protocol'] != protocol:
            raise ValueError('Canonical logical run identity changed')
    else:
        if pointer.exists():
            raise ValueError('Recovery exists without immutable logical run identity')
        initial = dict(fingerprint=fingerprint, protocol=protocol,
            initial_adapter=parameter_digest(model, True), created_at_utc=stamp())
        _json(initial_path, initial)
    if pointer.exists():
        state = _read_recovery(out, fingerprint)
        if not 0 <= state['step'] <= total or state['initial_adapter'] != initial['initial_adapter']:
            raise ValueError('Recovery absolute cursor/parent mismatch')
        _load_into_model(model, optimizer, state, device)
        _prune_recoveries(out / 'recovery', json.loads(pointer.read_text())['file'])
    else:
        if parameter_digest(model, True) != initial['initial_adapter']:
            raise ValueError('First segment must start from exact registered parent')
        random.seed(17); np.random.seed(17); torch.manual_seed(17)
        state = dict(fingerprint=fingerprint, protocol=protocol, step=0, history=[],
            checkpoints={'0': _checkpoint(model, out, 0)}, initial_adapter=initial['initial_adapter'])
        state = _save_recovery(model, optimizer, out, state, device)
    if end_step < state['step']:
        raise ValueError('Segment boundary precedes committed cursor')
    discarded = _discarded_history(out, state['history'])
    segment_id = 'segment_' + uuid.uuid4().hex
    journal_path = out / 'segments' / (segment_id + '.jsonl')
    start_step = state['step']; committed_step = start_step
    history = list(state['history']); checkpoints = dict(state['checkpoints'])
    params = [p for p in model.parameters() if p.requires_grad]
    local_rows = []; status = 'partial'; error = None

    def commit(step):
        nonlocal state, committed_step
        if step in protocol['checkpoint_steps']:
            checkpoints[str(step)] = _checkpoint(model, out, step)
        if step != committed_step:
            state = _save_recovery(model, optimizer, out, dict(fingerprint=fingerprint,
                protocol=protocol, step=step, history=history, checkpoints=checkpoints,
                initial_adapter=initial['initial_adapter']), device)
            committed_step = step

    try:
        with journal_path.open('x') as journal:
            for offset in range(start_step, end_step):
                if deadline is not None and time.time() >= deadline - SOFT_RESERVE_SECONDS:
                    break
                model.train(); optimizer.zero_grad(set_to_none=True)
                if str(device).startswith('cuda'):
                    torch.cuda.synchronize()
                tick = time.monotonic(); indices = schedule[offset]; rows = [encoded[i] for i in indices]
                nll = accumulate_gradients(model, rows, tokenizer.pad_token_id, 1, device)
                norm = torch.nn.utils.clip_grad_norm_(params, 1.)
                if not torch.isfinite(norm) or not math.isfinite(nll):
                    raise FloatingPointError('Nonfinite training gradient/loss')
                for group in optimizer.param_groups:
                    group['lr'] = lrs[offset]
                optimizer.step()
                if str(device).startswith('cuda'):
                    torch.cuda.synchronize()
                row = dict(step=offset + 1, row_indices=indices, learning_rate=lrs[offset],
                    response_nll=nll, gradient_norm=norm.item(),
                    supervised_tokens=sum(r['n_supervised'] for r in rows),
                    processed_tokens=sum(r['n_processed'] for r in rows), seconds=time.monotonic() - tick,
                    peak_memory_bytes=torch.cuda.max_memory_allocated() if str(device).startswith('cuda') else None,
                    segment_file=journal_path.name, segment_line=len(local_rows))
                journal.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
                journal.flush(); os.fsync(journal.fileno())
                history.append(row); local_rows.append(row)
                if row['step'] == 1 or row['step'] % 16 == 0:
                    print(json.dumps(row), flush=True)
                if row['step'] % 16 == 0:
                    commit(row['step'])
            commit(len(history))
        optimizer.zero_grad(set_to_none=True)
        if any(not torch.isfinite(p).all() for p in params):
            raise FloatingPointError('Nonfinite final adapter')
        status = 'completed' if committed_step == total else 'partial'
    except BaseException as exc:
        error = dict(type=type(exc).__name__, message=str(exc))
        status = 'failed'
        raise
    finally:
        _json(out / 'segments' / (segment_id + '.receipt.json'), dict(
            status=status, start_step=start_step, requested_end_step=end_step,
            committed_step=committed_step, physically_finished_updates=len(local_rows),
            uncommitted_finished_updates=max(0, len(history) - committed_step),
            process_seconds=time.monotonic() - started, error=error,
            discarded_prior_work=discarded, completed_at_utc=stamp()))
    return dict(status=status, step=committed_step, cumulative_history=history,
        checkpoints=checkpoints, fingerprint=fingerprint, initial_adapter=initial['initial_adapter'],
        final_adapter=parameter_digest(model, True), resumed_after_step=start_step,
        segment_updates=len(local_rows), segment_seconds=time.monotonic() - started,
        discarded_uncommitted_history=discarded,
        recovery=json.loads(pointer.read_text()))
