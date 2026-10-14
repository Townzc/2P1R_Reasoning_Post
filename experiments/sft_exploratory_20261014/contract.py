"""Pure deterministic input selection; no cloud or model calls."""
from collections import Counter
from experiments.sft_allocation_p008.contract import stable_seed
from experiments.sft_allocation_p008.schedule import schedule
from experiments.sft_allocation_p008.frozen_student_plan import validate_frozen_lrs
from experiments.sft_allocation_midpoint.common import digest
from src.sft_data import prefix, encode_row, budget_report

RUNS = ('base_4shot', 'instruct_0shot', 'wrong_teacher_t1')
SYSTEM = r'Please reason step by step, and put your final answer within \boxed{}.'
TARGETS = 524287
UPDATES = 256
WORKER_SECONDS = 6001
PLATFORM_SECONDS = 6061
STARTUP_SECONDS = 600
RESERVED_CENTS = 826


def wrong_candidates(cache, parent_order, limit=429):
    if len(parent_order) != len(set(parent_order)) or limit != 429:
        raise ValueError('Frozen order and authorized count required')
    positions = {p: i for i, p in enumerate(parent_order)}
    records = list(cache.values())
    if any(r['problem_id'] not in positions or k != r['candidate_id'] for k, r in cache.items()):
        raise ValueError('Foreign parent or candidate identity')
    records.sort(key=lambda r: (positions[r['problem_id']], r['attempt']))
    eligible = []
    seen = {}
    for r in records:
        key = (r['problem_id'], r['normalized_text_sha256'])
        # Preserve P008's exact NFC/whitespace-within-parent definition, including
        # the first earlier unsuccessful occurrence. Do not deduplicate by score.
        duplicate = seen.get(key)
        if r['duplicate_of'] != duplicate:
            raise ValueError('Frozen duplicate provenance differs')
        seen.setdefault(key, r['candidate_id'])
        s, t = r['score'], r['stop']
        if s['version'] != 'marked_answer_v1':
            raise ValueError('Parser changed')
        if (t['eos'] is True and t['truncated'] is False and
                t['token_ids'][-1] in (151643, 151645) and
                s['status'] == 'parsed' and s['answer_correct'] is False and duplicate is None):
            eligible.append(r)
    return eligible[:limit], len(eligible)


def dev_examples(dev, test, eligible_parent_ids):
    if len(dev) != 500 or len({r['id'] for r in dev}) != 500:
        raise ValueError('Original 500 reserved dev rows required')
    expected = sorted(dev, key=lambda r: stable_seed('dev_split', 0, r['id']))
    if dev != expected:
        raise ValueError('Original dev order differs')
    ids = {r['id'] for r in dev}
    if ids & set(eligible_parent_ids) or ids & {r['problem_id'] for r in test}:
        raise ValueError('Dev/train/test identity overlap')
    return dev[:4]


def prompt_ids(kind, row, tok, examples):
    if kind == 'base_4shot':
        text = ''.join(prefix(e['problem']) + e['reference'] + '\n\n' for e in examples) + prefix(row['prompt'])
        return tok(text, add_special_tokens=False)['input_ids']
    if kind == 'instruct_0shot':
        return tok.apply_chat_template([{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': row['prompt']}], tokenize=True, add_generation_prompt=True)
    if kind == 'wrong_teacher_t1':
        return tok(prefix(row['prompt']), add_special_tokens=False)['input_ids']
    raise ValueError('Unauthorized evaluation role')


def make_plan(rows, tok, frozen_lrs):
    encoded = [encode_row(r, tok, 2048) for r in rows]
    for r, e in zip(rows, encoded):
        r['source'].update({k: e[k] for k in ('n_prompt', 'n_processed', 'n_supervised')})
    p = schedule([r['n_supervised'] for r in encoded], TARGETS, UPDATES, 17)
    p.update(lrs=validate_frozen_lrs(frozen_lrs, UPDATES), row_path_ids=[r['path_id'] for r in rows],
        targets_are_frozen_before_student_scores=True, seed=17,
        budget=budget_report(encoded, p['updates'], 1), exploratory=True)
    if p['budget']['supervised_response_tokens'] != TARGETS or p['budget']['optimizer_updates'] != UPDATES:
        raise ValueError('Exact authorized dose unavailable; no silent change')
    return p


def validate_spec(spec, plan, config, sources):
    if spec['exploratory'] is not True or spec['preregistered'] is not False or spec['total_cap_cents'] != 3000:
        raise ValueError('Exploratory budget binding differs')
    if plan != spec['plan'] or config != spec['configs'].get(config['run_id']) or config['run_id'] not in RUNS:
        raise ValueError('Exact plan/config binding differs')
    if set(spec['configs']) != set(RUNS) or spec['source_files'] != sources:
        raise ValueError('Exact three-run/source binding differs')
    if any(c['max_seconds'] != WORKER_SECONDS for c in spec['configs'].values()):
        raise ValueError('Worker cap changed')
    if any(s['reserved_cents'] != RESERVED_CENTS for s in plan['slots'].values()) or set(plan['slots']) != set(RUNS):
        raise ValueError('Finite nonrecycled slots differ')
    return digest(spec)


def validate_release(spec, plan, config, release):
    import hashlib
    validate_spec(spec, plan, config, release['source_files'])
    a = release['acceptance']
    if (a['scope'] != 'exploratory-20261014-code-and-data' or
            a['decision'] not in ('PASS', 'PASS-WITH-NOTES') or
            a['spec_sha256'] != digest(spec) or a['source_files'] != spec['source_files'] or
            a['input_manifest_sha256'] != config['input_sha256'] or
            a['report_sha256'] != hashlib.sha256(release['review_report'].encode()).hexdigest() or
            len(a['review_commit']) != 40 or len(a['target_commit']) != 40):
        raise ValueError('Real exact source/code/input review required')
    if release['upload_verified']['manifest_sha256'] != config['input_sha256']:
        raise ValueError('Independent input readback required')
