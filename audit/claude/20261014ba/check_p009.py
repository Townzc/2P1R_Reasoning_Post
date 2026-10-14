import json, hashlib, unicodedata, sys, collections
sys.path.insert(0, '/tmp/claude-0/p9tools')
from qtok import build
I = '/tmp/claude-0/p9/in'
enc, dec, added = build('/tmp/claude-0/p9/qwen_tok.json')
R = {}
def qk(t): return hashlib.sha256(' '.join(unicodedata.normalize('NFC', t).split()).encode()).hexdigest()
def ok(t): return hashlib.sha256(t.encode()).hexdigest()
def prefix(p): return f"Problem: {p}\nSolution:\n"
SYSTEM = r'Please reason step by step, and put your final answer within \boxed{}.'
def chat(problem):  # Qwen2.5 chat template with explicit system
    return f"<|im_start|>system\n{SYSTEM}<|im_end|>\n<|im_start|>user\n{problem}<|im_end|>\n<|im_start|>assistant\n"
rl = lambda f: [json.loads(l) for l in open(f'{I}/{f}', encoding='utf-8')]
train = rl('math_train7500.jsonl'); m500 = rl('math500.jsonl'); gsm = rl('gsm8k_test1319.jsonl'); req = rl('math_teacher_requests8993.jsonl')
mdev = json.load(open(f'{I}/math_dev_examples.json')); gdev = json.load(open(f'{I}/gsm_dev_examples.json'))
uns = json.load(open(f'{I}/unsupported_math_train.json'))
# 0. encoder self-test on endpoint prompts (decode->re-encode must reproduce ids)
for name in ['qwen_math_zero', 'qwen_math_four', 'qwen_gsm_zero_parity', 'teacher_math_zero', 'teacher_gsm_zero']:
    d = json.load(open(f'{I}/{name}.json')); mism = 0; mx = 0
    for p in d['prompts']:
        ids = p['input_ids']; mx = max(mx, len(ids))
        if enc(dec(ids)) != ids: mism += 1
    R[f'selftest_{name}'] = dict(n=len(d['prompts']), reencode_mismatch=mism, max_prompt=mx, cap=d['max_new_tokens'],
                                 fits=mx + d['max_new_tokens'] <= 2048, eos=d['eos_token_id'])
# 1. train/test overlap + duplicates
tk = collections.Counter(qk(r['problem']) for r in train); mk = {qk(r['problem']) for r in m500}
R['train_rows'] = len(train); R['train_unique'] = len(tk); R['dup_groups'] = [[r['problem_id'] for r in train if qk(r['problem']) == k] for k, c in tk.items() if c > 1]
R['train_m500_overlap'] = len(set(tk) & mk); R['m500_unique'] = len(mk)
R['ids_unique'] = len({r['problem_id'] for r in train}) == 7500
# 2. teacher prompts: recompute for all 7500 train with my encoder
tp = {r['problem_id']: enc(chat(r['problem'])) for r in train}
over = sorted([(k, len(v)) for k, v in tp.items() if len(v) + 1024 > 2048])
R['my_overflow'] = over; R['claimed_overflow'] = [(u['problem_id'], u['prompt_tokens']) for u in uns]
R['overflow_match'] = over == sorted(R['claimed_overflow'])
# 3. request roster
c = collections.Counter(r['attempt'] for r in req); R['attempt_counts'] = dict(sorted(c.items()))
first = [r for r in req if r['attempt'] == 1]
R['first_cover_supported'] = {r['problem_id'] for r in first} == set(tp) - {k for k, _ in over}
extra = collections.defaultdict(set)
for r in req:
    if r['attempt'] > 1: extra[r['problem_id']].add(r['attempt'])
R['extra_parents'] = len(extra); R['extra_complete'] = all(v == {2, 3, 4} for v in extra.values())
sup = [k for k in tp if k not in dict(over)]
mine500 = set(sorted(sup, key=lambda p: ok('p009-extra-500-seed17:' + p))[:500])
R['extra_selection_reproduced'] = mine500 == set(extra)
R['prompt_ids_match_mine'] = sum(r['prompt_token_ids'] != tp[r['problem_id']] for r in req)
R['candidate_unique'] = len({r['candidate_id'] for r in req}) == len(req)
R['seeds_unique'] = len({r['seed'] for r in req}) == len(req)
R['order_first_attempts_before_extras'] = all(r['attempt'] == 1 for r in req[:len(first)])
# 4. MATH dev examples
R['mdev_ids'] = [r['problem_id'] for r in mdev]
R['mdev_tokens'] = [len(enc(prefix(r['problem']) + r['solution'] + '\n\n')) for r in mdev]
mdk = {qk(r['problem']) for r in mdev}
R['mdev_disjoint_train_m500'] = not (mdk & (set(tk) | mk))
R['mdev_from_test_split'] = all('/test/' in r['problem_id'] for r in mdev)
mm = max(len(enc(prefix(r['problem']))) for r in m500); R['m500_max_zero_prompt_mine'] = mm; R['per_example_limit_mine'] = (1024 - mm) // 4
demo = ''.join(prefix(r['problem']) + r['solution'] + '\n\n' for r in mdev)
four = json.load(open(f'{I}/qwen_math_four.json'))['prompts']
R['math_four_matches_construction'] = sum(p['input_ids'] != enc(demo + prefix(r['problem'])) for p, r in zip(four, m500))
zero = json.load(open(f'{I}/qwen_math_zero.json'))['prompts']
R['math_zero_matches_construction'] = sum(p['input_ids'] != enc(prefix(r['problem'])) for p, r in zip(zero, m500))
tz = json.load(open(f'{I}/teacher_math_zero.json'))['prompts']
R['teacher_math_zero_matches'] = sum(p['input_ids'] != enc(chat(r['problem'])) for p, r in zip(tz, m500))
# 5. GSM parity prompts vs P008 exploratory base prompts (same base prefix format)
par = json.load(open(f'{I}/qwen_gsm_zero_parity.json'))['prompts']
old = json.load(open('/tmp/claude-0/p9/old_wrong_prompts.json'))
oldm = {p['problem_id']: p['input_ids'] for p in old}
R['parity_vs_p008_prompts_mismatch'] = sum(p['input_ids'] != oldm[p['problem_id']] for p in par)
R['parity_order_matches_test'] = [p['problem_id'] for p in par] == [r['problem_id'] for r in gsm]
tg = json.load(open(f'{I}/teacher_gsm_zero.json'))['prompts']
R['teacher_gsm_zero_matches'] = sum(p['input_ids'] != enc(chat(r['prompt'])) for p, r in zip(tg, gsm))
R['gdev_ids'] = [r['id'] for r in gdev]
R['gdev_test_overlap'] = len({qk(r['problem']) for r in gdev} & {qk(r['prompt']) for r in gsm})
print(json.dumps(R, indent=1, ensure_ascii=False))
