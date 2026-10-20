"""Original E3 descriptive supply metrics; lexical similarity is not semantics.

Definitions are fixed before either new-temperature output. No model, tokenizer,
symbolic scorer, selection of questions or statistical inference is performed.
"""
from itertools import combinations
import re
import unicodedata
from experiments.p010.dataset_selection import usable, text_key

DEFINITION = {
    'complete': 'original frozen native_eos only; other stops separately counted',
    'correct': 'original frozen Boolean, all eight attempts in denominator',
    'usable_unique': 'native EOS, parsed correct; original normalized full-answer key; first occurrence per question',
    'length': 'original physical returned token count; logical retained tokens also reported',
    'token_cost': 'all eight physical returned tokens, including bad/capped/duplicate, divided by usable unique count',
    'rouge_L': 'F1 of exact longest common subsequence of whitespace-separated answer-segment tokens; case preserved',
    'equation_set': 'lexical expressions inside LaTeX math delimiters, plus un-delimited single-line equations; Unicode NFKC, whitespace removed',
    'equation_jaccard_empty': 'both empty -> 1, one empty -> 0; empty-union count disclosed',
    'pairs': 'all 28 original within-question pairs first; usable-unique pairs separate, never a replacement',
    'aggregation': 'pooled pair mean and equal-weight question means among questions with at least one pair, with denominator',
    'semantic_equivalence_claim': False,
    'confidence_intervals': False,
}


def lcs_length(a, b):
    """Exact bit-parallel LCS; a standard dynamic-programming identity."""
    if len(b) > len(a):
        a, b = b, a
    masks = {}
    for i, token in enumerate(b):
        masks[token] = masks.get(token, 0) | (1 << i)
    state = 0
    for token in a:
        matched = state | masks.get(token, 0)
        state = matched & ~(matched - ((state << 1) | 1))
    return state.bit_count()


def rouge_l(left, right):
    a, b = left.split(), right.split()
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return 2 * lcs_length(a, b) / (len(a) + len(b))


MATH = re.compile(r'\\\[(.*?)\\\]|\\\((.*?)\\\)|\$\$(.*?)\$\$|(?<!\\)\$(.*?)(?<!\\)\$', re.S)


def equation_set(text):
    expressions = []
    for match in MATH.finditer(text):
        expressions.extend(re.split(r'\\\\|\n', next(x for x in match.groups() if x is not None)))
    # Plain text equations are whole lines without prose punctuation. This is a
    # documented surface extractor, not an algebraic or reasoning validator.
    unmarked = MATH.sub('', text)
    for line in unmarked.splitlines():
        line = line.strip()
        if '=' in line and not re.search(r'[.!?;:]|[A-Za-z]{4,}', line):
            expressions.append(line)
    return {re.sub(r'\s+', '', unicodedata.normalize('NFKC', x)) for x in expressions if x.strip()}


def similarities(rows):
    pairs = []
    for a, b in combinations(rows, 2):
        left, right = equation_set(a['answer_text']), equation_set(b['answer_text'])
        union = left | right
        pairs.append(dict(left_attempt=a['attempt'], right_attempt=b['attempt'],
            rouge_L=rouge_l(a['answer_text'], b['answer_text']),
            equation_jaccard=len(left & right)/len(union) if union else 1.0,
            empty_equation_union=not union))
    return dict(pair_count=len(pairs), pairs=pairs,
        rouge_L_mean=sum(x['rouge_L'] for x in pairs)/len(pairs) if pairs else None,
        equation_jaccard_mean=sum(x['equation_jaccard'] for x in pairs)/len(pairs) if pairs else None,
        empty_equation_unions=sum(x['empty_equation_union'] for x in pairs))


def summarize(rows, problem_ids):
    if len(problem_ids) != 200 or len(set(problem_ids)) != 200 or len(rows) != 4800:
        raise ValueError('All original 200 questions and 4800 matched attempts required')
    groups = {label: {pid: {} for pid in problem_ids} for label in ('t06', 't08', 't10')}
    identities = set()
    for row in rows:
        label, pid, attempt = row['temperature_label'], row['problem_id'], row['attempt']
        if (label not in groups or pid not in groups[label] or type(attempt) is not int
                or not 1 <= attempt <= 8 or attempt in groups[label][pid]
                or type(row['score']['score'].get('correct')) is not bool
                or type(row['physical_returned_tokens']) is not int or not 1 <= row['physical_returned_tokens'] <= 1024
                or row['candidate_id'] in identities or type(row['answer_text']) is not str):
            raise ValueError('Unknown, duplicate, missing or altered original attempt')
        identities.add(row['candidate_id']); groups[label][pid][attempt] = row
    summaries = {}; questions = []
    for label, question_map in groups.items():
        counts = dict(native_eos=0, correct=0, usable_unique=0, physical_tokens=0, retained_tokens=0)
        stop_counts = {}; question_similarities = {'all': [], 'usable_unique': []}
        for pid in problem_ids:
            attempts = question_map[pid]
            if set(attempts) != set(range(1, 9)):
                raise ValueError('Original first-eight roster incomplete')
            part = [attempts[a] for a in range(1, 9)]; unique = []; seen = set()
            for row in part:
                reason = row['stop']['stop_reason']
                stop_counts[reason] = stop_counts.get(reason, 0) + 1
                counts['native_eos'] += reason == 'native_eos'
                counts['correct'] += row['score']['score']['correct']
                counts['physical_tokens'] += row['physical_returned_tokens']
                counts['retained_tokens'] += row['stop']['retained_tokens']
                key = text_key(row['answer_text'])
                if usable(row) and key not in seen:
                    unique.append(row); seen.add(key)
            counts['usable_unique'] += len(unique)
            sims = dict(all=similarities(part), usable_unique=similarities(unique))
            for group in sims: question_similarities[group].append(sims[group])
            questions.append(dict(temperature_label=label, problem_id=pid,
                usable_unique_attempts=[x['attempt'] for x in unique], similarities=sims))
        aggregates = {}
        for group, values in question_similarities.items():
            valid = [x for x in values if x['pair_count']]
            pairs = [p for x in valid for p in x['pairs']]
            aggregates[group] = dict(pair_count=len(pairs), questions_with_pairs=len(valid),
                empty_equation_unions=sum(x['empty_equation_unions'] for x in valid),
                pooled_rouge_L=sum(x['rouge_L'] for x in pairs)/len(pairs) if pairs else None,
                pooled_equation_jaccard=sum(x['equation_jaccard'] for x in pairs)/len(pairs) if pairs else None,
                equal_question_rouge_L=sum(x['rouge_L_mean'] for x in valid)/len(valid) if valid else None,
                equal_question_equation_jaccard=sum(x['equation_jaccard_mean'] for x in valid)/len(valid) if valid else None)
        summaries[label] = dict(**counts, attempts=1600, questions=200, stops=stop_counts,
            complete_fraction=counts['native_eos']/1600, correct_fraction=counts['correct']/1600,
            usable_unique_fraction=counts['usable_unique']/1600,
            average_physical_tokens=counts['physical_tokens']/1600,
            average_retained_tokens=counts['retained_tokens']/1600,
            physical_tokens_per_usable_unique=counts['physical_tokens']/counts['usable_unique'] if counts['usable_unique'] else None,
            similarities=aggregates)
    return dict(definitions=DEFINITION, temperatures=summaries, questions=questions,
        original_t08_scores_reused=1600, new_symbolic_scores_by_metrics=0,
        original_question_selection_unchanged=True, independent_A3_pending=True)
