"""Durable inference for the fixed pilot; no retries of ambiguous model calls."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import time

import torch

from .preflight import (PHASE, generation_batch, json_hash, seed_all, sha, write_json)
from .tokenization import ASSISTANT_END_ID, EOS_ID, trim_stop_text


def read(path):
    return json.loads(Path(path).read_text())


def ensure_record(path, value):
    path = Path(path)
    if path.exists():
        if read(path) != value:
            raise ValueError('Existing identity differs: ' + str(path))
    else:
        write_json(path, value)


class PhysicalLedger:
    """Caller also holds the whole-phase GPU lock; reservations precede work."""
    caps = {'nonformal_optimizer_update': 8, 'generation': 31203, 'annotation_forward': 8192}

    def __init__(self, path):
        self.path = Path(path)

    def reserve(self, kind, logical_ids):
        if kind not in self.caps or not logical_ids or len(set(logical_ids)) != len(logical_ids):
            raise ValueError('Invalid physical reservation')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            events = [json.loads(line) for line in f if line.strip()]
            if any(e['phase'] != PHASE for e in events):
                raise ValueError('Physical phase differs')
            previous = [e['logical_id'] for e in events if e['kind'] == kind]
            if len(previous) + len(logical_ids) > self.caps[kind]:
                raise RuntimeError('Physical budget exhausted: ' + kind)
            if set(previous).intersection(logical_ids):
                raise RuntimeError('Already reserved; reconcile missing output before retrying')
            now = datetime.now(timezone.utc).isoformat()
            f.seek(0, 2)
            for i, logical_id in enumerate(logical_ids, start=len(previous) + 1):
                f.write(json.dumps(dict(phase=PHASE, kind=kind, logical_id=logical_id,
                    ordinal=i, reserved_at_utc=now), sort_keys=True) + '\n')
            f.flush(); os.fsync(f.fileno())


def stop_due(deadline, reserve=180):
    return time.time() + reserve >= deadline


def require_time(deadline, reserve=180):
    if stop_due(deadline, reserve):
        raise TimeoutError('Daytime checkpoint/stop boundary reached')


def generation_rng():
    return dict(torch=torch.get_rng_state().tolist(),
        cuda=[s.tolist() for s in torch.cuda.get_rng_state_all()] if torch.cuda.is_initialized() else [])


def restore_generation_rng(state):
    if set(state) != {'torch', 'cuda'}:
        raise ValueError('Incomplete generation RNG')
    torch.set_rng_state(torch.tensor(state['torch'], dtype=torch.uint8))
    if state['cuda']:
        if len(state['cuda']) != torch.cuda.device_count():
            raise ValueError('Generation CUDA RNG topology differs')
        torch.cuda.set_rng_state_all([torch.tensor(s, dtype=torch.uint8) for s in state['cuda']])


def decode_tokens(tokenizer, tokens):
    first_eos = next((j for j, t in enumerate(tokens) if t in (ASSISTANT_END_ID, EOS_ID)), None)
    search_end = first_eos + 1 if first_eos is not None else len(tokens)
    first_string = None
    if '</s>' in tokenizer.decode(tokens[:search_end], skip_special_tokens=False):
        for j in range(1, search_end + 1):
            if '</s>' in tokenizer.decode(tokens[:j], skip_special_tokens=False):
                first_string = j; break
    if first_string is not None and (first_eos is None or first_string <= first_eos):
        tokens, reason = tokens[:first_string], 'stop_string'
    elif first_eos is not None:
        tokens, reason = tokens[:first_eos + 1], 'eos'
    else:
        reason = 'length_cap'
    if reason == 'length_cap' and len(tokens) != 2048:
        raise ValueError('Unexplained generation length')
    text = tokenizer.decode(tokens, skip_special_tokens=False)
    return dict(generated_ids=tokens, raw_text=text, scored_text=trim_stop_text(text),
        output_tokens=len(tokens), stop_reason=reason)


def checked_completed_batch(path, request):
    result = read(path)
    if result['request'] != request:
        raise ValueError('Completed generation request identity differs')
    records = result['records']
    if [r['id'] for r in records] != request['row_ids']:
        raise ValueError('Completed generation row identity differs')
    if [r['prompt_sha256'] for r in records] != request['prompt_sha256']:
        raise ValueError('Completed generation prompt identity differs')
    for r in records:
        if r['output_tokens'] != len(r['generated_ids']) or r['generation_calls'] != 1:
            raise ValueError('Completed generation count differs')
    if json_hash(records) != result['records_sha256']:
        raise ValueError('Completed output SHA differs')
    return result


def generate_rows(model, tokenizer, rows, folder, *, model_identity, logical_name,
                  ledger, deadline, batch_size, seed=None, reused=None, allow_new_calls=True):
    """One seeded stream per draw. Completed batches restore their post-call RNG."""
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate generation IDs')
    if batch_size not in (16, 64):
        raise ValueError('Unfrozen batch size')
    reused = reused or {}
    if seed is not None and reused:
        raise ValueError('Sampled stream cannot import foreign RNG history')
    if not set(reused).issubset(r['id'] for r in rows):
        raise ValueError('Unknown reused row')
    seed_all(17 if seed is None else seed)
    decode = dict(do_sample=seed is not None, max_new_tokens=2048,
        temperature=1.0 if seed is not None else None, top_p=1.0 if seed is not None else None,
        top_k=0 if seed is not None else None, seed=seed, repetition_penalty=1.0,
        stop_token_ids=[ASSISTANT_END_ID, EOS_ID], stop_strings=['</s>'],
        tools=False, extra_generation_rounds=0, batch_size=batch_size,
        precision='FP32_master_BF16_autocast', attention='sdpa', schema=2,
        implementation_sha256={n:sha(Path(__file__).with_name(n))
            for n in ('runtime_common.py','preflight.py','tokenization.py')},
        torch_version=torch.__version__,transformers_version=__import__('transformers').__version__)
    ensure_record(folder/'identity.json', dict(model=model_identity, logical_name=logical_name,
        decoding=decode, all_ids=[r['id'] for r in rows], reused_ids=sorted(reused)))
    records = []
    for row in rows:
        if row['id'] in reused:
            old = reused[row['id']]
            if old['prompt_sha256'] != json_hash(row['prompt_ids']) or old['decoding'] != 'greedy':
                raise ValueError('Reused generation prompt/decoding differs')
            records.append(old)
    pending_rows = [r for r in rows if r['id'] not in reused]
    for offset in range(0, len(pending_rows), batch_size):
        group = pending_rows[offset:offset + batch_size]
        request = dict(model=model_identity, logical_name=logical_name, decoding=decode,
            row_ids=[r['id'] for r in group], prompt_sha256=[json_hash(r['prompt_ids']) for r in group])
        path = folder/f'batch_{offset:05d}.json'
        if path.exists():
            result = checked_completed_batch(path, request)
            restore_generation_rng(result['rng_after'])
            records.extend(result['records']); continue
        if not allow_new_calls:
            raise ValueError('Completed run has missing batch outputs; no regeneration allowed')
        require_time(deadline, 240)
        ledger.reserve('generation', [logical_name + '/' + r['id'] for r in group])
        write_json(folder/f'batch_{offset:05d}.reservation.json', request)
        batch = generation_batch(group); began = time.monotonic()
        options = dict(do_sample=seed is not None, max_new_tokens=2048,
            pad_token_id=EOS_ID, eos_token_id=[ASSISTANT_END_ID, EOS_ID],
            repetition_penalty=1.0, use_cache=True, stop_strings=['</s>'], tokenizer=tokenizer)
        if seed is not None:
            options.update(temperature=1.0, top_p=1.0, top_k=0)
        model.eval(); torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
            outputs = model.generate(**batch, **options)
        torch.cuda.synchronize()
        ids = outputs[:, batch['input_ids'].shape[1]:].cpu().tolist()
        if len(ids) != len(group): raise ValueError('Missing generated row')
        result_rows = [dict(id=r['id'], prompt_sha256=json_hash(r['prompt_ids']),
            **decode_tokens(tokenizer, tokens), generation_calls=1,
            decoding='sampled' if seed is not None else 'greedy', extra_generation_rounds=0, tools=False)
            for r, tokens in zip(group, ids)]
        result = dict(request=request, records=result_rows, records_sha256=json_hash(result_rows),
            rng_after=generation_rng(), seconds=time.monotonic()-began,
            peak_memory_allocated=torch.cuda.max_memory_allocated(),
            completed_at_utc=datetime.now(timezone.utc).isoformat())
        write_json(path, result); records.extend(result_rows)
        del outputs, batch
        print(json.dumps(dict(event='generation_batch_done', run=logical_name,
            completed=len(records), total=len(rows), seconds=result['seconds'])), flush=True)
    if len(records) != len(rows) or len({r['id'] for r in records}) != len(rows):
        raise ValueError('Final generation coverage differs')
    by_id = {r['id']:r for r in records}
    records = [by_id[r['id']] for r in rows]
    summary = dict(logical_name=logical_name, count=len(records), records_sha256=json_hash(records),
        reused_count=len(reused), stops=dict(Counter(r['stop_reason'] for r in records)),
        output_tokens=sum(r['output_tokens'] for r in records))
    ensure_record(folder/'COMPLETE.json', summary)
    return records
