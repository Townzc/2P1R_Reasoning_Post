"""Independent adapter forks with fresh AdamW and atomically committed recovery."""
import json
import math
from pathlib import Path
import time

from experiments.thursday_probe.common import digest, dump, stamp
from experiments.thursday_probe.lora import parameter_digest, save_adapter
from src.relation_experiment import accumulate_gradients
from src.sft_data import sha256_file


def atomic_json(path, record):
    path = Path(path)
    temporary = path.with_name(path.name+'.pending')
    with temporary.open('w') as f:
        json.dump(record,f,indent=2,sort_keys=True,allow_nan=False); f.write('\n')
        f.flush()
        import os
        os.fsync(f.fileno())
    temporary.replace(path)


def adapter_state(model):
    from peft import get_peft_model_state_dict
    return {k:v.detach().cpu().clone() for k,v in get_peft_model_state_dict(model).items()}


def restore_adapter(model, checkpoint):
    from peft import get_peft_model_state_dict, set_peft_model_state_dict
    from safetensors.torch import load_file
    import torch
    checkpoint = Path(checkpoint)
    identity = json.loads((checkpoint/'checkpoint_identity.json').read_text())
    for name, h in identity['files_sha256'].items():
        if sha256_file(checkpoint/name) != h:
            raise ValueError('Parent adapter bytes changed')
    state = load_file(str(checkpoint/'adapter_model.safetensors'))
    if set(state) != set(get_peft_model_state_dict(model)):
        raise ValueError('Parent/child adapter capacity differs')
    set_peft_model_state_dict(model,state)
    if parameter_digest(model,True) != identity['parameter_digest']:
        raise ValueError('Child did not start from the exact parent tensors')
    if any(p.requires_grad != ('lora_' in n) for n,p in model.named_parameters()):
        raise ValueError('Adaptation parameter scope changed')
    if any(p.dtype != torch.float32 for p in model.parameters()):
        raise ValueError('FP32 base and adapters required')
    return identity


def new_optimizer(model, lr):
    import torch
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
        lr=lr,betas=(.9,.999),eps=1e-8,weight_decay=0,foreach=False)
    if optimizer.state:
        raise ValueError('Main/prep stage must reset optimizer state')
    return optimizer


def cpu_tree(obj):
    import torch
    if isinstance(obj,torch.Tensor):
        return obj.detach().cpu().clone()
    if isinstance(obj,dict):
        return {k:cpu_tree(v) for k,v in obj.items()}
    if isinstance(obj,list):
        return [cpu_tree(v) for v in obj]
    if isinstance(obj,tuple):
        return tuple(cpu_tree(v) for v in obj)
    return obj


def save_recovery(model, optimizer, folder, step, fingerprint, device):
    """Keep last committed recovery until the new file AND pointer are durable.

    Only obsolete rolling recovery files written by this function are pruned;
    scientific adapter checkpoints at 0/64/128/256 are never overwritten.
    """
    import torch
    import os
    folder=Path(folder); folder.mkdir(exist_ok=True)
    pointer=folder/'latest.json'
    previous=json.loads(pointer.read_text()) if pointer.exists() else None
    path=folder/f'step_{step:06d}.pt'
    if path.exists():
        raise FileExistsError('Recovery step already exists')
    record=dict(step=step,fingerprint=fingerprint,adapter=adapter_state(model),
        optimizer=cpu_tree(optimizer.state_dict()),torch_rng=torch.get_rng_state(),
        cuda_rng=torch.cuda.get_rng_state_all() if str(device).startswith('cuda') else [])
    with path.open('xb') as stream:
        torch.save(record,stream); stream.flush(); os.fsync(stream.fileno())
    current=dict(file=path.name,sha256=sha256_file(path),bytes=path.stat().st_size,
                 step=step,fingerprint=fingerprint,created_at_utc=stamp())
    atomic_json(pointer,current)
    if previous:
        old=folder/previous['file']
        if old.parent!=folder or not old.name.startswith('step_') or old.suffix!='.pt':
            raise ValueError('Invalid previous recovery path')
        if old != path:
            old.unlink()
    return current


def load_recovery(model, optimizer, folder, fingerprint, device):
    import torch
    from peft import set_peft_model_state_dict
    folder=Path(folder); pointer=json.loads((folder/'latest.json').read_text())
    path=folder/pointer['file']
    if path.parent!=folder or sha256_file(path)!=pointer['sha256'] or pointer['fingerprint']!=fingerprint:
        raise ValueError('Recovery identity mismatch')
    state=torch.load(path,map_location='cpu',weights_only=True)
    if state['fingerprint']!=fingerprint or state['step']!=pointer['step']:
        raise ValueError('Recovery state/config mismatch')
    set_peft_model_state_dict(model,state['adapter'])
    optimizer.load_state_dict(state['optimizer'])
    torch.set_rng_state(state['torch_rng'])
    if str(device).startswith('cuda'):
        torch.cuda.set_rng_state_all(state['cuda_rng'])
    return state['step']


def train(model, encoded, schedule, lrs, tokenizer, out, *, identity,
          checkpoint_steps, midpoint=None, deadline=None, device='cuda', resume_from=None):
    import torch
    out=Path(out)
    if len(schedule)!=len(lrs) or any(not math.isfinite(x) or x<=0 for x in lrs):
        raise ValueError('Invalid frozen dose or learning rate vector')
    fingerprint=digest(dict(identity=identity,schedule=schedule,lrs=lrs,
        row_hashes=[digest(r) for r in encoded],microbatch=1,clip=1.,optimizer='AdamW(.9,.999,1e-8,0)'))
    optimizer=new_optimizer(model,lrs[0]); params=[p for p in model.parameters() if p.requires_grad]
    step0=load_recovery(model,optimizer,resume_from,fingerprint,device) if resume_from else 0
    log_path=out/'train_history.jsonl'
    if log_path.exists():
        raise FileExistsError('Resume into a new attempt directory; never append ambiguous history')
    before=parameter_digest(model,True)
    saved={}; histories=[]; started=time.monotonic()
    if not resume_from:
        torch.manual_seed(17)
        saved['0']=save_adapter(model,out/'checkpoint_0')
        save_recovery(model,optimizer,out/'recovery',0,fingerprint,device)
    with log_path.open('x') as stream:
        for offset in range(step0,len(schedule)):
            if deadline is not None and time.time() >= deadline:
                raise TimeoutError('Training/phase time allowance exhausted')
            indices,lr=schedule[offset],lrs[offset]
            model.train(); optimizer.zero_grad(set_to_none=True)
            if str(device).startswith('cuda'): torch.cuda.synchronize()
            tick=time.monotonic(); rows=[encoded[i] for i in indices]
            nll=accumulate_gradients(model,rows,tokenizer.pad_token_id,1,device)
            norm=torch.nn.utils.clip_grad_norm_(params,1.)
            if not torch.isfinite(norm) or not math.isfinite(nll):
                raise FloatingPointError('Nonfinite training gradient/loss')
            for group in optimizer.param_groups: group['lr']=lr
            optimizer.step()
            if str(device).startswith('cuda'): torch.cuda.synchronize()
            step=offset+1
            row=dict(step=step,row_indices=indices,learning_rate=lr,response_nll=nll,
                gradient_norm=norm.item(),supervised_tokens=sum(r['n_supervised'] for r in rows),
                processed_tokens=sum(r['n_processed'] for r in rows),seconds=time.monotonic()-tick,
                peak_memory_bytes=torch.cuda.max_memory_allocated() if str(device).startswith('cuda') else None)
            histories.append(row); stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
            if step==1 or step%16==0: print(json.dumps(row),flush=True)
            if step%16==0 or step==len(schedule):
                # This includes optimizer moments, exact LR-vector position and RNG.
                save_recovery(model,optimizer,out/'recovery',step,fingerprint,device)
            if step in checkpoint_steps:
                saved[str(step)]=save_adapter(model,out/f'checkpoint_{step}')
            if midpoint and step==128:
                rng=torch.get_rng_state(); cuda_rng=torch.cuda.get_rng_state_all()
                midpoint(model)
                torch.set_rng_state(rng);torch.cuda.set_rng_state_all(cuda_rng)
    optimizer.zero_grad(set_to_none=True)
    final=parameter_digest(model,True)
    if final==before:
        raise ValueError('No adapter parameter update')
    if any(not torch.isfinite(p).all() for p in params):
        raise FloatingPointError('Nonfinite final adapter')
    dump(out/'training_summary.json',dict(updates=len(histories),resumed_after_step=step0,
        supervised_tokens=sum(r['supervised_tokens'] for r in histories),
        processed_tokens=sum(r['processed_tokens'] for r in histories),
        elapsed_seconds=time.monotonic()-started,initial_adapter=before,final_adapter=final,
        optimizer_reset=not bool(resume_from),fingerprint=fingerprint,checkpoints=saved))
    return histories,saved
