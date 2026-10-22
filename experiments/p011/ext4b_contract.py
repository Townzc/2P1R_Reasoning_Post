"""New direct-owner relaxed-pool 4xB scope; old P011 cells remain frozen."""
import random
from experiments.p011 import data_contract as rules
from experiments.p011.owner_0205_common import read, sha

OWNER_SHA = '2d5e3e9e0d25614d9a5b1e13e6e5535f620a79f61825c03a1283f75be99bb817'
POOL_SEED = 'p011-ext-4B-20261022'
LARGE = 'long_R12096x1_S-F15_s17'
SMALL = 'long_R3024xE4_S-F15_s17'
DATA_SCOPE = 'p011-ext-4B-relaxed-pool-input-construction-CR'


def admit(spec_path, review_path):
    spec, review = read(spec_path), read(review_path)
    if (spec['owner_report_sha256'] != OWNER_SHA
            or spec.get('large_questions') != 12096 or spec.get('small_questions') != 3024
            or spec.get('large_cell') != LARGE or spec.get('small_cell') != SMALL
            or sha(spec['direct_owner_amendment']['path']) != spec['direct_owner_amendment']['sha256']
            or review.get('scope') != DATA_SCOPE
            or review.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
            or review.get('spec_sha256') != sha(spec_path)
            or review.get('owner_report_sha256') != OWNER_SHA
            or review.get('source_files') != spec['source_files']
            or sha(review['local_report_path']) != review['report_sha256']
            or any(review.get(k) is not True for k in spec['required_flags'])):
        raise ValueError('Exact new relaxed-pool data CR and direct-owner binding required')
    for path, expected in spec['source_files'].items():
        if sha(path) != expected:
            raise ValueError('Reviewed source changed: '+path)
    return spec


def parent_order(pool):
    ordered = sorted(pool)
    if len(ordered) != len(set(ordered)) or len(ordered) < 12096:
        raise ValueError('At least12096 unique relaxed-pool questions required; no shrink')
    random.Random(POOL_SEED).shuffle(ordered)
    return ordered[:12096]


def choose_from_cached_census(key, rows, census, prefix_lengths, newline_length, leaked):
    """Use saved answer lengths; do not tokenize all850000 answers again.

    Rows are in the exact census source_file,row_index order. Recheck the
    original completeness/decontamination/native-total rule only for selected
    questions, then use the original seeded row permutation. No correctness
    filtering, result-based reroll, or extra answer-length normalization.
    """
    if (len(rows) != census['responses']
            or len(rows) != len(census['answer_lengths'])
            or rules.identity(key) != census['parent_sha256']
            or any(rules.parent_key(r['question']) != key for r in rows)):
        raise ValueError('Exact census group and original sorted row identities required')
    eligible = []
    for index, (row, length) in enumerate(zip(rows, census['answer_lengths'])):
        if (not leaked and rules.complete(row['response'])
                and prefix_lengths[row['question']] + length + 1 + newline_length <= 16384):
            eligible.append(index)
    if len(eligible) != census['eligible_responses'] or not eligible:
        raise ValueError('Selected group eligibility differs from completed census')
    order = list(range(len(rows)))
    random.Random(rules.identity(key+'p011')[:16]).shuffle(order)
    chosen = next(i for i in order if i in set(eligible))
    n = census['answer_lengths'][chosen] + 1
    if n != census['fixed_first_eligible_supervised_tokens']:
        raise ValueError('Original first eligible response differs from census K1')
    return rows[chosen], n
