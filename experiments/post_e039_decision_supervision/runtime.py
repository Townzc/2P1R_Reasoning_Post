"""Decision-weighted continuation using the previously verified recovery primitives.

No historical module globals are changed. The segment loop is the frozen trainer
with a new 128-step protocol and an explicit token-weighted loss entry point.
"""
from contextlib import nullcontext
import json
import math
import os
from pathlib import Path
import time
import uuid

from experiments.thursday_probe.common import digest, stamp
from experiments.thursday_probe.lora import parameter_digest
from experiments.thursday_probe_v2.training import new_optimizer
from experiments.post_e037_goal_training.training import (
    _json, _checkpoint, _save_recovery, _read_recovery, _load_into_model,
    _prune_recoveries, _discarded_history, SOFT_RESERVE_SECONDS)
from src.sft_data import encode_row, collate, shifted_loss_sum


def prepare_encoded(rows, span_records, tokenizer, max_length=1024):
    """Attach predeclared full-token masks to exact historical serialization."""
    if len(rows) != len(span_records):
        raise ValueError('One span record is required for every original row')
    result=[]
    for row,span in zip(rows,span_records):
        encoded=encode_row(row,tokenizer,max_length)
        from .decision_spans import validate_mask
        validate_mask(encoded,span)
        if span['source_row_sha256']!=digest(row):
            raise ValueError('Span audit belongs to a different original training row')
        mask=span['decision_mask']; interface=row.get('interface')
        if interface not in ('H','F') or len(mask)!=len(encoded['input_ids']) or any(type(x) is not bool for x in mask):
            raise ValueError('Frozen full-token decision mask/interface is invalid')
        if any(m and (label==-100 or i==len(mask)-1) for i,(m,label) in enumerate(zip(mask,encoded['labels']))):
            raise ValueError('Prompt, padding and terminal EOS cannot be decision tokens')
        selected=[i for i,m in enumerate(mask) if m]
        if interface=='H' and (not selected or selected!=list(range(selected[0],selected[-1]+1))):
            raise ValueError('Every H row requires a contiguous first-decision span')
        if interface=='H' and span.get('prior_leakage') is not False:
            raise ValueError('First decision requires an explicit prior-leakage audit')
        if interface=='F' and selected:
            raise ValueError('F supervision must remain unchanged')
        if span.get('decision_token_indices',selected)!=selected:
            raise ValueError('Decision token indices differ from full mask')
        if span.get('causal_logit_indices',[i-1 for i in selected])!=[i-1 for i in selected]:
            raise ValueError('Decision logits are shifted by exactly one token')
        # Data preparation may bind either the entire canonical encoded record or
        # its fields; never silently adopt a mask for a different token sequence.
        if 'input_ids' in span and span['input_ids']!=encoded['input_ids']:
            raise ValueError('Span audit and encoded input token IDs differ')
        if 'encoded_sha256' in span and span['encoded_sha256']!=digest(encoded):
            raise ValueError('Span audit encoded identity differs')
        result.append(dict(**encoded,interface=interface,decision_mask=list(mask)))
    return result


def row_weights(row, objective):
    if objective not in ('U','D'):
        raise ValueError('Explicit U or D training objective required')
    mask=row['decision_mask'];labels=row['labels'];length=row['n_supervised']
    if len(mask)!=len(labels) or len(labels)!=len(row['input_ids']) or any(type(m) is not bool for m in mask):
        raise ValueError('Token/mask alignment differs')
    valid=[i>0 and label!=-100 for i,label in enumerate(labels)]
    if sum(valid)!=length or length<=0 or labels[-1]==-100 or mask[-1] or any(m and not v for m,v in zip(mask,valid)):
        raise ValueError('Invalid supervised positions, denominator, or EOS mask')
    k=sum(mask)
    if row['interface']=='H':
        if k<=0:raise ValueError('Missing first-decision H supervision')
    elif row['interface']!='F' or k:
        raise ValueError('F rows cannot have decision weights')
    multiplier=5. if objective=='D' and row['interface']=='H' else 1.
    denominator=length+(multiplier-1)*k
    weights=[length*(multiplier if m else 1.)/denominator if v else 0. for m,v in zip(mask,valid)]
    if not math.isclose(sum(weights),length,rel_tol=1e-12,abs_tol=1e-12):
        raise ValueError('Per-response weight mass not conserved')
    return weights


def loss_sums(logits, labels, weights):
    """Predict labels[t] from logits[t-1]; ignore prompt/right-padding labels."""
    import torch
    import torch.nn.functional as F
    if logits.shape[:2]!=labels.shape or weights.shape!=labels.shape:
        raise ValueError('Logits/labels/weights shape mismatch')
    targets=labels[:,1:];valid=targets!=-100;w=weights[:,1:]
    if not valid.any() or not torch.isfinite(weights).all() or (weights<0).any() or (w[~valid]!=0).any():
        raise ValueError('Invalid supervised weight tensor')
    raw=shifted_loss_sum(logits,labels)
    if torch.all(w[valid]==1):return raw,raw
    losses=F.cross_entropy(logits[:,:-1][valid].float(),targets[valid],reduction='none')
    return (losses*w[valid]).sum(),raw


def accumulate_gradients(model, rows, pad_id, microbatch, device, *, objective):
    import torch
    denominator=sum(r['n_supervised'] for r in rows)
    if denominator<=0 or microbatch<=0:raise ValueError('Positive raw supervised denominator required')
    weighted_total=raw_total=0.
    for start in range(0,len(rows),microbatch):
        part=rows[start:start+microbatch];batch={k:v.to(device) for k,v in collate(part,pad_id).items()}
        width=batch['labels'].shape[1]
        weights=torch.tensor([row_weights(r,objective)+[0.]*(width-len(r['labels'])) for r in part],device=device,dtype=torch.float32)
        context=torch.autocast('cuda',dtype=torch.bfloat16) if str(device).startswith('cuda') else nullcontext()
        with context:
            output=model(input_ids=batch['input_ids'],attention_mask=batch['attention_mask'],use_cache=False)
            weighted,raw=loss_sums(output.logits,batch['labels'],weights)
        if not torch.isfinite(weighted) or not torch.isfinite(raw):raise FloatingPointError('Nonfinite continuation loss')
        (weighted/denominator).backward()
        weighted_total+=weighted.detach().item();raw_total+=raw.detach().item()
        del output,weighted,raw,batch,weights
    return dict(objective_loss=weighted_total/denominator,unweighted_response_nll=raw_total/denominator,
                raw_supervised_denominator=denominator,weight_mass=sum(sum(row_weights(r,objective)) for r in rows))


def train_segment(model, encoded, schedule, lrs, tokenizer, out, *, identity,
                  objective, end_step, deadline, device='cuda'):
    """Advance one logical run to an absolute boundary, preserving frozen dose.

    The caller restores the registered parent only on the first invocation. Later
    invocations load this run's adapter AND optimizer/RNG, regardless of the
    caller's current adapter. No midpoint evaluation runs inside training.
    """
    import random
    import numpy as np
    import torch
    started = time.monotonic()
    out = Path(out)
    if objective not in ('U','D'):raise ValueError('Explicit U or D objective required')
    for row in encoded:row_weights(row,objective)
    total = len(schedule)
    if (not total or total != len(lrs) or any(not math.isfinite(x) or x <= 0 for x in lrs) or
            type(end_step) is not int or not 0 <= end_step <= total):
        raise ValueError('Invalid frozen dose, LR vector, or absolute segment boundary')
    if deadline is not None and not math.isfinite(deadline):
        raise ValueError('A finite deadline is required when specified')
    if any(not indices or any(type(i) is not int or not 0 <= i < len(encoded) for i in indices)
           for indices in schedule):
        raise ValueError('Invalid frozen training schedule')
    if str(device).startswith('cuda') and (total != 128 or any(len(x) != 16 for x in schedule)):
        raise ValueError('Production training requires registered 128 updates and effective batch16')
    if any(p.requires_grad != ('lora_' in n) or p.dtype != torch.float32 for n, p in model.named_parameters()):
        raise ValueError('Frozen FP32 base and LoRA-only trainable scope required')
    protocol = dict(identity=identity, identity_sha256=digest(identity), schedule_sha256=digest(schedule),
        lr_vector_sha256=digest(lrs), encoded_rows_sha256=digest([digest(r) for r in encoded]),
        total_updates=total, microbatch=1, clip=1., optimizer='AdamW(.9,.999,1e-8,0)',
        training_seed=17, checkpoint_steps=sorted({0,total} | {s for s in (64,128) if s<=total}),
        objective=objective, decision_multiplier=5. if objective=='D' else 1.,
        H_weight_mass='per_response_raw_supervised_tokens', F_weights=1.,
        denominator='raw_supervised_tokens', decision_masks_sha256=digest([r['decision_mask'] for r in encoded]))
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
                metrics = accumulate_gradients(model, rows, tokenizer.pad_token_id, 1, device, objective=objective)
                nll = metrics['objective_loss']
                norm = torch.nn.utils.clip_grad_norm_(params, 1.)
                if not torch.isfinite(norm) or not math.isfinite(nll):
                    raise FloatingPointError('Nonfinite training gradient/loss')
                for group in optimizer.param_groups:
                    group['lr'] = lrs[offset]
                optimizer.step()
                if str(device).startswith('cuda'):
                    torch.cuda.synchronize()
                row = dict(step=offset + 1, row_indices=indices, learning_rate=lrs[offset],
                    response_nll=nll, objective_loss=nll, unweighted_response_nll=metrics['unweighted_response_nll'],
                    objective=objective, raw_supervised_denominator=metrics['raw_supervised_denominator'],
                    weight_mass=metrics['weight_mass'], gradient_norm=norm.item(),
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
