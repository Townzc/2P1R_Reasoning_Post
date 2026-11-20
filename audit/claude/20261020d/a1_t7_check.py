"""Independent A1 audit of P010 T7 data (Claude). Usage: python3 -I a1_t7_check.py T7_DIR REPO GOLD_ROWS_JSON"""
import json, sys, glob, re, unicodedata, collections
T, REPO, GOLDF = sys.argv[1:4]
S1 = json.load(open(f'{REPO}/reports/p009_20261014/stage1_s1_inputs_v1/ROSTER_s17.json'))['selections']
q400 = [p.split('::')[0] for p in S1['400']['path_ids']]; q3200 = [p.split('::')[0] for p in S1['3200']['path_ids']]
recs = {}
for f in sorted(glob.glob(f'{T}/ev/derived/*.json')):
    for r in json.load(open(f)):
        assert r['candidate_id'] not in recs; recs[r['candidate_id']] = r
gold = {}
for r in json.load(open(GOLDF)):
    if r['dataset'] not in ('qwen_math_zero', 'qwen_math_four', 'teacher_math_zero'): gold.setdefault(r['problem_id'], r['gold'])
def last_boxed(s):
    i = max(s.rfind('\\boxed'), s.rfind('\\fbox'))
    if i < 0: return None
    j = s.find('{', i); d = 0
    for k in range(j, len(s)):
        if s[k] == '{' and s[k-1] != '\\': d += 1
        elif s[k] == '}' and s[k-1] != '\\':
            d -= 1
            if d == 0: return s[j + 1:k]
    return None
nrm = lambda t: re.sub(r'\s+', '', (t or '').replace('\\left', '').replace('\\right', '').replace('dfrac', 'frac').replace('\\!', '').replace('$', '')).rstrip('.')
res = dict(n_records=len(recs))
usable, bad_box, bad_usable, false_eq = {}, [], [], []
for cid, r in recs.items():
    st, sc = r['stop'], r['score']['score'] if r.get('score') else {}
    seg = st['answer_segment']; eos = st['stop_reason'] == 'native_eos' and st.get('actual_eos_at_stop', True)
    b = last_boxed(seg)
    if sc.get('box_extracted') and b != sc.get('extracted_answer'): bad_box.append(cid)
    u = bool(sc.get('correct')) and eos and b is not None
    usable[cid] = u
    if bool(r['usable']) != u: bad_usable.append(cid)
    if not sc.get('correct') and b is not None and eos and nrm(b) == nrm(gold.get(r['problem_id'])): false_eq.append(cid)
res.update(box_mismatch=len(bad_box), usable_mismatch=len(bad_usable), usable_mismatch_examples=bad_usable[:5],
           judged_wrong_but_string_equal=len(false_eq), transport_flags=dict(collections.Counter(str(r.get('transport')) [:60] for r in recs.values()).most_common(4)))
# coverage
att = collections.defaultdict(set)
for cid in recs: q, a = cid.split('::attempt'); att[q].add(int(a))
res['n400_all16'] = all(att[q] == set(range(1, 17)) for q in q400)
s400 = set(q400); cond_ok = True; extra = []
for q in q3200:
    if q in s400: continue
    a = sorted(att[q]); exp = []
    for k in range(1, 5):
        exp.append(k)
        if usable.get(f'{q}::attempt{k:02d}'): break
    if a != exp: cond_ok = False; extra.append((q, a, exp))
res['n3200_conditional_attempts_exact'] = cond_ok; res['conditional_examples'] = extra[:5]
res['no_unexpected_questions'] = set(att) <= set(q3200)
# K1 reselection
def k1(q):
    for k in range(1, 5):
        c = f'{q}::attempt{k:02d}'
        if usable.get(c): return c, False
    return f'{q}::attempt01', True
for n, qs in (('400', q400), ('3200', q3200)):
    mine = [k1(q) for q in qs]
    rows = json.load(open(f'{T}/sel/n{n}_k1/rows.json'))
    res[f'n{n}_k1_equal'] = [m[0] for m in mine] == [r['path_id'] for r in rows]
    res[f'n{n}_fallback'] = sum(m[1] for m in mine); res[f'n{n}_fallback_rate'] = round(sum(m[1] for m in mine) / len(qs), 4)
    res[f'n{n}_response_bytes_ok'] = all(r['response'] == recs[r['path_id']]['stop']['answer_segment'] for r in rows)
    plan = json.load(open(f'{T}/sel/n{n}_k1/plan.json')); enc = json.load(open(f'{T}/sel/n{n}_k1/encoded.json'))
    nsup = {e['path_id']: e['n_supervised'] for e in enc}; cnt = collections.Counter(i for u in plan['updates'] for i in u)
    res[f'n{n}_plan'] = dict(once=sum(nsup.values()), targets=sum(nsup[p] * x for p, x in zip(plan['row_path_ids'], plan['row_exposures'])),
        plan_targets=plan['supervised_targets'], updates=len(plan['updates']), counts_ok=all(cnt[i] == x for i, x in enumerate(plan['row_exposures'])),
        exp=(min(plan['row_exposures']), max(plan['row_exposures'])), eos_last=all(e['input_ids'][-1] == 151643 == e['labels'][-1] for e in enc),
        labels_ok=all(sum(t != -100 for t in e['labels']) == e['n_supervised'] for e in enc), seed=plan['seed'], lr=plan['lr_vector_sha256'][:8])
res['k1_400_is_prefix_of_3200'] = json.load(open(f'{T}/sel/n400_k1/rows.json')) == json.load(open(f'{T}/sel/n3200_k1/rows.json'))[:400]
# K4/K8 inventories (usable-only), conflicts
key = lambda t: re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', t)).strip()
for K in (4, 8):
    inv, conf = [], []
    for q in q400:
        seen, picked = set(), []
        for a in range(1, 17):
            c = f'{q}::attempt{a:02d}'
            if not usable[c]: continue
            kk = key(recs[c]['stop']['answer_segment'])
            if kk in seen: continue
            seen.add(kk); picked.append(c)
            if len(picked) == K: break
        inv.append(picked)
        if not picked or picked[0] != k1(q)[0]: conf.append(q)
    res[f'k{K}_N'] = sum(map(len, inv)); res[f'k{K}_Pcov'] = sum(1 for p in inv if p); res[f'k{K}_underfilled'] = sum(len(p) < K for p in inv)
    res[f'k{K}_nesting_conflicts'] = len(conf)
print(json.dumps(res, indent=1)); json.dump(res, open(f'{T}/A1_T7_RESULT.json', 'w'), indent=1)
