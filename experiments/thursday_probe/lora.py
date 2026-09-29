"""One fixed PEFT recipe and byte-level checkpoint identity checks."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

from experiments.thursday_probe.common import dump
from src.relation_experiment import accumulate_gradients
from src.sft_data import sha256_file

TARGETS = ['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj']


def attach(model):
    from peft import LoraConfig, get_peft_model, TaskType
    if importlib.metadata.version('peft') != '0.17.1':
        raise ValueError('Pinned PEFT 0.17.1 required')
    cfg = LoraConfig(r=16,lora_alpha=32,lora_dropout=0,bias='none',
                     target_modules=TARGETS,task_type=TaskType.CAUSAL_LM)
    model = get_peft_model(model,cfg)
    for name,p in model.named_parameters():
        if p.requires_grad != ('lora_' in name):
            raise ValueError('Unexpected adaptation parameter scope')
    return model


def parameter_digest(model, adapter=False):
    h=hashlib.sha256(); count=0
    for name,p in model.named_parameters():
        if ('lora_' in name) != adapter:
            continue
        h.update(name.encode()); h.update(str(tuple(p.shape)).encode())
        h.update(str(p.dtype).encode()); h.update(p.detach().cpu().contiguous().numpy().tobytes())
        count += p.numel()
    return {'sha256':h.hexdigest(),'parameters':count}


def save_adapter(model, path):
    path=Path(path)
    if path.exists():
        raise FileExistsError('Never overwrite unique adapter')
    model.save_pretrained(path, safe_serialization=True)
    hashes={p.name:sha256_file(p) for p in path.iterdir() if p.is_file()}
    record={'files_sha256':hashes,'bytes':sum(p.stat().st_size for p in path.iterdir() if p.is_file()),
            'parameter_digest':parameter_digest(model,True)}
    dump(path/'checkpoint_identity.json',record)
    return record


def train(model, encoded, schedule, lrs, tokenizer, out, checkpoints=False, midpoint=None):
    import torch
    if len(schedule) != len(lrs) or any(lr <= 0 for lr in lrs):
        raise ValueError('Frozen positive LR vector required')
    params=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(params,lr=lrs[0],betas=(.9,.999),eps=1e-8,weight_decay=0,foreach=False)
    if optimizer.state:
        raise ValueError('Optimizer state must reset')
    histories=[]; saved={}
    if checkpoints:
        saved['0']=save_adapter(model, out/'checkpoint_0')
    with (out/'train_history.jsonl').open('x') as log:
        for step,(indices,lr) in enumerate(zip(schedule,lrs),1):
            model.train(); optimizer.zero_grad(set_to_none=True)
            torch.cuda.synchronize(); tick=time.monotonic()
            rows=[encoded[i] for i in indices]
            nll=accumulate_gradients(model,rows,tokenizer.pad_token_id,1,'cuda')
            norm=torch.nn.utils.clip_grad_norm_(params,1.)
            if not torch.isfinite(norm):
                raise FloatingPointError('Nonfinite gradient')
            for g in optimizer.param_groups:
                g['lr']=lr
            optimizer.step(); torch.cuda.synchronize()
            r={'step':step,'row_indices':indices,'learning_rate':lr,'response_nll':nll,
               'gradient_norm':norm.item(),'supervised_tokens':sum(r['n_supervised'] for r in rows),
               'processed_tokens':sum(r['n_processed'] for r in rows),'seconds':time.monotonic()-tick,
               'peak_memory_bytes':torch.cuda.max_memory_allocated()}
            histories.append(r); log.write(json.dumps(r,allow_nan=False)+'\n'); log.flush()
            if step == 1 or step % 16 == 0:
                print(json.dumps(r),flush=True)
            if checkpoints and step in {len(schedule)//4,len(schedule)//2,len(schedule)}:
                saved[str(step)]=save_adapter(model,out/('checkpoint_'+str(step)))
            if midpoint and step == len(schedule)//2:
                midpoint(model)
    optimizer.zero_grad(set_to_none=True)
    del optimizer
    return histories,saved
