"""Original full training/state/export body; only exact engineering subset admission differs.

This is not an A/D scientific cell and cannot produce a formal cell result.
"""
from pathlib import Path
import math,time
from experiments.p011.long_training import ARMS,accumulate
from experiments.p011.long_preflight.subset import validate
from experiments.p011 import long_checkpoint
from experiments.sft_allocation_midpoint import checkpoint
from experiments.sft_allocation_midpoint.common import dump,digest,manifest

def train_terminal_subset(model, tokenizer, optimizer, encoded, plan, rates, arm, out, journal, identity):
    """Caller must provide an admitted once-only journal; every step is durably bounded."""
    import torch
    proof = validate(encoded, plan, rates, arm)
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
