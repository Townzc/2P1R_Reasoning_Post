"""Incremental per-row stopping for E017; no gold or answer scoring in the stop path."""
import json
from pathlib import Path
import time

import torch
from transformers import GenerationConfig, StoppingCriteria, StoppingCriteriaList

from analyses.gsm8k_answer_audit import BOUNDARY, score
from analyses.completion_contract import completion_score
from src.sft_data import prefix


def decoded(tokenizer, ids, skip_special_tokens=True):
    return tokenizer.decode(ids, skip_special_tokens=skip_special_tokens,
                            clean_up_tokenization_spaces=False)


class TaskBoundaryStop(StoppingCriteria):
    """One Boolean per original batch row; never compact or manufacture an EOS.

    Inspect only the newly extended generated prefix. The independent auditor
    scans prefixes with the separately published C020 oracle after generation.
    """
    def __init__(self, tokenizer, prompt_width, batch_size, max_new_tokens):
        if min(prompt_width, batch_size, max_new_tokens) <= 0:
            raise ValueError('Positive prompt width, batch size and cap required')
        self.tokenizer = tokenizer
        self.prompt_width = prompt_width
        self.batch_size = batch_size
        self.cap = max_new_tokens
        self.vocab_size = len(tokenizer)
        self.eos = tokenizer.eos_token_id
        self.special = set(tokenizer.all_special_ids) - {self.eos}
        self.events = [None] * batch_size
        self.steps = 0

    def __call__(self, input_ids, scores, **kwargs):
        count = input_ids.shape[1] - self.prompt_width
        if input_ids.shape[0] != self.batch_size or count != self.steps + 1 or count > self.cap:
            raise ValueError('Fixed batch and sequential one-token generation required')
        self.steps = count
        generated = input_ids[:, self.prompt_width:].tolist()
        for i, ids in enumerate(generated):
            if self.events[i] is not None:
                if ids[-1] != self.eos:
                    raise ValueError('Finished row was not padded with the declared pad token')
                continue
            last = ids[-1]
            invalid = last in self.special or not 0 <= last < self.vocab_size
            if last == self.eos or invalid:
                reason = 'native_eos' if last == self.eos else 'invalid_special_token'
                segment = decoded(self.tokenizer, ids[:-1])
                boundary = None
            else:
                text = decoded(self.tokenizer, ids)
                boundary = BOUNDARY.search(text)
                reason = 'new_problem_boundary' if boundary else 'length_cap' if count == self.cap else None
                segment = text[:boundary.start()] if boundary else text
            if reason:
                self.events[i] = {'stop_reason': reason, 'retained_tokens': count,
                    'actual_eos_at_stop': reason == 'native_eos', 'answer_segment': segment,
                    'boundary_offset': boundary.start() if boundary else None,
                    'trigger_text': boundary.group() if boundary else None}
        return torch.tensor([e is not None for e in self.events], device=input_ids.device, dtype=torch.bool)


def prediction(row, tokenizer, output_ids, event, batch_seconds, batch_index, prompt_width):
    """Store exact prefix and full padded output; only the former is model completion."""
    if event is None:
        raise ValueError('No recorded stop event')
    count = event['retained_tokens']
    tokens = output_ids[:count]
    if not tokens or any(t != tokenizer.eos_token_id for t in output_ids[count:]):
        raise ValueError('Invalid prefix or post-stop batch padding')
    raw = tokens[:-1] if event['actual_eos_at_stop'] else tokens
    vocab = len(tokenizer)
    if any(not 0 <= t < vocab for t in raw):
        text = decoded(tokenizer, raw[:-1], False) + f'<|invalid_token_id_{raw[-1]}|>'
    else:
        text = decoded(tokenizer, raw, False)
    return {**row, 'raw_text': text, 'generated_ids': tokens, 'generated_tokens': count,
            'batch_output_ids': output_ids, 'batch_generated_steps': len(output_ids),
            'post_stop_padding_tokens': len(output_ids)-count,
            'batch_index': batch_index, 'padded_prompt_width': prompt_width,
            'generation_batch_seconds': batch_seconds, 'stop': event,
            'task_score': completion_score(row, event),
            'legacy_marked_prefix_score': score(row, text, event['actual_eos_at_stop'],
                                               event['stop_reason'] == 'length_cap')}


def generate(model, tokenizer, rows, cfg, path):
    model.eval()
    settings = GenerationConfig(do_sample=False, num_beams=1, max_new_tokens=cfg['max_new_tokens'],
        eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.eos_token_id, use_cache=True)
    predictions = []
    with Path(path).open('x', encoding='utf-8') as f:
        for start in range(0, len(rows), cfg['eval_batch_size']):
            part = rows[start:start+cfg['eval_batch_size']]
            ids = [tokenizer(prefix(r['prompt']), add_special_tokens=False)['input_ids'] for r in part]
            width = max(map(len, ids))
            if width + cfg['max_new_tokens'] > cfg['max_length']:
                raise ValueError('Context cap exceeded; never truncate or filter')
            inputs = torch.tensor([[tokenizer.eos_token_id]*(width-len(x))+x for x in ids], device='cuda')
            masks = torch.tensor([[0]*(width-len(x))+[1]*len(x) for x in ids], device='cuda')
            stopper = TaskBoundaryStop(tokenizer, width, len(part), cfg['max_new_tokens'])
            tick = time.perf_counter()
            with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
                output = model.generate(input_ids=inputs, attention_mask=masks, generation_config=settings,
                                        stopping_criteria=StoppingCriteriaList([stopper]))
            torch.cuda.synchronize()
            seconds = time.perf_counter()-tick
            if not torch.equal(output[:, :width], inputs):
                raise ValueError('Generation changed the prompt prefix')
            outputs = output[:, width:].tolist()
            if any(e is None for e in stopper.events) or max(e['retained_tokens'] for e in stopper.events) != len(outputs[0]):
                raise ValueError('Batch stopped early or continued after every row stopped')
            for row, tokens, event in zip(part, outputs, stopper.events):
                result = prediction(row, tokenizer, tokens, event, seconds, start//cfg['eval_batch_size'], width)
                predictions.append(result)
                f.write(json.dumps(result, ensure_ascii=False, allow_nan=False)+'\n'); f.flush()
            print(json.dumps({'evaluation': Path(path).name, 'completed_prompts': len(predictions),
                              'batch_seconds': seconds}), flush=True)
            del inputs, masks, output
    return predictions
