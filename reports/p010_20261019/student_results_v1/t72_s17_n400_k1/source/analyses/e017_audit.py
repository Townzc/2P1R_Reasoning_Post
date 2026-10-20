"""Independent raw-prefix audit using C020, never the E017 incremental stop class."""
from collections import Counter
import math

from analyses.completion_contract import first_stop, completion_score
from analyses.gsm8k_answer_audit import score
from src.sft_data import prefix, read_jsonl


def audit_predictions(path, rows, tokenizer, cfg):
    saved = read_jsonl(path)
    if len(saved) != len(rows):
        raise ValueError('Incomplete denominator')
    vocab = len(tokenizer)
    decode = lambda ids: tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    for start in range(0, len(rows), cfg['eval_batch_size']):
        part = saved[start:start+cfg['eval_batch_size']]
        width = max(len(tokenizer(prefix(r['prompt']), add_special_tokens=False)['input_ids'])
                    for r in rows[start:start+cfg['eval_batch_size']])
        steps = max(r['generated_tokens'] for r in part)
        for row, record in zip(rows[start:start+cfg['eval_batch_size']], part):
            if any(record.get(k) != v for k,v in row.items()):
                raise ValueError('Row identity, prompt or reference differs')
            full, ids = record['batch_output_ids'], record['generated_ids']
            if (not ids or any(type(t) is not int or t < 0 for t in full)
                    or record['generated_tokens'] != len(ids) or full[:len(ids)] != ids
                    or len(full) != steps or record['batch_generated_steps'] != steps
                    or record['post_stop_padding_tokens'] != steps-len(ids)
                    or record['batch_index'] != start//cfg['eval_batch_size'] or record['padded_prompt_width'] != width
                    or width+steps > cfg['max_length']
                    or any(t != tokenizer.eos_token_id for t in full[len(ids):])):
                raise ValueError('Raw prefix/batch/padding metadata differs')
            special = set(tokenizer.all_special_ids) | {t for t in full if t >= vocab}
            event = first_stop(full, decode, tokenizer.eos_token_id, cfg['max_new_tokens'], special)
            if event != record['stop'] or event['retained_tokens'] != len(ids):
                raise ValueError('Independent first-stop event differs')
            visible = ids[:-1] if event['actual_eos_at_stop'] else ids
            text = tokenizer.decode(visible[:-1] if visible and visible[-1] >= vocab else visible,
                                    skip_special_tokens=False, clean_up_tokenization_spaces=False)
            if visible and visible[-1] >= vocab:
                text += f'<|invalid_token_id_{visible[-1]}|>'
            if (record['raw_text'] != text or record['task_score'] != completion_score(row,event)
                    or record['legacy_marked_prefix_score'] != score(row,text,event['actual_eos_at_stop'],event['stop_reason']=='length_cap')):
                raise ValueError('Rendered text or score differs from raw tokens')
            seconds = record['generation_batch_seconds']
            if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds <= 0 or seconds != part[0]['generation_batch_seconds']:
                raise ValueError('Invalid shared batch timing')
    return saved


def decisions(predictions, cfg):
    gate = cfg['usability_screen']
    if len(predictions) != gate['n']:
        raise ValueError('No decision from incomplete output')
    reasons = Counter(r['stop']['stop_reason'] for r in predictions)
    parsed = Counter(r['task_score']['marked']['status'] for r in predictions)
    correct = sum(r['task_score']['task_answer_correct'] for r in predictions)
    invalid = reasons.get('invalid_special_token',0)
    false_eos = sum(r['stop']['actual_eos_at_stop'] != (r['stop']['stop_reason']=='native_eos') for r in predictions)
    passed = (parsed.get('parsed',0)>=gate['minimum_parsed'] and correct>=gate['minimum_task_answer_correct']
              and reasons.get('length_cap',0)<=gate['maximum_actual_length_cap_stops']
              and invalid==0 and false_eos==0)
    batch_max = sum(r['batch_generated_steps'] for i,r in enumerate(predictions) if i%cfg['eval_batch_size']==0)
    return {'n':len(predictions), 'parse_status':dict(parsed), 'stop_reasons':dict(reasons),
            'task_answer_correct':correct, 'native_eos_correct':sum(r['task_score']['native_eos_correct'] for r in predictions),
            'legacy_marked_prefix_clean_correct':sum(r['legacy_marked_prefix_score']['clean_correct'] for r in predictions),
            'invalid_stop_records':invalid, 'false_native_eos_records':false_eos,
            'retained_generated_tokens':sum(r['generated_tokens'] for r in predictions),
            'padded_batch_output_tokens':sum(r['batch_generated_steps'] for r in predictions),
            'batch_maximum_lengths_sum':batch_max, 'operational_usability_passed':passed,
            'scientific_grid_authorized':False, 'automatic_training_authorized':False,
            'interpretation':'Observed-development implementation calibration; not fresh confirmation, proof validation or a revised E016 score.'}
