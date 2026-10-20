"""Pure P011 long-data rules; no model, scoring, network, or admission side effects.

The operational choices left unspecified in plan v1 are listed in the CR request.
They must be accepted before the real construction path runs.
"""
from collections import Counter
import hashlib
import math
import random
import unicodedata

PLAN_SHA256 = '20d919afd4f1d7d1f237042bad5804fff1de20ebeda444cfdbf92f250bb69c22'
MAX_TOTAL_TOKENS = 16384
CELLS = {'A1': (256, 1), 'A2': (256, 2), 'A3': (256, 4),
         'A4': (256, 8), 'A5': (256, 16), 'A6': (1024, 1),
         'A7': (4096, 1), 'A8': (1024, 4)}


def parent_key(text):
    if type(text) is not str or not text.strip():
        raise ValueError('Nonempty literal user text required')
    return unicodedata.normalize('NFKC', text).strip()


def identity(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def answer_region(text):
    if type(text) is not str:
        raise ValueError('Literal assistant response required')
    return text.rsplit('</think>', 1)[-1] if '</think>' in text else text[-2000:]


def complete(text):
    # Completeness only. Never infer that a boxed answer is correct.
    return '\\boxed{' in answer_region(text)


def conversation_pair(row):
    turns = row['conversations']
    if (type(turns) is not list or len(turns) != 2
            or turns[0]['from'] != 'human'
            or turns[1]['from'] not in ('gpt', 'assistant')):
        raise ValueError('Expected exactly one human/assistant pair; no silent repair')
    question, response = turns[0]['value'], turns[1]['value']
    parent_key(question)
    if type(response) is not str or not response:
        raise ValueError('Empty/non-string response')
    return question, response


def grams(text):
    """Proposed CR-bound implementation: case-sensitive NFKC whitespace words."""
    words = parent_key(text).split()
    return {tuple(words[i:i + 13]) for i in range(max(0, len(words) - 12))}


class Decontamination:
    def __init__(self, problems):
        self.exact = {parent_key(x) for x in problems}
        self.index = set().union(*(grams(x) for x in self.exact))

    def hit(self, text):
        key = parent_key(text)
        return key in self.exact or bool(grams(key) & self.index)


def native_text(tokenizer, question, response):
    messages = [{'role': 'user', 'content': question}]
    prefix = tokenizer.apply_chat_template(messages, tokenize=False,
                                          add_generation_prompt=True)
    full = tokenizer.apply_chat_template(
        messages + [{'role': 'assistant', 'content': response}],
        tokenize=False, add_generation_prompt=False)
    # Qwen's own default system is inserted by its pinned template. No supplied system.
    expected = prefix + response + '<|im_end|>\n'
    if full != expected:
        raise ValueError('Pinned native Qwen template/prefix/suffix differs')
    return prefix, full


def bounded_length(tokenizer, question, response):
    """A 16385 sentinel suffices for rejection; never truncates a training answer."""
    prefix, _ = native_text(tokenizer, question, response)
    pieces = (prefix, response + '<|im_end|>', '\n')
    return min(MAX_TOTAL_TOKENS + 1, sum(len(tokenizer(
        text, add_special_tokens=False, truncation=True,
        max_length=MAX_TOTAL_TOKENS + 1)['input_ids']) for text in pieces))


def encode_complete(tokenizer, question, response, path_id):
    prefix, text = native_text(tokenizer, question, response)
    # Tokenize the native prefix, literal assistant+EOS, and ignored trailing
    # newline separately. Whole-string BPE can merge the prompt's newline with
    # an assistant-leading newline, making an assistant-only token mask
    # impossible. This explicit, CR-bound boundary policy is used both for
    # parent length filtering and real training encoding; no whitespace is lost.
    pre, answer, suffix = [tokenizer(part, add_special_tokens=False,
        truncation=False)['input_ids'] for part in (prefix, response + '<|im_end|>', '\n')]
    ids = pre + answer + suffix
    if tokenizer.decode(ids, skip_special_tokens=False,
                        clean_up_tokenization_spaces=False) != text:
        raise ValueError('Segmented native chat tokens must recover the exact original text')
    if len(ids) > MAX_TOTAL_TOKENS:
        raise ValueError('Selected full answer exceeds the total sequence limit')
    labels = [-100] * len(pre) + answer + [-100] * len(suffix)
    positions = [i for i, x in enumerate(labels) if x != -100]
    eos = tokenizer.convert_tokens_to_ids('<|im_end|>')
    if (not positions or positions[0] == 0
            or positions != list(range(positions[0], positions[-1] + 1))
            or labels[positions[-1]] != eos):
        raise ValueError('Assistant plus im_end must form one nonempty masked span')
    return {'path_id': path_id, 'parent_sha256': identity(parent_key(question)),
            'input_ids': ids, 'labels': labels,
            'n_supervised': len(positions), 'n_processed': len(ids),
            'assistant_start': positions[0], 'assistant_end': positions[-1] + 1,
            'eos_token_id': eos, 'template_final_newline_supervised': False}


def ot3_order(eligible_keys, rows_by_parent):
    # The inventory already shuffles candidates and retains the first4096
    # eligible parents under the owner-approved R3 amendment. Never reshuffle.
    order = list(eligible_keys)
    if len(order) != len(set(order)):
        raise ValueError('Selected parent order contains duplicates')
    if len(order) < 4096:
        raise ValueError(f'Only {len(order)} eligible OT3 parents; report without resampling')
    selected = order[:4096]
    result = {}
    for key in selected:
        rows = list(rows_by_parent(key))
        if len(rows) != 16:
            raise ValueError('All selected parents must retain exactly 16 original rows')
        # Use the literal 16-character hexadecimal string as Random's seed.
        random.Random(identity(key + 'p011')[:16]).shuffle(rows)
        result[key] = rows
    return selected, result


def choose_d_row(key, teacher, rows):
    """Fix one raw row before any length/completeness filtering; no cherry-picking."""
    if teacher not in ('am_thinking', 'am_qwen3') or not rows:
        raise ValueError('Explicit D teacher and nonempty original row order required')
    seed = identity(key + ':p011-D:' + teacher + ':20261021')[:16]
    return random.Random(seed).choice(rows)


def exact_subset(lengths, target, seed):
    """Exact q+1 subset with bounded checkpoint memory, never a dose approximation.

    Same seeded bitset reachability as the earlier scheduler; checkpoints replace
    storing every prefix bitset for long answers. Reconstruction recomputes only
    a 64-item block. Failure is retained and does not change B or the answer set.
    """
    if target == 0:
        return []
    divisor = math.gcd(*lengths)
    if target % divisor:
        raise ValueError('Exact balanced whole-answer dose is arithmetically infeasible')
    values = [x // divisor for x in lengths]
    target //= divisor
    order = list(range(len(values)))
    random.Random(seed).shuffle(order)
    mask, reachable, checkpoints = (1 << (target + 1)) - 1, 1, {0: 1}
    used = 0
    for used, i in enumerate(order, 1):
        reachable |= (reachable << values[i]) & mask
        if used % 64 == 0:
            checkpoints[used] = reachable
        if (reachable >> target) & 1:
            break
    if not (reachable >> target) & 1:
        raise ValueError('No exact balanced whole-answer remainder; no truncation')
    left, chosen = target, []
    while used:
        begin = ((used - 1) // 64) * 64
        previous, history = checkpoints[begin], []
        for j in range(begin, used):
            i = order[j]
            history.append((i, previous))
            previous |= (previous << values[i]) & mask
        for i, before in reversed(history):
            if not (before >> left) & 1:
                chosen.append(i)
                left -= values[i]
        used = begin
    if left != 0:
        raise AssertionError('Exact subset reconstruction differs')
    return chosen


def whole_schedule(rows, budget, seed=17):
    from bisect import bisect_left
    lengths = [x['n_supervised'] for x in rows]
    if (not lengths or any(type(x) is not int or x <= 0 for x in lengths)
            or type(budget) is not int or budget <= 0 or seed != 17):
        raise ValueError('Positive integer full-answer dose and seed17 required')
    q, remainder = divmod(budget, sum(lengths))
    if q < 1:
        raise ValueError('One complete pass exceeds frozen B; never drop answers or raise B')
    extras = exact_subset(lengths, remainder, seed)
    stream = []
    for epoch in range(q):
        one_pass = list(range(len(rows)))
        random.Random(f'17:pass:{epoch}').shuffle(one_pass)
        stream.extend(one_pass)
    random.Random('17:extras').shuffle(extras)
    stream.extend(extras)
    updates = (budget + 63999) // 64000
    if len(stream) < updates:
        raise ValueError('Insufficient whole presentations for nonempty updates')
    prefix = [0]
    for i in stream:
        prefix.append(prefix[-1] + lengths[i])
    cuts = [0]
    for step in range(1, updates):
        j = bisect_left(prefix, step * budget / updates)
        j = min((j - 1, j), key=lambda k: abs(prefix[k] - step * budget / updates))
        cuts.append(max(cuts[-1] + 1, min(j, len(stream) - (updates - step))))
    cuts.append(len(stream))
    batches = [stream[a:b] for a, b in zip(cuts, cuts[1:])]
    counts = Counter(stream)
    if (prefix[-1] != budget or any(counts[i] not in (q, q + 1) for i in range(len(rows)))
            or any(not b for b in batches)):
        raise AssertionError('Whole-answer balanced exact dose invariant differs')
    return {'supervised_tokens': budget, 'optimizer_updates': updates, 'q': q,
            'seed': seed, 'row_path_ids': [x['path_id'] for x in rows],
            'exposures': [counts[i] for i in range(len(rows))], 'updates': batches,
            'length_bucket_width': None, 'presentation_order': 'shuffled_full_passes_then_extras',
            'subset_selection_depends_on_lengths': True,
            'runtime_admitted': False}
