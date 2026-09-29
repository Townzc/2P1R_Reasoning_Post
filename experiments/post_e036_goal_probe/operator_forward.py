"""Exact candidate continuation scoring; no autoregressive sampling or training."""
import math
from pathlib import Path
import time

from .generation import _atomic, _digest, _file_hash, _read


def probabilities(logps):
    if len(logps) != 4 or any(not math.isfinite(x) or x > 1e-6 for x in logps):
        raise ValueError('Four finite nonpositive log probabilities required')
    mass=sum(math.exp(x) for x in logps)
    maximum=max(logps); z=sum(math.exp(x-maximum) for x in logps)
    return mass, [math.exp(x-maximum)/z for x in logps]


def score_candidates(model, context, candidates):
    import torch
    if not context or set(candidates) != set('+-*/') or any(not v for v in candidates.values()):
        raise ValueError('Comparable nonempty context and four continuations required')
    if max(len(context)+len(v) for v in candidates.values()) > 1024:
        raise ValueError('Operator context exceeded')
    ops=list('+-*/'); logps=[]; calls=0; input_tokens=0
    torch.cuda.synchronize(); tick=time.monotonic(); torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode(), torch.autocast('cuda',dtype=torch.bfloat16):
        if all(len(candidates[o]) == 1 for o in ops):
            inputs=torch.tensor([context],device='cuda')
            lp=model(input_ids=inputs,attention_mask=torch.ones_like(inputs),use_cache=False).logits[0,-1].float().log_softmax(-1)
            logps=[lp[candidates[o][0]].item() for o in ops]
            calls=1; input_tokens=len(context)
        else:
            for op in ops:
                cand=candidates[op]; inputs=torch.tensor([context+cand[:-1]],device='cuda')
                logits=model(input_ids=inputs,attention_mask=torch.ones_like(inputs),use_cache=False).logits[0]
                # Only candidate tokens; no EOS, future numbers, or result.
                lp=logits[len(context)-1:len(context)+len(cand)-1].float().log_softmax(-1)
                logps.append(sum(lp[i,t].item() for i,t in enumerate(cand)))
                calls+=1; input_tokens+=inputs.numel()
    torch.cuda.synchronize()
    return dict(log_probabilities=logps,forward_calls=calls,input_tokens=input_tokens,
        candidate_tokens=sum(map(len,candidates.values())),seconds=time.monotonic()-tick,
        peak_memory_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_memory_reserved_bytes=torch.cuda.max_memory_reserved())


def run_operator(model, rows, out, state, model_hash, release_hash, deadline):
    directory=Path(out)/'operator_scores'/state;directory.mkdir(parents=True,exist_ok=True)
    records=[]
    for i,row in enumerate(rows):
        path=directory/f'{i:06d}.json'; intent=directory/f'{i:06d}.intent.json'
        identity=dict(request_hash=_digest(row),model_hash=model_hash,release_manifest_sha256=release_hash)
        if path.exists():
            record=_read(path)
            if record['identity'] != identity:raise ValueError('Operator result identity changed')
        else:
            if intent.exists():raise RuntimeError('Ambiguous operator forward: no automatic replay')
            if time.time()+90 > deadline:break
            meta={k:row[k] for k in ('problem_id','group_id','target_index','skeleton_family_id','expected_operator') if k in row}
            record=dict(**meta,state=state,identity=identity,
                correct_operator=row['expected_operator'],context_ids=row.get('context_ids'),
                candidate_ids=row.get('candidates'),full_context_text=row.get('full_context_text'),
                answer_prefix=row.get('answer_prefix'))
            if not row['available']:
                record.update(status='unavailable',reason=row['reason'],forward_calls=0,input_tokens=0,seconds=0,candidates=[])
            else:
                _atomic(intent,identity,immutable=True)
                metrics=score_candidates(model,row['context_ids'],row['candidates'])
                logps=metrics.pop('log_probabilities'); mass,normalized=probabilities(logps)
                record.update(status='available',reason=None,**metrics,candidate_probability_mass=mass,
                    candidates=[dict(operator=o,log_probability=lp,probability=math.exp(lp),normalized_probability=np)
                                for o,lp,np in zip('+-*/',logps,normalized)])
            _atomic(path,record,immutable=True)
        records.append(record)
    result=dict(state=state,release_manifest_sha256=release_hash,model_hash=model_hash,records=records,
        status='completed' if len(records)==len(rows) else 'partial',
        recorded_contexts=len(records),unavailable_contexts=sum(r['status']=='unavailable' for r in records),
        forward_contexts=sum(r['status']=='available' for r in records),
        candidate_scores=4*sum(r['status']=='available' for r in records),
        forward_calls=sum(r['forward_calls'] for r in records),
        input_tokens=sum(r['input_tokens'] for r in records),seconds=sum(r['seconds'] for r in records))
    _atomic(directory.parent/(state+'.json'),result)
    return result
