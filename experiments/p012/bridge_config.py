"""A4 Modal LoRA bridge configuration, accepted with B-1/B-2 at 8bbf06a7."""
from __future__ import annotations
import copy
from .training_config import training_config
from .training_inputs import validate_training_request

BRIDGE_LR = 5e-4 * (2000 / 1536) ** .0775
# B-2: vLLM0.11 cannot load lm_head LoRA for Qwen's tied embedding/output head.
# Keep adapters unmerged and record this difference from Tinker train_unembed.
TARGETS = 'q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj'


def bridge_config(model, revision, dataset, cell):
    cfg=training_config(model,revision,'qwen',dataset,'inputs','checkpoint',17,cell)
    cfg.update(finetuning_type='lora',learning_rate=BRIDGE_LR,lora_rank=32,
               lora_alpha=32,lora_dropout=0.0,lora_target=TARGETS)
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
                   lora_alpha=32,alpha_basis='B-1: cookbook alpha32; based on documentation, not confirmed by server',
                   target_modules=TARGETS.split(','),merge_performed=False,
                   expected_trainable_parameters=36929536,
                   tinker_difference='B-2: no lm_head adapter; Tinker uses train_unembed=True')
    return checked
