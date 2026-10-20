"""Conservative, CPU-only problem identity and released-solution auditing.

No model call, eval, symbolic expression execution, or outcome-based backfill.
Answer agreement is not a proof verifier. Unsupported answers stay unresolved.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
import re
import unicodedata


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def normalized(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def words(text, mask_numbers=False):
    value = unicodedata.normalize('NFC', text).lower()
    tokens = re.findall(r'[a-z]+|\d+(?:\.\d+)?|[^\w\s]', value)
    return ['<number>' if mask_numbers and re.fullmatch(r'\d+(?:\.\d+)?', t) else t for t in tokens]


def shingles(text, n=5, mask_numbers=False):
    ts = words(text, mask_numbers)
    return {tuple(ts[i:i+n]) for i in range(max(1, len(ts)-n+1))}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a or b else 1.0


def near_edges(records, threshold=0.8, n=5, mask_numbers=False):
    """Exact shingle-Jaccard join using an inverted index (no approximate LSH)."""
    index, lengths = defaultdict(list), []
    for i, r in enumerate(records):
        ss = shingles(r['problem'], n, mask_numbers)
        overlap = Counter()
        for s in ss:
            for other in index[s]:
                if threshold * len(ss) <= lengths[other] <= len(ss) / threshold:
                    overlap[other] += 1
        for other, shared in sorted(overlap.items()):
            score = shared / (len(ss) + lengths[other] - shared)
            if score >= threshold:
                yield other, i, score
        lengths.append(len(ss))
        for s in ss:
            index[s].append(i)


def group_records(records, threshold=0.8, n=5):
    parents = list(range(len(records)))
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    def union(a, b):
        a, b = root(a), root(b)
        if a != b:
            parents[max(a, b)] = min(a, b)
    edges, exact = [], {}
    for i, r in enumerate(records):
        key = normalized(r['problem'])
        if key in exact:
            union(exact[key], i)
            edges.append({'a': records[exact[key]]['id'], 'b': r['id'], 'kind': 'normalized_exact', 'score': 1.0})
        else:
            exact[key] = i
    for masked in (False, True):
        for a, b, score in near_edges(records, threshold, n, masked):
            union(a, b)
            edges.append({'a': records[a]['id'], 'b': records[b]['id'],
                          'kind': 'number_masked_candidate' if masked else 'near_text', 'score': score})
    groups = defaultdict(list)
    for i, r in enumerate(records):
        groups[root(i)].append(r['id'])
    names = {k: 'group-' + sha('\n'.join(sorted(ids)))[:20] for k, ids in groups.items()}
    return {r['id']: names[root(i)] for i, r in enumerate(records)}, edges


def stratified_order(records, seed, purpose):
    strata = defaultdict(list)
    for r in records:
        strata[r['stratum']].append(r)
    for rows in strata.values():
        rows.sort(key=lambda r: (sha(f'{seed}:{purpose}:{r["id"]}'), r['id']))
    # Balanced prefixes over available subject/level strata, declared before outputs.
    keys = sorted(strata, key=lambda k: sha(f'{seed}:{purpose}:stratum:{k}'))
    result = []
    for i in range(max(map(len, strata.values()), default=0)):
        result.extend(strata[k][i] for k in keys if i < len(strata[k]))
    return result


def stratified_take(records, count, seed, purpose):
    """Proportional largest-remainder quotas, at least one per available stratum."""
    strata = defaultdict(list)
    for row in records:
        strata[row['stratum']].append(row)
    if count == 0:
        return []
    if count > len(records):
        raise ValueError('Insufficient parents for stratified sample')
    keys = sorted(strata, key=lambda k: sha(f'{seed}:{purpose}:stratum:{k}'))
    ideal = {k: count*len(strata[k])/len(records) for k in keys}
    floor = 1 if count >= len(keys) else 0
    quota = {k: min(len(strata[k]), max(floor, int(ideal[k]))) for k in keys}
    while sum(quota.values()) > count:
        k = max((k for k in keys if quota[k] > floor), key=lambda k: quota[k]-ideal[k])
        quota[k] -= 1
    while sum(quota.values()) < count:
        k = max((k for k in keys if quota[k] < len(strata[k])), key=lambda k: ideal[k]-quota[k])
        quota[k] += 1
    for k in keys:
        strata[k].sort(key=lambda r: sha(f'{seed}:{purpose}:{r["id"]}'))
    used, result = Counter(), []
    # Weighted ordering keeps nested prefixes close to the frozen full-draw quotas.
    for _ in range(count):
        k = min((k for k in keys if used[k] < quota[k]), key=lambda k: (used[k]+.5)/quota[k])
        result.append(strata[k][used[k]])
        used[k] += 1
    return result


def assign_partitions(records, config, groups):
    test_groups = {groups[r['id']] for r in records if r['original_split'] == 'test'}
    used = set()
    for r in records:
        r['group_id'] = groups[r['id']]
        r['exclusions'] = []
        if r['original_split'] == 'test':
            r['partition'] = 'official_test'
            continue
        if r.get('original_file_id_verified') is False:
            r['exclusions'].append('source_id_unresolved')
        if r['group_id'] in test_groups:
            r['exclusions'].append('test_linked_exact_near_or_number_template')
        if r['dataset'] == 'math' and r['level'] not in config['math_levels']:
            r['exclusions'].append('outside_math_levels_1_to_3')
        if '[asy]' in r['problem'] or '\\includegraphics' in r['problem']:
            r['exclusions'].append('diagram_markup')
        if not r['exclusions']:
            if r['group_id'] in used:
                r['exclusions'].append('same_group_representative_already_kept')
            else:
                used.add(r['group_id'])
        r['partition'] = 'excluded' if r['exclusions'] else 'eligible_unassigned'
    for dataset in ('gsm8k', 'math'):
        eligible = [r for r in records if r['dataset'] == dataset and r['partition'] == 'eligible_unassigned']
        counts = [("development", config['development_parents'][dataset]),
                  ("audit_draw", config['audit_parents'][dataset]),
                  ("fresh_draw_reserved", config['reserved_fresh_parents'][dataset])]
        if len(eligible) < sum(count for _, count in counts):
            raise ValueError(f'Insufficient eligible parent groups for declared {dataset} splits')
        for partition, count in counts:
            selected = stratified_take(eligible, count, config['seed'], dataset+':'+partition)
            for rank, r in enumerate(selected, 1):
                r['partition'], r['rank'] = partition, rank
            selected_ids = {r['id'] for r in selected}
            eligible = [r for r in eligible if r['id'] not in selected_ids]
        for r in eligible:
            r['partition'] = 'unused_training_reserve'
    return records


def last_boxed(text):
    hits = list(re.finditer(r'\\(?:boxed|fbox)\s*\{', text))
    if not hits:
        return None
    match = hits[-1]
    depth, start = 1, match.end()
    for i in range(start, len(text)):
        if text[i] == '{' and (i == 0 or text[i-1] != '\\'):
            depth += 1
        elif text[i] == '}' and (i == 0 or text[i-1] != '\\'):
            depth -= 1
            if depth == 0:
                return text[start:i]
    return None


def canonical_answer(answer):
    if answer is None:
        return None
    value = unicodedata.normalize('NFC', str(answer)).strip().strip('$')
    value = value.replace('\\dfrac', '\\frac').replace('\\tfrac', '\\frac')
    for token in ('\\left', '\\right', '\\!', '\\,', '\\;', '\\quad'):
        value = value.replace(token, '')
    # Do not consume the second backslash of a matrix row separator (\\\\ ).
    value = re.sub(r'(?<!\\)\\ ', '', value)
    value = ''.join(value.split())
    # Unambiguous LaTeX presentation only. Units, base subscripts, percent,
    # variable assignments, mixed numbers and arbitrary algebra stay unresolved.
    wrapper = re.fullmatch(r'\\(?:text|textrm|mathrm|mbox)\{([^{}]*)\}', value)
    if wrapper:
        value = wrapper[1]
    value = re.sub(r'\\frac([0-9])([0-9])', r'\\frac{\1}{\2}', value)
    value = re.sub(r'\\sqrt([0-9a-zA-Z])', r'\\sqrt{\1}', value)
    return value


def scalar(answer):
    """Only exact scalar literals or a literal fraction; no eval or parser execution."""
    value = canonical_answer(answer)
    if value is None or len(value) > 200:
        return None
    # Thousands separators only when the complete number follows that grammar.
    if re.fullmatch(r'[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?', value):
        value = value.replace(',', '')
    frac = re.fullmatch(r'([+-]?)\\frac\{([+-]?\d+)\}\{([+-]?\d+)\}', value)
    if frac:
        value = f'{frac[1]}{frac[2]}/{frac[3]}'
    if re.fullmatch(r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:/[+-]?\d+)?', value):
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError):
            return None
    return None


def answer_status(a, b):
    if a is None or b is None or canonical_answer(a) == '' or canonical_answer(b) == '':
        return 'unresolved'
    x, y = scalar(a), scalar(b)
    if x is not None and y is not None:
        return 'agree' if x == y else 'disagree'
    if canonical_answer(a) == canonical_answer(b):
        return 'agree'
    return 'unresolved'


def final_answer(response, dataset):
    boxed = last_boxed(response)
    if boxed is not None:
        return boxed
    if dataset == 'gsm8k' and '####' in response:
        return response.rsplit('####', 1)[-1].strip()
    return None


def check_candidate(parent, row, seen, tokenizer, max_length):
    from src.sft_data import encode_row
    response = row['generated_solution']
    rec = {'response_sha256': sha(response), 'normalized_response_sha256': sha(normalized(response))}
    if not response.strip():
        return rec | {'reason': 'empty_response'}
    expected = answer_status(row['expected_answer'], parent['answer'])
    if expected != 'agree':
        return rec | {'reason': 'source_reference_' + expected}
    prediction = final_answer(response, parent['dataset'])
    if prediction is None:
        return rec | {'reason': 'missing_final_answer'}
    agreement = answer_status(prediction, parent['answer'])
    if agreement != 'agree':
        return rec | {'reason': 'final_answer_' + agreement}
    if rec['normalized_response_sha256'] in seen:
        return rec | {'reason': 'duplicate_normalized_text'}
    seen.add(rec['normalized_response_sha256'])
    try:
        encoded = encode_row({'prompt': parent['problem'], 'response': response,
                              'problem_id': parent['id']}, tokenizer, 1_000_000)
    except ValueError as exc:
        return rec | {'reason': 'serialization_error', 'error': str(exc)}
    rec.update(n_prompt=encoded['n_prompt'], n_supervised=encoded['n_supervised'],
               n_processed=encoded['n_processed'])
    return rec | {'reason': 'accepted' if encoded['n_processed'] <= max_length else 'over_length'}


def quantiles(values):
    if not values:
        return None
    values = sorted(values)
    return {'n': len(values), 'min': values[0], 'p50': values[math.ceil(len(values)*.5)-1],
            'p90': values[math.ceil(len(values)*.9)-1], 'p95': values[math.ceil(len(values)*.95)-1],
            'p99': values[math.ceil(len(values)*.99)-1], 'max': values[-1],
            'mean': sum(values)/len(values), 'sum': sum(values)}


def grid_statistics(parents, accepted, ps, ks):
    order = sorted(parents, key=lambda r: r['rank'])
    result = []
    for p in ps:
        rows = order[:p]
        if len(rows) != p:
            raise ValueError('Grid denominator does not equal acquired P')
        for k in ks:
            selected = [a for r in rows for a in accepted.get(r['id'], [])[:k]]
            result.append({'acquired_p': p, 'target_k': k,
                           'trainable_p': sum(bool(accepted.get(r['id'])) for r in rows),
                           'target_reached_p': sum(len(accepted.get(r['id'], [])) >= k for r in rows),
                           'zero_solution_p': sum(not accepted.get(r['id']) for r in rows),
                           'unique_pairs': len(selected), 'target_pair_shortfall': p*k-len(selected),
                           'one_pass_supervised_tokens': sum(a['n_supervised'] for a in selected),
                           'one_pass_processed_tokens': sum(a['n_processed'] for a in selected)})
    return result
