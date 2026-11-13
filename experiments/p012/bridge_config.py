"""A4 Modal LoRA bridge configuration; formal execution awaits one review."""
from __future__ import annotations
import copy
from .training_config import training_config
from .training_inputs import validate_training_request

BRIDGE_LR = 5e-4 * (2000 / 1536) ** .0775
# LF's shorthand "all" excludes lm_head. Enumerate it to implement the owner's
# all-linear requirement and Tinker's train_unembed=True. Do not merge adapters
# into this model's tied embedding/output weights; evaluate with vLLM LoRA.
TARGETS = 'q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj,lm_head'


def bridge_config(model, revision, dataset, cell):
    cfg=training_config(model,revision,'qwen',dataset,'inputs','checkpoint',17,cell)
    cfg.update(finetuning_type='lora',learning_rate=BRIDGE_LR,lora_rank=32,
               lora_alpha=64,lora_dropout=0.0,lora_target=TARGETS)
    return cfg


def validate_bridge_request(request):
    if request['model']['repo']!='Qwen/Qwen2.5-1.5B' or request['config']['seed']!=17:
        raise ValueError('Bridge is Qwen1.5B base seed17 only')
    if request['config']!=bridge_config(request['model']['repo'],request['model']['revision'],
                                       request['dataset']['name'],request['cell']):
        raise ValueError('Bridge differs from frozen LoRA recipe')
    converted=copy.deepcopy(request)
    for key in ('lora_rank','lora_alpha','lora_dropout','lora_target'):converted['config'].pop(key)
    converted['config'].update(finetuning_type='full',learning_rate=1e-5)
    checked=validate_training_request(converted)
    checked.update(track='modal_lora_bridge',rank=32,learning_rate=BRIDGE_LR,
                   lora_alpha=64,alpha_basis='Pinned LLaMA-Factory default rank*2',
                   target_modules=TARGETS.split(','),merge_performed=False)
    return checked
