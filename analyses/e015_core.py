"""Isolated E015 training intervention and vectorized reference measurements."""
import json
import math
import time

from analyses.e014 import reference_measurement, token_hash
from src.relation_experiment import accumulate_gradients


def terminal_lr(step):
    if type(step) is not int or not 1 <= step <= 256:
        raise ValueError('E015 requires integer update indices 1 through 256')
    return 5e-5 if step <= 192 else 5e-5 * (1 + math.cos(math.pi * (step - 192) / 64)) / 2


def make_cases(train, encoded):
    if len(train) != len(encoded):
        raise ValueError('Train/encoding cardinality differs')
    cases = []
    for i, (row, enc) in enumerate(zip(train, encoded)):
        if row['problem_id'] != enc['problem_id']:
            raise ValueError('Train/encoding order differs')
        prompt, target = enc['input_ids'][:enc['n_prompt']], enc['input_ids'][enc['n_prompt']:]
        if not prompt or not target or enc['labels'] != [-100] * len(prompt) + target:
            raise ValueError('Exact prompt mask/target serialization required')
        cases.append({'problem_id': row['problem_id'], 'row_index': i,
                      'selected_for_batch1': False, 'prompt_ids': prompt, 'target_ids': target,
                      'prompt_ids_sha256': token_hash(prompt), 'target_ids_sha256': token_hash(target)})
    return cases


def reference_record(logits, case):
    """Reference-conditioned full forward; never interpret as generated-prefix EOS."""
    import torch
    record = reference_measurement(logits, case, [
        {'kind': 'reference_eos', 'target_position': len(case['target_ids']) - 1, 'alternative_id': None}])
    n_prompt, n_target = len(case['prompt_ids']), len(case['target_ids'])
    shifted = logits[n_prompt - 1:n_prompt + n_target - 1].detach().float()
    if shifted.shape[-1] < 2 or not torch.isfinite(shifted).all():
        raise ValueError('At least two finite vocabulary logits required')
    target = torch.tensor(case['target_ids'], device=shifted.device)
    target_logits = shifted.gather(1, target[:, None])[:, 0]
    top_values, top_ids = shifted.topk(2, dim=-1)
    best_other = torch.where(top_ids[:, 0] == target, top_values[:, 1], top_values[:, 0])
    record.update(
        argmax_log_probability=torch.log_softmax(shifted, dim=-1).max(dim=-1).values.tolist(),
        target_minus_argmax_logit=(target_logits - top_values[:, 0]).tolist(),
        target_minus_best_other_logit=(target_logits - best_other).tolist())
    return record


def train_updates(model, optimizer, encoded, schedule, cfg, pad_id, log, history, device='cuda'):
    """Same E013 update operations, with an explicit LR set before optimizer.step.

    CPU support is only for tiny random-model correctness fixtures. A caller-
    owned history preserves completed updates if a later update is interrupted.
    """
    import torch
    cuda = str(device).startswith('cuda')
    for step, indices in enumerate(schedule, 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        if cuda:
            torch.cuda.synchronize()
        tick = time.perf_counter()
        rows = [encoded[i] for i in indices]
        nll = accumulate_gradients(model, rows, pad_id, cfg['microbatch_size'], device)
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), cfg['grad_clip'])
        if not torch.isfinite(norm):
            raise FloatingPointError('Nonfinite gradient')
        for group in optimizer.param_groups:
            group['lr'] = terminal_lr(step)
        actual = [group['lr'] for group in optimizer.param_groups]
        if not actual or len(set(actual)) != 1:
            raise ValueError('All optimizer groups must use the same actual LR')
        optimizer.step()
        if cuda:
            torch.cuda.synchronize()
        record = {'step': step, 'actual_learning_rate': actual[0], 'row_indices': list(indices),
                  'response_nll': nll, 'grad_norm': norm.item(),
                  'supervised_tokens': sum(r['n_supervised'] for r in rows),
                  'processed_tokens': sum(r['n_processed'] for r in rows),
                  'seconds': time.perf_counter() - tick,
                  'peak_allocated_mib': torch.cuda.max_memory_allocated() / 1024**2 if cuda else 0,
                  'peak_reserved_mib': torch.cuda.max_memory_reserved() / 1024**2 if cuda else 0}
        history.append(record)
        log.write(json.dumps(record, allow_nan=False) + '\n')
        log.flush()
        if step == 1 or step % 32 == 0:
            print(json.dumps(record), flush=True)
    return history
