"""Check Codex E3 metric primitives against independent naive implementations on the real T0.8 rows.
Usage: python3 -I metrics_check.py SOURCE_DIR T08_ROWS OUT"""
import sys, json, random, re, itertools, collections
SRC, T8, OUT = sys.argv[1:4]
sys.path.insert(0, SRC)
from experiments.p010 import e3_metrics as M
from experiments.p010.dataset_selection import usable, text_key

def lcs_dp(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]

rng = random.Random(7); bad = 0
for _ in range(3000):
    a = [rng.choice('abcde') for _ in range(rng.randrange(0, 40))]
    b = [rng.choice('abcde') for _ in range(rng.randrange(0, 40))]
    if M.lcs_length(a, b) != lcs_dp(a, b): bad += 1
rows = [x['original_record'] for x in json.load(open(T8))]
by = collections.defaultdict(list)
for r in rows: by[r['problem_id']].append(r)
# real-text LCS check on a sample of pairs
pairs = [(a, b) for v in by.values() for a, b in itertools.combinations(v, 2)]
rng.shuffle(pairs); real_bad = 0
for a, b in pairs[:300]:
    x, y = a['answer_text'].split(), b['answer_text'].split()
    if M.lcs_length(x, y) != lcs_dp(x, y): real_bad += 1
# T0.8 baseline descriptive numbers (independent of their summarize)
n = len(rows); eos = sum(r['stop']['stop_reason'] == 'native_eos' for r in rows)
cor = sum(bool(r['score']['score'].get('correct')) for r in rows)
uu = 0; usable_flag_agree = 0; gs = sum(bool(r.get('gold_supported')) for r in rows)
for pid, v in by.items():
    seen = set()
    for r in sorted(v, key=lambda r: r['attempt']):
        usable_flag_agree += usable(r) == bool(r['usable'])
        k = text_key(r['answer_text'])
        if usable(r) and k not in seen: seen.add(k); uu += 1
rl = [M.rouge_l(a['answer_text'], b['answer_text']) for v in by.values() for a, b in itertools.combinations(sorted(v, key=lambda r: r['attempt']), 2)]
eq = [M.equation_set(r['answer_text']) for r in rows[:5]]
res = dict(lcs_random_mismatch=bad, lcs_real_mismatch_of_300=real_bad, t08_n=n, t08_native_eos=eos, t08_correct=cor,
           t08_gold_supported=gs, t08_usable_fn_agrees_with_saved_flag=usable_flag_agree, t08_usable_unique=uu,
           t08_pairs=len(rl), t08_pooled_rougeL=round(sum(rl) / len(rl), 4), eq_set_examples=[sorted(e)[:6] for e in eq[:2]])
json.dump(res, open(OUT, 'w'), indent=1, ensure_ascii=False); print(json.dumps(res, indent=1, ensure_ascii=False))
