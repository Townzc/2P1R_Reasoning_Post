"""Fixed posthoc forced-answer protocol; original labels/weights remain immutable."""
from decimal import Decimal, ROUND_FLOOR
import zlib
from experiments.p011.owner_0205_common import digest
from experiments.sft_allocation_midpoint.common import digest as original_digest

SUFFIX = '\n</think>\n\nFinal answer: \\boxed{'
CELLS = ('baseline', 'A1r2', 'A5', 'A6', 'A7', 'D1', 'D2')
CONTRASTS = (('A1r2','A7'), ('A1r2','A6'), ('A1r2','A5'), ('A5','A7'), ('D1','D2'))


def expected_math_ids():
    return {f'math500:{i:04d}:{mode}:{seed}' for i in range(500)
            for mode, seeds in [('sample',range(4)),('greedy',[0])] for seed in seeds}


def loop_heuristic(saved_decoded_text):
    # Explicit implementation for CR: character suffix, UTF-8 byte denominator.
    tail = saved_decoded_text[-6000:].encode('utf-8')
    ratio = len(zlib.compress(tail)) / len(tail) if tail else None
    return {'compression_ratio':ratio, 'loop':ratio is not None and ratio < .12,
            'last_characters':6000, 'threshold':.12, 'descriptive_only':True}


def forced_request(raw, decoded, suffix_ids):
    if (raw['id'] != decoded['id'] or len(raw['answers']) != 1
            or decoded['raw_record_sha256'] != original_digest(raw)
            or raw['answers'][0]['finish_reason'] != 'length'
            or decoded['backend_finish_reason'] != 'length'
            or decoded['stop_reason'] not in ('length_cap','native_eos','invalid_special_token')
            or len(raw['answers'][0]['token_ids']) != 16384):
        raise ValueError('Exactly the original verified backend-length16384 row required')
    prompt, generated = raw['prompt_token_ids'], raw['answers'][0]['token_ids']
    if any(type(t) is not int or t < 0 for ids in (prompt, generated, suffix_ids) for t in ids):
        raise ValueError('Literal native token IDs only')
    return {'id':raw['id'], 'prompt_token_ids':prompt + generated + suffix_ids,
            'original_raw_record_sha256':original_digest(raw), 'original_request_sha256':raw['request_sha256'],
            'original_prompt_ids_sha256':digest(prompt), 'original_generated_ids_sha256':digest(generated),
            'original_prompt_tokens':len(prompt), 'original_generated_tokens':16384,
            'suffix_ids_sha256':digest(suffix_ids)}


def checked_budget(budget, now):
    """One shared GPU attempt, seven sequential cells, at most $12 total reserve."""
    reserve, noncompute = Decimal('12'), Decimal('1.50')
    rate = Decimal(budget['hourly_rate_usd'])
    prior = Decimal(budget['new_epoch_observed_tagged_cost_usd'])
    delayed = Decimal(budget['prior_unattributed_cost_allowance_usd'])
    if (not 0 <= now-budget['observed_epoch'] <= 3600 or rate <= 0 or prior < 0
            or delayed < Decimal('20.02') or prior+delayed+reserve > Decimal('150')
            or budget['active_or_pending_or_unknown_model_slots'] >= 8
            or budget['new_task_reserve_usd'] != '12'
            or budget['all_prior_attempts_terminal'] is not True):
        raise ValueError('Fresh remaining P011 budget or eight-slot contract failed')
    # 600s startup + 60s platform grace are costed too. 3h is an upper bound,
    # not permission to reserve more than $12 at the authenticated resource rate.
    seconds = min(10800, int(((reserve-noncompute)*3600/rate).to_integral_value(rounding=ROUND_FLOOR))-660)
    if seconds < 3600:
        raise ValueError('Less than one hour fits the authorized cost envelope; report without dispatch')
    return {'worker_hard_seconds':seconds, 'maximum_worker_seconds':10800,
            'startup_seconds':600, 'platform_grace_seconds':60,
            'compute_upper_usd':str(rate*Decimal(seconds+660)/3600),
            'new_noncompute_allowance_usd':str(noncompute), 'new_reserve_usd':'12',
            'epoch_accounted_upper_after_usd':str(prior+delayed+reserve),
            'actual_invoice_claimed':False, 'automatic_retry':False}


def joined_labels(original, forced, selected_ids):
    if set(original) != expected_math_ids() or set(forced) != set(selected_ids):
        raise ValueError('All original MATH rows and exactly all selected forced rows required')
    if not set(selected_ids) <= set(original) or any(type(x) is not bool for x in list(original.values())+list(forced.values())):
        raise ValueError('Missing/unknown correctness cannot become zero')
    return {k:forced[k] if k in selected_ids else v for k,v in original.items()}


def question_vectors(labels, mode):
    if set(labels) != expected_math_ids() or mode not in ('sample','greedy'):
        raise ValueError('Complete MATH label vector required')
    return {f'math500:{i:04d}':([labels[f'math500:{i:04d}:sample:{s}'] for s in range(4)]
            if mode=='sample' else [labels[f'math500:{i:04d}:greedy:0']]*4) for i in range(500)}


def forced_sampling(eos):
    return {'n':1,'temperature':0.,'top_p':1.,'top_k':-1,'repetition_penalty':1.,'seed':17,
            'max_tokens':64,'stop':None,'stop_token_ids':list(eos),'ignore_eos':False,
            'detokenize':True,'skip_special_tokens':False,'include_stop_str_in_output':True}


def decode_continuation(request, item, eos, tokenizer, vocab_size):
    """Original native EOS/special/cap semantics, with the new explicit64 cap.

    Only new continuation IDs are decoded; the original16384 IDs are never
    decoded again. The original primary labels are not inputs to this oracle.
    """
    if (item['id']!=request['id'] or item['request_sha256']!=digest(request)
            or item['prompt_token_ids']!=request['prompt_token_ids']
            or item['sampling']!=forced_sampling(eos) or len(item['answers'])!=1):
        raise ValueError('Exact new continuation identity/sampling required')
    answer=item['answers'][0];ids=answer['token_ids']
    if (not ids or len(ids)>64 or any(type(t) is not int or not 0<=t<vocab_size for t in ids)
            or not isinstance(answer['backend_text'],str)):
        raise ValueError('Complete native continuation required')
    specials=set(tokenizer.all_special_ids)-set(eos)
    terminal=next(((i,'native_eos' if t in eos else 'invalid_special_token')
                   for i,t in enumerate(ids) if t in eos or t in specials),None)
    unknown=sorted(set(ids)-set(tokenizer.get_vocab().values()))
    if terminal:
        index,stop=terminal
        if stop=='native_eos' and (index!=len(ids)-1 or answer['finish_reason'] not in ('stop','length')):
            raise ValueError('Native stop is not terminal')
        if unknown:raise ValueError('Unmapped token before completed stop')
        visible=ids[:index]
    else:
        if len(ids)!=64 or answer['finish_reason']!='length':
            raise ValueError('Partial continuation is unknown, never zero')
        stop,visible='length_cap',ids
    text=tokenizer.decode(visible,skip_special_tokens=False,clean_up_tokenization_spaces=False)
    return {'id':request['id'],'request_sha256':digest(request),'stop_reason':stop,
        'continuation_text':text,'answer_segment':'\\boxed{'+text,'generated_tokens':len(ids),
        'unmapped_model_token_ids':unknown,'raw_record_sha256':digest(item),
        'backend_text_sha256':digest(answer['backend_text']),
        'backend_finish_reason':answer['finish_reason'],'backend_stop_reason':answer['stop_reason']}
