"""C1 leaf functions for exact-token, forward-only NLL; NOT runtime admission.

No tokenizer, optimizer, generator, adapter, network or automatic retry. A future
reviewed entry must bind the original input files, base-weight manifest, budget,
deadline and once-only journal before using these functions on real inputs.
"""
import math

from experiments.sft_allocation_midpoint.common import digest

MODEL = {'model_id': 'Qwen/Qwen2.5-1.5B',
         'revision': '8faed761d45a263340a0528343f099c05c9a4323'}
QUANTILES = (0., .1, .25, .5, .75, .9, 1.)


def checked_sequence(row):
    """The original P010 answer span, including its original terminal EOS."""
    ids, labels = row['input_ids'], row['labels']
    n, prompt, count = row['n_processed'], row['n_prompt'], row['n_supervised']
    if (type(ids) is not list or type(labels) is not list
            or any(type(x) is not int or x < 0 or x >= 151936 for x in ids)
            or any(type(x) is not int for x in labels)
            or any(type(x) is not int for x in (n, prompt, count))
            or n != len(ids) or len(labels) != n or not 1 <= prompt < n <= 2048
            or count != n - prompt or count <= 0
            or labels != [-100] * prompt + ids[prompt:]
            or ids[-1] != 151643 or ids[prompt:].count(151643) != 1):
        raise ValueError('Exact complete original answer/mask/EOS required')
    return {'sequence_sha256': digest({'input_ids': ids, 'labels': labels}),
            'target_positions': list(range(prompt, n)), 'supervised_tokens': count}


def inventory(groups):
    """Validate six original groups; merge only literally identical token/mask pairs.

    Hash reuse is about identical conditional probabilities under the same base,
    not equality of teacher text or problem IDs. Each original answer keeps its
    separate group membership and fallback flag. No original exposure schedule
    is applied: C1 describes each saved complete answer once in its own group.
    """
    expected = {f'{teacher}_n{n}' for teacher in ('t15', 't7', 't72') for n in (400, 3200)}
    if set(groups) != expected:
        raise ValueError('C1 requires exactly original three teachers x two sample sizes')
    unique, memberships = {}, {}
    for name in sorted(expected):
        obj = groups[name]
        teacher, ntext = name.split('_n')
        n = int(ntext)
        config, rows, encoded = obj['config'], obj['rows'], obj['encoded']
        if (len(rows) != n or len(encoded) != n or config['n'] != n
                or config['seed'] != 17 or config['updates'] != 1024
                or config['targets'] != 2097148
                or any(config['model'].get(k) != v for k, v in MODEL.items())
                or config['encoded_rows_sha256'] != digest(encoded)
                or config['training_rows_sha256'] != digest(rows)
                or len({r['problem_id'] for r in rows}) != n):
            raise ValueError('Original input/config identity or counts changed')
        members = []
        for row, enc in zip(rows, encoded):
            if any(row[k] != enc[k] for k in ('path_id', 'problem_id')):
                raise ValueError('Encoded/source order or identity differs')
            if teacher == 't15':
                if row['attempt'] != 1 or row.get('unverified_fallback', False) is not False:
                    raise ValueError('Inherited T15 S1 consists of original usable attempt01 only')
                fallback = False
            else:
                fallback = row['unverified_fallback']
                if (type(fallback) is not bool or row['teacher'] != teacher
                        or type(row['attempt']) is not int or not 1 <= row['attempt'] <= 4
                        or (fallback and row['attempt'] != 1)):
                    raise ValueError('Original teacher/retry/fallback metadata differs')
            check = checked_sequence(enc)
            key = check['sequence_sha256']
            task = {'input_ids': enc['input_ids'], 'labels': enc['labels'], **check}
            if key in unique and unique[key] != task:
                raise ValueError('Different exact sequences share the same identity')
            unique.setdefault(key, task)
            members.append({'path_id': row['path_id'], 'problem_id': row['problem_id'],
                            'sequence_sha256': key, 'unverified_fallback': fallback,
                            'original_row_sha256': digest(row),
                            'original_encoded_row_sha256': digest(enc)})
        memberships[name] = members
    for teacher in ('t15', 't7', 't72'):
        if memberships[teacher + '_n3200'][:400] != memberships[teacher + '_n400']:
            raise ValueError('Original within-teacher n400 must nest exactly in n3200')
    return unique, memberships


def forward_one(model, task):
    """One teacher-forced forward; position j is predicted by logits at j-1.

    The model must already be the verified untouched base in eval mode. FP32
    cross-entropy is computed on selected BF16 logits. The returned token vector
    preserves the original supervised order and includes the original EOS.
    """
    import torch
    import torch.nn.functional as F
    if model.training or getattr(model, 'peft_config', None):
        raise ValueError('Untouched base in eval mode required; no LoRA/training')
    key = digest({'input_ids': task['input_ids'], 'labels': task['labels']})
    positions = [i for i, label in enumerate(task['labels']) if label != -100]
    if (key != task['sequence_sha256'] or positions != task['target_positions']
            or not positions or positions[0] == 0
            or len(positions) != task['supervised_tokens']):
        raise ValueError('Frozen task span changed')
    device = next(model.parameters()).device
    with torch.inference_mode():
        tokens = torch.tensor([task['input_ids']], dtype=torch.long, device=device)
        mask = torch.ones_like(tokens)
        result = model(input_ids=tokens, attention_mask=mask, use_cache=False, return_dict=True)
        logits = result.logits
        if logits.ndim != 3 or tuple(logits.shape[:2]) != tuple(tokens.shape):
            raise ValueError('Causal model returned unexpected logits structure')
        indices = torch.tensor(positions, dtype=torch.long, device=device)
        losses = F.cross_entropy(logits[0, indices - 1, :].float(),
                                 tokens[0, indices], reduction='none')
        values = losses.double().cpu().tolist()
    if len(values) != len(positions) or any(not math.isfinite(x) or x < 0 for x in values):
        raise ValueError('Nonfinite or incomplete token NLL; never fill missing values')
    return {'sequence_sha256': key, 'supervised_tokens': len(values),
            'target_positions': positions, 'token_nll': values,
            'nll_sum': math.fsum(values), 'mean_nll': math.fsum(values) / len(values)}


def linear_quantile(values, q):
    if not values or not 0 <= q <= 1:
        raise ValueError('Nonempty descriptive quantile required')
    ordered = sorted(values)
    at = (len(ordered) - 1) * q
    low, high = math.floor(at), math.ceil(at)
    return ordered[low] + (ordered[high] - ordered[low]) * (at - low)


def descriptive_summary(memberships, confirmed):
    """Only complete confirmed vectors; no bootstraps/tests/zero-filled failures."""
    needed = {r['sequence_sha256'] for rows in memberships.values() for r in rows}
    if set(confirmed) != needed:
        raise ValueError('Complete exact roster required before any aggregate')
    for key, obj in confirmed.items():
        vals = obj['token_nll']
        if (obj['sequence_sha256'] != key or not vals or len(vals) != obj['supervised_tokens']
                or any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in vals)
                or obj['nll_sum'] != math.fsum(vals)
                or obj['mean_nll'] != math.fsum(vals) / len(vals)):
            raise ValueError('Invalid saved token NLL vector')
    def subset(rows):
        if not rows:
            return {'answers': 0, 'supervised_tokens': 0, 'token_weighted_nll': None,
                    'perplexity': None, 'answer_mean_nll_quantiles': None}
        records = [confirmed[x['sequence_sha256']] for x in rows]
        count = sum(x['supervised_tokens'] for x in records)
        mean = math.fsum(x['nll_sum'] for x in records) / count
        try:
            perplexity = math.exp(mean)
        except OverflowError:
            perplexity = None
        return {'answers': len(rows), 'supervised_tokens': count,
                'token_weighted_nll': mean, 'perplexity': perplexity,
                'perplexity_overflow': perplexity is None,
                'answer_mean_nll_quantiles': {str(q): linear_quantile(
                    [x['mean_nll'] for x in records], q) for q in QUANTILES}}
    return {'groups': {name: {'all': subset(rows),
                             'nonfallback': subset([x for x in rows if not x['unverified_fallback']]),
                             'fallback': subset([x for x in rows if x['unverified_fallback']])}
                       for name, rows in memberships.items()},
            'descriptive_only': True, 'statistical_tests': 0,
            'unique_forward_sequences': len(needed),
            'answer_count_weighting': 'each original complete answer once per group',
            'quantiles': 'linear interpolation of per-answer mean NLL'}
