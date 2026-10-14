"""Exact original batch validator with the independently reviewed vocabulary cache."""
import math
from analyses.completion_contract import completion_score
from analyses.gsm8k_answer_audit import score
from scripts.exploratory_reference_vocab_cache_proposal import reference_event_cached as reference_event

def audit_batch(raw, records, rows, prompts, tok, eos_ids):
    if (len(records) != len(rows) or len(raw['batch_output_ids']) != len(rows) or
            len(prompts) != len(rows) or len(raw['events']) != len(rows)):
        raise ValueError('Incomplete original batch')
    ids = [p['input_ids'] for p in prompts]
    width = max(map(len, ids))
    if raw['input_ids'] != ids or raw['prompt_width'] != width or raw['problem_ids'] != [r['problem_id'] for r in rows]:
        raise ValueError('Frozen prompts/identities differ')
    steps = len(raw['batch_output_ids'][0])
    if not 0 < steps <= 512 or width + steps > 2048:
        raise ValueError('Generation/context cap differs')
    for row, p, tokens, record, event in zip(rows,prompts,raw['batch_output_ids'],records,raw['events']):
        if p['problem_id'] != row['problem_id'] or any(record.get(k)!=v for k,v in row.items()):
            raise ValueError('Original endpoint row differs')
        if len(tokens)!=steps or any(type(t)is not int or t<0 for t in tokens):
            raise ValueError('Raw output shape differs')
        expected=reference_event(tokens,tok,eos_ids);n=expected['retained_tokens']
        if event!=expected or record['stop']!=expected or any(t!=tok.eos_token_id for t in tokens[n:]):
            raise ValueError('Independent native stop/padding differs')
        visible=tokens[:n-1] if expected['actual_eos_at_stop'] else tokens[:n]
        text=tok.decode(visible,skip_special_tokens=False,clean_up_tokenization_spaces=False)
        if (record['generated_ids']!=tokens[:n] or record['batch_output_ids']!=tokens or
                record['generated_tokens']!=n or record['raw_text']!=text or
                record['batch_generated_steps']!=steps or record['post_stop_padding_tokens']!=steps-n or
                record['padded_prompt_width']!=width or
                record['generation_batch_seconds']!=raw['seconds'] or
                record['task_score']!=completion_score(row,expected) or
                record['legacy_marked_prefix_score']!=score(row,text,expected['actual_eos_at_stop'],expected['stop_reason']=='length_cap')):
            raise ValueError('Raw/score correspondence differs')
        if not math.isfinite(raw['seconds']) or raw['seconds']<=0:
            raise ValueError('Invalid actual batch duration')
        if expected['stop_reason']=='length_cap' and record['task_score']['task_answer_correct']:
            raise ValueError('Capped completion cannot be counted correct')
    return True
