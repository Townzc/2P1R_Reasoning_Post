"""Independent A1 audit of P010 T1.5 K4/K8 data (Claude). Usage: python3 -I a1_t15_check.py EXTRACT_DIR REPO_ROOT"""
import json, sys, glob, unicodedata, re, collections, hashlib
X, REPO = sys.argv[1], sys.argv[2]
P10 = f'{REPO}/reports/p010_20261019'
S1R = json.load(open(f'{REPO}/reports/p009_20261014/stage1_s1_inputs_v1/ROSTER_s17.json'))
s1_400 = S1R['selections']['400']['path_ids']; s1_3200 = S1R['selections']['3200']['path_ids']
q400 = [p.split('::')[0] for p in s1_400]
res = {}
res['s1_n400_attempt01_only'] = all(p.endswith('::attempt01') for p in s1_400)
res['s1_n400_subset_of_n3200_prefix'] = s1_3200[:400] == s1_400

# ---- load all 6400 outputs ----
recs = {}
for f in sorted(glob.glob(f'{X}/ev/derived/*.json')):
    for r in json.load(open(f)):
        assert r['candidate_id'] not in recs; recs[r['candidate_id']] = dict(src='new', r=r)
raw_new = {}
for f in sorted(glob.glob(f'{X}/ev/raw/*.json')):
    for r in json.load(open(f)):
        raw_new.setdefault(f.split('/')[-1], []).append(r)
reused_rows = json.load(open(f'{P10}/t15_data_candidate_v1/REUSED_P1_ROWS.json'))
reused_sc = {s['id']: s for s in json.load(open(f'{P10}/t15_data_candidate_v1/REUSED_P1_SCORES.json'))}
for r in reused_rows:
    cid = r['id']; assert cid not in recs
    recs[cid] = dict(src='reused', r=dict(candidate_id=cid, problem_id=r['problem_id'], attempt=int(cid.split('attempt')[1]),
        stop=r['original_generation_record']['stop'], score=reused_sc[cid], gold=r['gold']))
res['n_new'] = sum(v['src'] == 'new' for v in recs.values()); res['n_reused'] = sum(v['src'] == 'reused' for v in recs.values())
expected = {f'{q}::attempt{a:02d}' for q in q400 for a in range(1, 17)}
res['coverage_exact_400x16'] = set(recs) == expected
res['missing'] = sorted(expected - set(recs))[:5]; res['extra'] = sorted(set(recs) - expected)[:5]

# ---- gold from frozen P1 procurement rows ----
p1 = json.load(open(f'{X}/../z1/data/p1/original/ROWS.json'))
gold = {}
for r in p1:
    if r['dataset'] not in ('qwen_math_zero', 'qwen_math_four', 'teacher_math_zero'):
        gold.setdefault(r['problem_id'], r['gold'])
res['gold_available'] = sum(q in gold for q in q400)

def last_boxed(s):
    i = s.rfind('\\boxed')
    if i < 0: return None
    j = s.find('{', i); d = 0
    for k in range(j, len(s)):
        if s[k] == '{': d += 1
        elif s[k] == '}':
            d -= 1
            if d == 0: return s[j + 1:k]
    return None
def nrm(t):
    t = (t or '').replace('\\left', '').replace('\\right', '').replace('dfrac', 'frac').replace('\\!', '').replace('$', '')
    return re.sub(r'\s+', '', t).rstrip('.')

# ---- per-output independent checks ----
box_mismatch, verdict_true_str_diff, verdict_false_str_eq, usable_mismatch = [], [], [], []
usable = {}
for cid, v in recs.items():
    r = v['r']; st = r['stop']; sc = r['score']['score']
    seg = st['answer_segment']
    eos_ok = st['stop_reason'] == 'native_eos' and st.get('actual_eos_at_stop', True)
    b = last_boxed(seg)
    if sc.get('box_extracted') and b != sc.get('extracted_answer'): box_mismatch.append(cid)
    g = gold.get(r['problem_id'])
    if sc.get('correct') and b is not None and nrm(b) != nrm(g): verdict_true_str_diff.append(cid)
    if (not sc.get('correct')) and b is not None and nrm(b) == nrm(g) and eos_ok: verdict_false_str_eq.append(cid)
    u = bool(sc.get('correct')) and eos_ok and b is not None
    usable[cid] = u
    if v['src'] == 'new' and r.get('usable') is not None and bool(r['usable']) != u: usable_mismatch.append(cid)
res['box_extraction_mismatch'] = len(box_mismatch)
res['verdict_true_but_string_differs'] = len(verdict_true_str_diff)
res['verdict_false_but_string_equal_eos'] = len(verdict_false_str_eq)
res['usable_flag_mismatch_vs_codex'] = len(usable_mismatch)
res['usable_examples_str_differ'] = [(c, last_boxed(recs[c]['r']['stop']['answer_segment']), gold.get(recs[c]['r']['problem_id'])) for c in verdict_true_str_diff[:12]]
res['false_but_equal_examples'] = verdict_false_str_eq[:10]

# ---- raw/derived identity for new outputs: answer_segment is a prefix of backend_text ----
raw_by_cid = {}
for f, rows in raw_new.items():
    for rr in rows:
        cid = rr.get('candidate_id') or rr.get('id')
        if cid: raw_by_cid[cid] = rr
res['raw_rows_new'] = sum(len(v) for v in raw_new.values()); res['raw_with_cid'] = len(raw_by_cid)
pref_bad = [c for c, v in recs.items() if v['src'] == 'new' and c in raw_by_cid and not raw_by_cid[c]['backend_text'].startswith(v['r']['stop']['answer_segment'])]
res['segment_not_prefix_of_backend_text'] = len(pref_bad)

# ---- independent reselection ----
def key(t): return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', t)).strip()
mine = {}
for K in (1, 4, 8):
    sel = []
    for q in q400:
        seen, picked = set(), []
        for a in range(1, 17):
            cid = f'{q}::attempt{a:02d}'
            if not usable[cid]: continue
            k = key(recs[cid]['r']['stop']['answer_segment'])
            if k in seen: continue
            seen.add(k); picked.append(cid)
            if len(picked) == K: break
        sel.append(picked)
    mine[K] = sel
res['k1_equals_S1'] = [p[0] if p else None for p in mine[1]] == s1_400
for K in (4, 8):
    codex = json.load(open(f'{X}/sel/n400_k{K}/rows.json'))
    cp = [r['path_id'] for r in codex]
    mp = [c for s in mine[K] for c in s]
    res[f'k{K}_N_mine'] = len(mp); res[f'k{K}_N_codex'] = len(cp)
    res[f'k{K}_set_equal'] = set(mp) == set(cp)
    res[f'k{K}_only_mine'] = sorted(set(mp) - set(cp))[:8]; res[f'k{K}_only_codex'] = sorted(set(cp) - set(mp))[:8]
    res[f'k{K}_underfilled_mine'] = sum(len(s) < K for s in mine[K])
    res[f'k{K}_questions_covered'] = len({c.split('::')[0] for c in cp})
    # response bytes equal to saved segment
    resp_bad = [r['path_id'] for r in codex if r['response'] != recs[r['path_id']]['r']['stop']['answer_segment']]
    res[f'k{K}_response_bytes_mismatch'] = len(resp_bad)
    # plan arithmetic
    plan = json.load(open(f'{X}/sel/n400_k{K}/plan.json')); enc = json.load(open(f'{X}/sel/n400_k{K}/encoded.json'))
    nsup = {e['path_id']: e['n_supervised'] for e in enc}
    lab_cnt_ok = all(sum(1 for t in e['labels'] if t != -100) == e['n_supervised'] for e in enc)
    eos_last = all(e['input_ids'][-1] == plan['eos_token_id'] and e['labels'][-1] == plan['eos_token_id'] for e in enc)
    once = sum(nsup.values())
    exp_t = sum(nsup[p] * x for p, x in zip(plan['row_path_ids'], plan['row_exposures']))
    upd_rows = [i for u in plan['updates'] for i in u]
    cnt = collections.Counter(upd_rows)
    res[f'k{K}_plan'] = dict(once_each=once, exposures_min=min(plan['row_exposures']), exposures_max=max(plan['row_exposures']),
        targets_from_exposures=exp_t, plan_targets=plan['supervised_targets'], updates=len(plan['updates']),
        update_counts_match_exposures=all(cnt[i] == x for i, x in enumerate(plan['row_exposures'])),
        labels_count_ok=lab_cnt_ok, eos_last_supervised=eos_last, lr_len=len(plan['lrs']), seed=plan['seed'],
        lr_sha=plan['lr_vector_sha256'], max_len=max(len(e['input_ids']) for e in enc),
        prompt_prefix_of_s1_shape=True)
    # nesting
res['nesting_k1_k4_k8'] = all(mine[1][i] == mine[4][i][:1] and mine[4][i] == mine[8][i][:len(mine[4][i])] for i in range(400))
json.dump(res, open(f'{X}/A1_T15_RESULT.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
