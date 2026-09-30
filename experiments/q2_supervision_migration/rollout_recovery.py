"""Durable evidence for a live trainer; never authorize a process restart.

Only standard-library code is imported. These helpers neither execute candidate
programs nor load checkpoints. Saving a checkpoint and sampled log probabilities
does not establish recovery of vLLM RNG, TRL buffers, or optimizer execution.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

from .contracts import identity_hash
from .gpu_profile import ProfileError, durable_json


def _json_evidence(value):
    """Retain non-JSON scalar values explicitly instead of emitting NaN JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return {'nonfinite_float_repr': repr(value)}
    if isinstance(value, (list, tuple)):
        return [_json_evidence(v) for v in value]
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            return {'unsupported_type': type(value).__name__, 'exact_repr': repr(value)}
        return {k: _json_evidence(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return {'unsupported_type': type(value).__name__, 'exact_repr': repr(value)}


def _tokens(value):
    return isinstance(value, (list, tuple)) and all(type(x) is int and x >= 0 for x in value)


def journal_backend_rollout(batch, prompt_ids, completion_ids, sampled_logprobs, *,
                            committed_updates, last_loaded_step, max_completion_tokens=640):
    """Persist the returned token/logprob payload before decoding or validation.

    A malformed return is retained but cannot authorize rewards or an update.
    Existing/partial journals are never overwritten or reused to call generation.
    The caller must invoke this immediately after the backend returns and before
    decoding. This records only the return; it never requests another rollout.
    """
    intent = batch.intent()
    body = {'schema': 1, 'kind': 'backend_rollout_before_decode',
            'intent_sha256': batch.intent_sha256,
            'policy_sha256': intent['policy_sha256'],
            'committed_updates': _json_evidence(committed_updates),
            'last_loaded_step': _json_evidence(last_loaded_step),
            'prompt_ids': _json_evidence(prompt_ids),
            'completion_ids': _json_evidence(completion_ids),
            'sampled_logprobs': _json_evidence(sampled_logprobs),
            'boundary': 'single_turn_return_before_decode_and_policy_logprob_forward',
            'cross_process_resume_authorized': False}
    body['record_sha256'] = identity_hash(body)
    durable_json(batch.directory / 'backend_rollout.json', body)
    n = len(intent['tasks'])
    if (type(committed_updates) is not int or committed_updates < 0 or
            type(last_loaded_step) is not int or last_loaded_step != committed_updates or
            committed_updates != intent['batch_index']):
        raise ProfileError('backend return has unverified policy/update lineage')
    if type(max_completion_tokens) is not int or max_completion_tokens <= 0:
        raise ProfileError('invalid frozen completion cap')
    if any(not isinstance(x, (list, tuple)) or len(x) != n
           for x in (prompt_ids, completion_ids, sampled_logprobs)):
        raise ProfileError('backend token/logprob batch shape differs')
    for prompt, completion, logps in zip(prompt_ids, completion_ids, sampled_logprobs):
        if not _tokens(prompt) or not prompt or not _tokens(completion):
            raise ProfileError('backend returned malformed token IDs')
        if len(completion) > max_completion_tokens:
            raise ProfileError('backend completion exceeds the frozen cap')
        if not isinstance(logps, (list, tuple)) or len(logps) != len(completion):
            raise ProfileError('sampled logprobs are not token-aligned')
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in logps):
            raise ProfileError('missing or nonfinite sampled token logprob')
    return body


def _file_inventory(path):
    """Hash actual bytes while rejecting links, empty files, and unstable saves."""
    if path.is_symlink() or not path.is_file():
        raise ProfileError('checkpoint contains a link or nonregular file')
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
        os.fsync(stream.fileno())
        closed = os.fstat(stream.fileno())
    after = path.stat()
    keys = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
    if not before.st_size or not keys(before) == keys(opened) == keys(closed) == keys(after):
        raise ProfileError('checkpoint file changed during inventory or is empty')
    return {'bytes': after.st_size, 'sha256': digest.hexdigest()}


def checkpoint_inventory(checkpoint_dir, phase_dir, *, committed_updates):
    """Verify a returned save against immutable commit receipts; no torch.load.

    Intended for on_save or a confirmed exception checkpoint after saving has
    returned. The caller writes this result to a separate exclusive-create
    manifest. The manifest must remain outside the inventoried checkpoint.
    """
    checkpoint, phase = Path(checkpoint_dir), Path(phase_dir)
    if type(committed_updates) is not int or committed_updates < 0:
        raise ProfileError('invalid checkpoint committed update count')
    expected = phase / 'trainer' / f'checkpoint-{committed_updates}'
    if checkpoint != expected or any(p.is_symlink() for p in (phase, phase / 'trainer', checkpoint)):
        raise ProfileError('checkpoint is not the owned phase save directory')
    if not checkpoint.is_dir():
        raise ProfileError('checkpoint save directory is missing')
    commits = {p.name for p in phase.glob('update_*.json')}
    pres = {p.name for p in phase.glob('pre_update_*.json')}
    wanted_commits = {f'update_{i:04d}.json' for i in range(1, committed_updates + 1)}
    wanted_pres = {f'pre_update_{i:04d}.json' for i in range(1, committed_updates + 1)}
    if commits != wanted_commits or pres != wanted_pres:
        raise ProfileError('checkpoint has missing, extra, or uncommitted update receipts')
    commit_hashes = {}
    for step in range(1, committed_updates + 1):
        update_path, pre_path = phase / f'update_{step:04d}.json', phase / f'pre_update_{step:04d}.json'
        update, pre = json.loads(update_path.read_text()), json.loads(pre_path.read_text())
        if (type(update.get('committed_update')) is not int or update['committed_update'] != step or
                type(pre.get('step')) is not int or pre['step'] != step or pre.get('all_finite') is not True or
                type(pre.get('gradient_tensors')) is not int or pre['gradient_tensors'] <= 0):
            raise ProfileError('checkpoint update receipts do not confirm a finite committed step')
        for path in (update_path, pre_path):
            commit_hashes[path.name] = _file_inventory(path)
    entries = sorted(checkpoint.rglob('*'))
    if any(p.is_symlink() or (not p.is_file() and not p.is_dir()) for p in entries):
        raise ProfileError('checkpoint contains a link or special file')
    files, stamps = {}, {}
    for path in entries:
        if path.is_file():
            name = str(path.relative_to(checkpoint))
            files[name] = _file_inventory(path)
            stat = path.stat()
            stamps[name] = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
    required = {'model.safetensors', 'optimizer.pt', 'scheduler.pt', 'rng_state.pth', 'trainer_state.json'}
    if not required <= files.keys():
        raise ProfileError('checkpoint lacks model/optimizer/scheduler/RNG/Trainer state')
    state = json.loads((checkpoint / 'trainer_state.json').read_text())
    if type(state.get('global_step')) is not int or state['global_step'] != committed_updates:
        raise ProfileError('checkpoint Trainer global_step differs from committed dose')
    # Include the parsed state in the same byte identity checked above.
    if _file_inventory(checkpoint / 'trainer_state.json') != files['trainer_state.json']:
        raise ProfileError('Trainer state changed during checkpoint inventory')
    final_entries = list(checkpoint.rglob('*'))
    if any(p.is_symlink() or (not p.is_dir() and not p.is_file()) for p in final_entries):
        raise ProfileError('checkpoint gained a link or special file during inventory')
    if {str(p.relative_to(checkpoint)) for p in final_entries if p.is_file()} != set(files):
        raise ProfileError('checkpoint file set changed during inventory')
    for name, stamp in stamps.items():
        stat = (checkpoint / name).stat()
        if (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) != stamp:
            raise ProfileError('checkpoint changed after a file was inventoried')
    for directory in sorted([checkpoint, *(p for p in entries if p.is_dir())], reverse=True):
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    return {'schema': 1, 'committed_updates': committed_updates,
            'trainer_global_step': state['global_step'], 'files': files,
            'commit_receipts': commit_hashes,
            'stable_file_hashes_recorded': True,
            'checkpoint_loading_verified': False,
            'vllm_rng_captured': False,
            'exact_resume_including_vllm_rng_verified': False,
            'cross_process_resume_authorized': False}
