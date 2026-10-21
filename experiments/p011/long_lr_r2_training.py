"""Separate delegated LR r2 training body; no dispatch or admission is implemented here.

The complete runtime must first bind CR/A1/A2-lite, exact model/input/source
manifests, per-update cost/deadline journal and final-state storage. No resume,
retry, selection, evaluation or cloud controller is provided by this module.
"""
from collections import Counter
from contextlib import nullcontext
import math
from pathlib import Path
import random
import time

from experiments.sft_allocation_midpoint.common import digest, dump, manifest, verify
from experiments.sft_allocation_midpoint import checkpoint
from experiments.p011 import long_checkpoint

TARGETS = ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']
ARMS = {
    'S-L15': {'model_id': 'Qwen/Qwen2.5-1.5B-Instruct',
              'revision': '989aa7980e4cf806f80c7fef2b1adb7bc71aa306', 'mode': 'lora', 'peak_lr': 1e-4},
    'S-F15': {'model_id': 'Qwen/Qwen2.5-1.5B-Instruct',
              'revision': '989aa7980e4cf806f80c7fef2b1adb7bc71aa306', 'mode': 'full', 'peak_lr': 1e-5},
    'S-L3': {'model_id': 'Qwen/Qwen2.5-3B-Instruct',
             'revision': 'aa8e72537993ba99e69dfaafa59ed015b17504d1', 'mode': 'lora', 'peak_lr': 1e-4},
}


def learning_rates(updates, arm):
    """Proposed CR-bound rounding: ceil(5% U), step1-indexed cosine to10% peak."""
    if type(updates) is not int or updates < 2 or arm not in ARMS:
        raise ValueError('Valid fixed U and original smoke arm required')
    warm = max(1, math.ceil(.05 * updates))
    peak = ARMS[arm]['peak_lr']
    return [peak * step / warm if step <= warm else peak * (.1 + .9 * .5 *
            (1 + math.cos(math.pi * (step - warm) / (updates - warm))))
            for step in range(1, updates + 1)]


def compatible_frozen_rates(rates, updates, arm):
    """Validate the original saved vector without replacing any of its values."""
    if (type(rates) is not list or len(rates) != updates
            or any(type(x) is not float or not math.isfinite(x) for x in rates)):
        return False
    expected = learning_rates(updates, arm)
    tolerance = 1e-12 * ARMS[arm]['peak_lr']
    return all(abs(actual - computed) <= tolerance
               for actual, computed in zip(rates, expected))


def validate_plan(encoded, plan, rates, arm):
    if not encoded or len({r['path_id'] for r in encoded}) != len(encoded):
        raise ValueError('Nonempty unique original answer roster required')
    for r in encoded:
        ids, labels = r['input_ids'], r['labels']
        start, end = r['assistant_start'], r['assistant_end']
        if (type(ids) is not list or type(labels) is not list
                or any(type(x) is not int or not 0 <= x < 151936 for x in ids)
                or any(type(x) is not int for x in labels)
                or any(type(x) is not int for x in (start, end, r['n_supervised'], r['n_processed']))
                or not 0 < start < end <= len(ids) <= 16384
                or len(ids) != r['n_processed'] or len(labels) != len(ids)
                or labels != [-100] * start + ids[start:end] + [-100] * (len(ids) - end)
                or r['n_supervised'] != end - start or ids[end - 1] != 151645
                or r['eos_token_id'] != 151645 or r['template_final_newline_supervised'] is not False):
            raise ValueError('Original full native assistant span or strict total16384 differs')
    budget, updates = plan['supervised_tokens'], plan['optimizer_updates']
    if (type(budget) is not int or budget <= 0 or type(updates) is not int
            or updates != (budget + 63999) // 64000 or plan['seed'] != 17
            or plan['length_bucket_width'] is not None
            or plan['presentation_order'] != 'shuffled_full_passes_then_extras'
            or plan['row_path_ids'] != [r['path_id'] for r in encoded]
            or len(plan['updates']) != updates or not compatible_frozen_rates(rates, updates, arm)):
        raise ValueError('Exact source-built dose/update/order/LR vector differs')
    stream = []
    for update in plan['updates']:
        if not update or any(type(i) is not int or not 0 <= i < len(encoded) for i in update):
            raise ValueError('No empty, partial or foreign answer presentation')
        stream.extend(update)
    once = sum(r['n_supervised'] for r in encoded)
    q = budget // once
    if q < 1 or plan['q'] != q:
        raise ValueError('Every complete answer must be exposed at least once')
    for epoch in range(q):
        order = list(range(len(encoded)))
        random.Random(f'17:pass:{epoch}').shuffle(order)
        if stream[epoch * len(encoded):(epoch + 1) * len(encoded)] != order:
            raise ValueError('Whole-pass order changed before training')
    extras = stream[q * len(encoded):]
    counts = Counter(stream)
    if (len(extras) != len(set(extras)) or any(counts[i] not in (q, q + 1) for i in range(len(encoded)))
            or plan['exposures'] != [counts[i] for i in range(len(encoded))]
            or sum(encoded[i]['n_supervised'] for i in stream) != budget):
        raise ValueError('Whole-answer q/q+1 exact dose differs')
    return {'B': budget, 'U': updates, 'once_pass_tokens': once, 'q': q,
            'lr_sha256': digest(rates), 'encoded_sha256': digest(encoded), 'plan_sha256': digest(plan)}


def load_model(assets, arm):
    """Only the new long native-Instruct recipe; no old training body is called."""
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    recipe = ARMS[arm]
    if (any(assets.get(k) != recipe[k] for k in ('model_id', 'revision'))
            or not torch.cuda.is_available() or torch.cuda.device_count() != 1
            or 'H100' not in torch.cuda.get_device_name(0)
            or torch.cuda.get_device_properties(0).total_memory < 75 * 1024**3):
        raise ValueError('Pinned original arm and one H10080GB required')
    verify(assets['remote_path'], assets['files'])
    random.seed(17)
    np.random.seed(17)
    torch.manual_seed(17)
    torch.cuda.manual_seed_all(17)
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)
    tok = AutoTokenizer.from_pretrained(assets['remote_path'], local_files_only=True,
                                       trust_remote_code=False, use_fast=True)
    if tok.eos_token_id != 151645:
        raise ValueError('Native Instruct EOS differs')
    model = AutoModelForCausalLM.from_pretrained(assets['remote_path'], local_files_only=True,
            trust_remote_code=False, dtype=torch.float32, attn_implementation='sdpa').cuda()
    model.config.use_cache = False
    if recipe['mode'] == 'lora':
        from peft import LoraConfig, TaskType, get_peft_model
        model = get_peft_model(model, LoraConfig(r=64, lora_alpha=128, lora_dropout=0.,
            bias='none', target_modules=TARGETS, task_type=TaskType.CAUSAL_LM))
        if any(p.requires_grad != ('lora_' in n) for n, p in model.named_parameters()):
            raise ValueError('Unexpected adapter parameter scope')
        model.enable_input_require_grads()
    elif any(not p.requires_grad for p in model.parameters()):
        raise ValueError('Full-parameter arm cannot freeze parameters')
    if any(p.dtype != torch.float32 for p in model.parameters()):
        raise ValueError('FP32 parameters/AdamW state, BF16 autocast recipe required')
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
        lr=recipe['peak_lr'], betas=(.9, .999), eps=1e-8, weight_decay=0., foreach=False)
    return model, tok, optimizer


def accumulate(model, rows, check):
    """One unpadded complete sequence per micro-batch, token-normalized per update."""
    import torch
    from src.sft_data import shifted_loss_sum
    device = next(model.parameters()).device
    denominator = sum(r['n_supervised'] for r in rows)
    if denominator <= 0:
        raise ValueError('No supervised tokens in update')
    total = 0.
    for row in rows:
        check()
        ids = torch.tensor([row['input_ids']], dtype=torch.long, device=device)
        labels = torch.tensor([row['labels']], dtype=torch.long, device=device)
        context = torch.autocast('cuda', dtype=torch.bfloat16) if device.type == 'cuda' else nullcontext()
        with context:
            output = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False)
            loss = shifted_loss_sum(output.logits, labels)
        if not torch.isfinite(loss):
            raise ValueError('Nonfinite complete-answer loss')
        (loss / denominator).backward()
        total += loss.item()
        del ids, labels, output, loss
    return total / denominator


def train_terminal(model, tokenizer, optimizer, encoded, plan, rates, arm, out, journal, identity):
    """Caller must provide an admitted once-only journal; every step is durably bounded."""
    import torch
    proof = validate_plan(encoded, plan, rates, arm)
    if identity['arm'] != arm or identity['input_plan_sha256'] != proof['plan_sha256']:
        raise ValueError('Runtime identity differs from frozen input plan')
    out = Path(out)
    params = [p for p in model.parameters() if p.requires_grad]
    supervised, processed = 0, 0
    for step, indices in enumerate(plan['updates'], 1):
        rows = [encoded[i] for i in indices]
        intent = {'step': step, 'indices': indices, 'lr': rates[step - 1],
                  'supervised_tokens': sum(r['n_supervised'] for r in rows),
                  'processed_tokens': sum(r['n_processed'] for r in rows)}
        journal.begin(f'update_{step:05}', intent)
        journal.commit()
        model.train()
        optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        start = time.monotonic()
        loss = accumulate(model, rows, journal.check)
        norm = torch.nn.utils.clip_grad_norm_(params, 1.)
        if not torch.isfinite(norm) or not math.isfinite(loss):
            raise ValueError('Nonfinite update; preserve attempted unit, no retry')
        for group in optimizer.param_groups:
            group['lr'] = rates[step - 1]
        optimizer.step()
        torch.cuda.synchronize()
        supervised += intent['supervised_tokens']
        processed += intent['processed_tokens']
        journal.end(f'update_{step:05}', {**intent, 'loss': loss, 'gradient_norm': norm.item(),
            'seconds': time.monotonic() - start, 'cumulative_supervised': supervised,
            'cumulative_processed': processed, 'max_allocated_bytes': torch.cuda.max_memory_allocated()})
        journal.commit()
        journal.finish_update()
    if supervised != proof['B']:
        raise ValueError('Actual full dose differs')
    optimizer.zero_grad(set_to_none=True)
    journal.begin('terminal_state', proof)
    journal.commit()
    state = checkpoint.snapshot(model, optimizer, identity, proof['U'], supervised, processed, rates, plan['updates'])
    state['schema'] = 'p011_complete_training_state_v1'
    state['adaptation_mode'] = ARMS[arm]['mode']
    state['parameter_payload_meaning'] = 'all_trainable_parameters; full model for full arm, adapters for LoRA'
    state_record = long_checkpoint.save(out, state, journal.commit)
    del state
    journal.end('terminal_state', state_record)
    journal.commit()
    destination = out / 'model_for_vllm'
    journal.begin('terminal_model_export', {'mode': ARMS[arm]['mode'], 'final_state': state_record})
    journal.commit()
    model.eval()
    final = model.merge_and_unload(safe_merge=True) if ARMS[arm]['mode'] == 'lora' else model
    final = final.to(dtype=torch.bfloat16)
    destination.mkdir(exist_ok=False)
    final.save_pretrained(destination, safe_serialization=True)
    tokenizer.save_pretrained(destination)
    exported = {'relative_path': 'model_for_vllm', 'files': manifest(destination),
                'final_state': state_record, 'mode': ARMS[arm]['mode'],
                'optimizer_updates_after_terminal_state': 0, 'evaluation_performed': False}
    dump(out / 'MODEL_EXPORT.json', exported)
    journal.commit()
    journal.end('terminal_model_export', {'proof_sha256': digest(exported)})
    journal.commit()
    return {**proof, 'actual_supervised_tokens': supervised, 'actual_processed_tokens': processed,
            'terminal_state': state_record, 'model_export_sha256': digest(exported)}
