"""Prepared A/D native-chat requests and sole permitted P1 text adaptation.

No vLLM/model/scorer calls occur here. Complete runtime CR must bind the
original benchmark rows, tokenizer/config, source and budget before use.
"""
from collections import Counter
import unicodedata
from experiments.sft_allocation_midpoint.common import digest

BENCHMARK_COUNTS = {'math500': 500, 'aime24': 30, 'aime25': 30, 'amc23': 40}
MAX_NEW_TOKENS = 16384


def request_roster(benchmarks, tokenizer):
    if Counter(r['benchmark'] for r in benchmarks) != Counter(BENCHMARK_COUNTS):
        raise ValueError('Exactly the four original full benchmarks required')
    requests, seen = [], set()
    for row in benchmarks:
        benchmark, index = row['benchmark'], row['source_row']
        if type(index) is not int or not 0 <= index < BENCHMARK_COUNTS[benchmark]:
            raise ValueError('Original source row missing or out of range')
        pid = f'{benchmark}:{index:04d}'
        if pid in seen or not isinstance(row['answer'], str) or not row['answer'].strip():
            raise ValueError('Duplicate endpoint or unsupported gold cannot be silently dropped')
        seen.add(pid)
        messages = [{'role': 'user', 'content': row['problem']}]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        tokens = tokenizer(text, add_special_tokens=False)['input_ids']
        normalized=tokenizer.backend_tokenizer.normalizer.normalize_str(text)
        if (normalized!=unicodedata.normalize('NFC',text)
                or tokenizer.decode(tokens,skip_special_tokens=False,clean_up_tokenization_spaces=False)!=normalized):
            raise ValueError('Pinned native NFC-only prompt roundtrip differs; no cleanup/truncation')
        if not tokens or any(type(t) is not int or t < 0 for t in tokens):
            raise ValueError('Original complete native prompt token IDs required')
        # Context size is selected and reviewed from the actual longest prompt;
        # no truncation or unreviewed context policy is introduced here.
        modes = [('sample', s) for s in range(4 if benchmark == 'math500' else 8)]
        if benchmark == 'math500':
            modes.append(('greedy', 0))
        for mode, seed in modes:
            requests.append({'id': f'{pid}:{mode}:{seed}', 'problem_id': pid,
                'benchmark': benchmark, 'source_row': index, 'mode': mode, 'seed': seed,
                'prompt_token_ids': tokens, 'prompt_text_sha256': digest(normalized), 'raw_prompt_text_sha256':digest(text),
                'native_NFC_changed':text!=normalized,
                'gold': row['answer'], 'required_context': len(tokens) + MAX_NEW_TOKENS})
    return requests


def sampling(request, model_eos_ids):
    if (request['mode'] not in ('sample', 'greedy') or not model_eos_ids
            or len(model_eos_ids) != len(set(model_eos_ids))
            or 151645 not in model_eos_ids or any(type(i) is not int for i in model_eos_ids)):
        raise ValueError('Native model-pinned EOS IDs and exact endpoint mode required')
    greedy = request['mode'] == 'greedy'
    return {'n': 1, 'temperature': 0. if greedy else .6, 'top_p': 1. if greedy else .95,
            'top_k': -1, 'repetition_penalty': 1., 'seed': request['seed'],
            'max_tokens': MAX_NEW_TOKENS, 'stop': None, 'stop_token_ids': list(model_eos_ids),
            'ignore_eos': False, 'detokenize': True, 'skip_special_tokens': False,
            'include_stop_str_in_output': True}


def answer_region(text):
    if not isinstance(text, str):
        raise ValueError('Complete decoded output required')
    return text.rsplit('</think>', 1)[-1] if '</think>' in text else text


def scoring_rows(requests, verified_outputs):
    """Only a full raw oracle may supply outputs; never silently score unknowns."""
    ids = [r['id'] for r in requests]
    if len(ids) != len(set(ids)) or set(verified_outputs) != set(ids):
        raise ValueError('Exact complete request/output roster required')
    result = []
    for r in requests:
        o = verified_outputs[r['id']]
        if (o.get('request_sha256') != digest(r) or o.get('id') != r['id']
                or o.get('stop_reason') not in ('native_eos', 'length_cap', 'invalid_special_token')):
            raise ValueError('Unknown stop or foreign output; reconcile instead of scoring zero')
        text = o['answer_text']
        region = answer_region(text)
        result.append({'id': r['id'], 'gold': r['gold'], 'answer_segment': region,
                       'stop_reason': o['stop_reason'], 'request_sha256': digest(r),
                       'raw_text_sha256': digest(text), 'last_think_boundary_present': '</think>' in text,
                       'region_sha256': digest(region)})
    # The unchanged journal/pool/scalar applies last_box to answer_segment;
    # length_cap remains incorrect irrespective of an apparently correct box.
    return result


def paired_question_interval(left, right):
    """CR-candidate: full per-question sample averages, paired question resampling."""
    import numpy as np
    if (set(left) != set(right) or len(left) != 500
            or any(len(v) != 4 or any(type(x) is not bool for x in v)
                   for group in (left, right) for v in group.values())):
        raise ValueError('Two full MATH500 sets of four frozen Boolean outcomes required')
    ids = sorted(left)
    differences = np.asarray([sum(right[k])/4 - sum(left[k])/4 for k in ids], dtype=np.float64)
    rng = np.random.default_rng(20261021)
    # Fixed batch1000 only limits memory; same generator stream/order is retained.
    resampled = np.concatenate([differences[rng.integers(0, 500, size=(1000, 500))].mean(axis=1)
                                for _ in range(10)])
    low, high = np.quantile(resampled, [.025, .975], method='linear')
    return {'difference_pp': float(differences.mean()*100), 'ci95_pp': [float(low*100), float(high*100)],
            'unit': 'paired_question_mean_of_four', 'questions': 500, 'resamples': 10000,
            'seed': 20261021, 'quantile_method': 'linear', 'question_order_sha256': digest(ids),
            'training_seed_population_claim': False}
