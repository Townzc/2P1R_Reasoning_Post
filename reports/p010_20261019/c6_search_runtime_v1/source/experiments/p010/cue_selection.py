"""P010 E2 label-free proposal and entropy selection, before any cue search.

Probability provider and answer normalizer are deliberately separate. Neither
function here accepts a gold answer, correctness label, or test-set record.
"""
import math
from collections import Counter

WIDTH = 20
DEPTH = 2
PROBLEMS = 30
ROLLOUTS = 16


def _valid_matrix(matrix, n, vocab):
    if len(matrix) != n or any(len(row) != vocab for row in matrix):
        raise ValueError('Full original dev-by-vocabulary probability matrix required')
    for row in matrix:
        if (any(not math.isfinite(x) or not 0 <= x <= 1 for x in row)
                or not math.isclose(sum(row), 1.0, abs_tol=2e-5)):
            raise ValueError('Unnormalized/nonfinite model probability distribution')


def propose(next_probabilities, problem_ids, allowed_token_ids, vocab_size, *, width=WIDTH):
    """Average joint prefix probabilities, retain a depth-wise beam, pool depths.

    next_probabilities(prefix) returns one full vocabulary vector for each of
    the same30 dev prompts. There is no generated answer or gold lookup here.
    First and second-depth beams are both eligible final openings, as in the
    paper's tables. Tie order is the token tuple, fixed before observations.
    All probabilities are measured for all30 prompts; absent per-problem beams
    are not silently assigned zero mass. The source-code reference defaults
    differ from P010; this implementation explicitly freezes width20/depth2/30.
    """
    ids = tuple(problem_ids)
    allowed = tuple(sorted(set(allowed_token_ids)))
    if (len(ids) != PROBLEMS or len(set(ids)) != PROBLEMS
            or type(vocab_size) is not int or type(width) is not int
            or width != WIDTH or len(allowed) < width
            or any(type(t) is not int or not 0 <= t < vocab_size for t in allowed)):
        raise ValueError('Exact30 unique dev IDs and20-opening beam required')
    beams = [((), [1.0]*PROBLEMS)]
    depths = []
    all_openings = []
    for depth in range(1, DEPTH+1):
        candidates = []
        for prefix, joint in beams:
            matrix = next_probabilities(prefix)
            _valid_matrix(matrix, PROBLEMS, vocab_size)
            # Any prefix outside this parent's top20 cannot enter the global
            # top20. Rank by mean joint mass, never mean log probability.
            ranked = sorted(allowed, key=lambda t: (
                -sum(joint[i]*matrix[i][t] for i in range(PROBLEMS))/PROBLEMS, t))[:width]
            for t in ranked:
                values = [joint[i]*matrix[i][t] for i in range(PROBLEMS)]
                candidates.append((prefix+(t,), values))
        candidates.sort(key=lambda x: (-sum(x[1])/PROBLEMS, x[0]))
        beams = candidates[:width]
        records = [dict(token_ids=list(p), mean_probability=sum(v)/PROBLEMS,
                        per_problem_probability=v) for p, v in beams]
        depths.append(dict(depth=depth, beam=records))
        all_openings.extend(records)
    all_openings.sort(key=lambda x: (-x['mean_probability'], tuple(x['token_ids'])))
    chosen = all_openings[:width]
    if len({tuple(x['token_ids']) for x in chosen}) != width:
        raise ValueError('Exactly20 distinct token openings required')
    return dict(problem_ids=list(ids), beam_width=width, maximum_depth=DEPTH,
                depths=depths, candidates=chosen, no_cue_added_separately=True,
                gold_used=False, correctness_used=False,
                ranking='mean joint probability across all30 development prompts')


def select(candidates, problem_ids, observations):
    """Select from20 frozen openings plus no-cue using all16 answers per prompt.

    Observations must contain only candidate/problem/rollout and an already
    normalized answer key. None denotes missing/unparseable answers. Unknown
    transport or partial rows must be reconciled outside this function.
    """
    ids = tuple(problem_ids)
    prefixes = [tuple(x) for x in candidates]
    if (len(ids) != PROBLEMS or len(set(ids)) != PROBLEMS
            or len(prefixes) != WIDTH+1 or prefixes[0] != ()
            or len(set(prefixes)) != WIDTH+1
            or any(not 1 <= len(p) <= DEPTH for p in prefixes[1:])):
        raise ValueError('Frozen20 openings plus no-cue and exact30 dev prompts required')
    indexed = {}
    for row in observations:
        if set(row) != {'candidate', 'problem_id', 'rollout', 'answer_key'}:
            raise ValueError('Gold, score or unrelated fields are forbidden in cue selection')
        key = (row['candidate'], row['problem_id'], row['rollout'])
        if (type(key[0]) is not int or not 0 <= key[0] < len(prefixes)
                or key[1] not in ids or type(key[2]) is not int or not 0 <= key[2] < ROLLOUTS
                or key in indexed or (row['answer_key'] is not None
                                      and not isinstance(row['answer_key'], str))):
            raise ValueError('Duplicate, unknown or malformed development observation')
        indexed[key] = row['answer_key']
    if len(indexed) != (WIDTH+1)*PROBLEMS*ROLLOUTS:
        raise ValueError('Every candidate requires the same complete480 responses')
    summary = []
    for j, prefix in enumerate(prefixes):
        entropies = []
        missing = 0
        for pid in ids:
            counts = Counter(indexed[(j, pid, k)] for k in range(ROLLOUTS))
            missing += counts.get(None, 0)
            entropies.append(-sum((n/ROLLOUTS)*math.log2(n/ROLLOUTS) for n in counts.values()))
        summary.append(dict(candidate=j, token_ids=list(prefix), responses=PROBLEMS*ROLLOUTS,
                            missing=missing, missing_fraction=missing/(PROBLEMS*ROLLOUTS),
                            entropies_bits=entropies, mean_entropy_bits=sum(entropies)/PROBLEMS))
    # Exact integer boundary: greater than10pp (48/480), not greater-or-equal.
    for item in summary:
        item['eligible'] = item['missing'] <= summary[0]['missing']+48
    winner = min((x for x in summary if x['eligible']),
                 key=lambda x: (x['mean_entropy_bits'], x['candidate']))
    return dict(candidates=summary, selected_candidate=winner['candidate'],
                selected_token_ids=winner['token_ids'], gold_used=False,
                correctness_used=False, test_data_used=False,
                tie_rule='no-cue then frozen beam rank', no_cue_is_eligible=True)
