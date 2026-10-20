"""Immutable complete LoRA training states; never prunes or automatically replays."""
from pathlib import Path
import os
import random
from .common import dump, read, sha, digest


def cpu(value):
    import torch
    if isinstance(value,torch.Tensor):return value.detach().cpu().clone()
    if isinstance(value,dict):return {k:cpu(v) for k,v in value.items()}
    if isinstance(value,list):return [cpu(v) for v in value]
    if isinstance(value,tuple):return tuple(cpu(v) for v in value)
    return value


def rng_state():
    import torch,numpy as np
    n=np.random.get_state()
    return dict(python=random.getstate(),numpy=[n[0],n[1].tolist(),n[2],n[3],n[4]],
                torch=torch.get_rng_state(),cuda=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [])


def restore_rng(state):
    import torch,numpy as np
    random.setstate(state['python']);n=state['numpy']
    np.random.set_state((n[0],np.asarray(n[1],dtype=np.uint32),n[2],n[3],n[4]))
    torch.set_rng_state(state['torch'])
    if len(state['cuda']) != torch.cuda.device_count():raise ValueError('CUDA RNG device count differs')
    if state['cuda']:torch.cuda.set_rng_state_all(state['cuda'])


def same(a,b):
    import torch
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and a.dtype==b.dtype and torch.equal(a,b)
    if type(a)!=type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,(tuple,list)):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b


def snapshot(model,optimizer,identity,step,targets,processed,lrs,schedule):
    return dict(schema='complete_lora_v1',identity=identity,step=step,supervised_tokens=targets,
        processed_tokens=processed,lrs=lrs,schedule=schedule,cursor=step,
        trainable_names=[n for n,p in model.named_parameters() if p.requires_grad],
        adapter={n:cpu(p) for n,p in model.named_parameters() if p.requires_grad},
        optimizer=cpu(optimizer.state_dict()),rng=cpu(rng_state()))


def save(root,state,commit=lambda:None):
    import torch
    path=Path(root)/f"checkpoint_{state['step']:04d}";path.mkdir(parents=True,exist_ok=False)
    file=path/'state.pt'
    with file.open('xb') as f:
        torch.save(state,f);f.flush();os.fsync(f.fileno())
    restored=torch.load(file,map_location='cpu',weights_only=True)
    if not same(state,restored):raise ValueError('Full serialization changed training state')
    record=dict(schema=state['schema'],file='state.pt',bytes=file.stat().st_size,sha256=sha(file),
                identity_sha256=digest(state['identity']),step=state['step'],
                supervised_tokens=state['supervised_tokens'],processed_tokens=state['processed_tokens'])
    dump(path/'manifest.json',record);commit()
    return record


def load(path,identity=None):
    import torch
    path=Path(path);m=read(path/'manifest.json')
    if m['file']!='state.pt' or (path/'state.pt').stat().st_size!=m['bytes'] or sha(path/'state.pt')!=m['sha256']:
        raise ValueError('Checkpoint hash/size differs')
    s=torch.load(path/'state.pt',map_location='cpu',weights_only=True)
    if s['schema']!='complete_lora_v1' or digest(s['identity'])!=m['identity_sha256'] or s['cursor']!=s['step']:
        raise ValueError('Checkpoint identity/cursor differs')
    if identity is not None and s['identity']!=identity:raise ValueError('Foreign checkpoint')
    for k in ('step','supervised_tokens','processed_tokens'):
        if s[k]!=m[k]:raise ValueError('Checkpoint dose differs')
    return s


def restore(model,optimizer,state):
    import torch
    params={n:p for n,p in model.named_parameters() if p.requires_grad}
    if list(params)!=state['trainable_names'] or set(params)!=set(state['adapter']):
        raise ValueError('Trainable parameter identity differs')
    with torch.no_grad():
        for n,p in params.items():
            x=state['adapter'][n]
            if x.shape!=p.shape or x.dtype!=p.dtype or not torch.isfinite(x).all():
                raise ValueError('Adapter schema/finite check failed')
            p.copy_(x)
    optimizer.load_state_dict(state['optimizer'])
    if not same(cpu(optimizer.state_dict()),state['optimizer']):raise ValueError('Optimizer restore differs')
    restore_rng(state['rng'])


def maximum_difference(a,b):
    import torch
    if isinstance(a,torch.Tensor):
        if not isinstance(b,torch.Tensor) or a.shape!=b.shape or a.dtype!=b.dtype:return float('inf')
        return float((a.to('cpu').double()-b.to('cpu').double()).abs().max()) if a.numel() else 0.
    if type(a)!=type(b):return float('inf')
    if isinstance(a,dict):return max((maximum_difference(a[k],b[k]) for k in a),default=0.) if a.keys()==b.keys() else float('inf')
    if isinstance(a,(list,tuple)):return max((maximum_difference(x,y) for x,y in zip(a,b)),default=0.) if len(a)==len(b) else float('inf')
    return 0. if a==b else float('inf')

