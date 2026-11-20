"""Independent A1 of P011 AM (D) constructed inputs (Claude). Usage: python3 -I a1_am.py X_DIR OUT"""
import sys, json, hashlib, unicodedata, collections, re
X, OUT = sys.argv[1:3]
L = lambda f: json.load(open(f'{X}/{f}'))
J = lambda f: [json.loads(l) for l in open(f'{X}/{f}')]
sha = lambda f: hashlib.sha256(open(f'{X}/{f}', 'rb').read()).hexdigest()
res = {}
man = L('MANIFEST.json')['files']
res['manifest_bad'] = [n for n, v in man.items() if n in __import__('os').listdir(X) and sha(n) != v['sha256']]
raw = {r['path_id']: r for r in J('SELECTED_RAW.jsonl')}
enc = {e['path_id']: e for e in J('ENCODED.jsonl')}
inv = L('CELL_INVENTORY.json'); dose = L('FROZEN_DOSE.json'); disp = J('PARENT_DISPOSITIONS.jsonl'); fc = L('FILTER_COUNTS.json')
res['n_raw'], res['n_enc'] = len(raw), len(enc)
cells = inv['cells']
res['cell_sizes'] = {k: len(v) for k, v in cells.items()}
pk = lambda t: unicodedata.normalize('NFKC', t).strip()
hid = lambda t: hashlib.sha256(t.encode()).hexdigest()
# parent identity / pairing
d1, d2 = cells['D1'], cells['D2']
par1 = [hid(pk(raw[p]['question'])) for p in d1]; par2 = [hid(pk(raw[p]['question'])) for p in d2]
res['pairs_same_parent_in_order'] = par1 == par2
res['selected_parent_list_matches_filter'] = par1 == fc['selected_parent_sha256']
res['teacher_sources'] = dict(collections.Counter(p.split(':')[0] for p in d1)), dict(collections.Counter(p.split(':')[0] for p in d2))
res['unique_parents'] = len(set(par1))
# dispositions: order and eligibility
elig = [d['parent_sha256'] for d in disp if d['eligible']]
res['dispositions_examined'] = len(disp); res['dispositions_eligible'] = len(elig)
res['positions_contiguous'] = [d['candidate_position'] for d in disp] == list(range(1, len(disp) + 1))
res['selected_equals_eligible_in_candidate_order'] = elig == par1
res['last_examined_is_eligible_1024th'] = disp[-1]['eligible'] and len(elig) == 1024
res['chosen_rows_match'] = all(d['chosen']['am_thinking'] == a and d['chosen']['am_qwen3'] == b for d, a, b in zip([d for d in disp if d['eligible']], d1, d2))
flagc = collections.Counter()
for d in disp:
    for k, v in d['flags'].items():
        flagc[k] += v is True
res['flag_counts_recomputed'] = dict(flagc); res['filter_counts_reported'] = fc['counts']
# completeness / decontam (independent re-implementation)
def region(t): return t.rsplit('</think>', 1)[-1] if '</think>' in t else t[-2000:]
res['all_complete'] = all('\\boxed{' in region(raw[p]['response']) for p in d1 + d2)
bench = L('BENCHMARKS.json')
def grams(t):
    w = pk(t).split(); return {tuple(w[i:i + 13]) for i in range(max(0, len(w) - 12))}
bidx = set().union(*(grams(b['problem']) for b in bench)); bexact = {pk(b['problem']) for b in bench}
res['decontam_hits_in_selected'] = sum(pk(raw[p]['question']) in bexact or bool(grams(raw[p]['question']) & bidx) for p in d1)
res['benchmark_counts'] = dict(collections.Counter(b['benchmark'] for b in bench))
# encoding structure
IM_END, NL = 151645, 198
bad = collections.Counter(); prefixes = {}
for p in d1 + d2:
    e = enc[p]; ids, lab = e['input_ids'], e['labels']
    s, t = e['assistant_start'], e['assistant_end']
    ok = (len(ids) == len(lab) == e['n_processed'] <= 16384 and all(x == -100 for x in lab[:s]) and lab[s:t] == ids[s:t]
          and all(x == -100 for x in lab[t:]) and ids[t - 1] == IM_END and lab[t - 1] == IM_END and t - s == e['n_supervised']
          and len(ids) - t == 1 and ids[-1] == NL and IM_END not in ids[s:t - 1])
    bad['structure'] += not ok
    prefixes.setdefault(e['parent_sha256'], set()).add(tuple(ids[:s]))
    bad['parent_sha_mismatch'] += e['parent_sha256'] != hid(pk(raw[p]['question']))
res['encoding_bad'] = dict(bad)
res['same_prefix_ids_across_teachers'] = all(len(v) == 1 for v in prefixes.values())
first = next(iter(prefixes.values())); fp = list(next(iter(first)))
res['prefix_head_ids'] = fp[:12]
res['all_prefixes_share_system_head'] = all(list(next(iter(v)))[:len(fp[:20])] == fp[:20] for v in prefixes.values())
res['max_len'] = max(enc[p]['n_processed'] for p in d1 + d2)
res['verify_score_selected'] = {t: collections.Counter(str((raw[p]['metadata']['turn_info'][1] or {}).get('verify_score')) for p in c).most_common(4) for t, c in (('D1', d1), ('D2', d2))}
res['response_starts_think'] = {t: sum(raw[p]['response'].lstrip().startswith('<think>') for p in c) for t, c in (('D1', d1), ('D2', d2))}
res['response_has_answer_tag'] = {t: sum('<answer>' in raw[p]['response'] for p in c) for t, c in (('D1', d1), ('D2', d2))}
# dose & plans
once = {k: sum(enc[p]['n_supervised'] for p in v) for k, v in cells.items()}
res['once_recomputed'] = once; res['dose'] = dose
res['B_is_max'] = dose['B'] == max(once.values()) and dose['U'] == (dose['B'] + 63999) // 64000
import random
for k in ('D1', 'D2'):
    pl = L(f'{k}_PLAN.json'); rows = pl['row_path_ids']; n = len(rows)
    assert rows == cells[k]
    lengths = [enc[p]['n_supervised'] for p in rows]
    stream = [i for u in pl['updates'] for i in u]
    q = pl['q']; cnt = collections.Counter(stream)
    passes_ok = all(sorted(stream[e * n:(e + 1) * n]) == list(range(n)) for e in range(q))
    exp_pass = []
    for e in range(q):
        o = list(range(n)); random.Random(f'17:pass:{e}').shuffle(o); exp_pass += o
    extras = stream[q * n:]
    res[f'{k}_plan'] = dict(q=q, n=n, updates=len(pl['updates']), U_ok=len(pl['updates']) == dose['U'],
        tokens=sum(lengths[i] for i in stream), tokens_eq_B=sum(lengths[i] for i in stream) == dose['B'],
        exposures_q_q1=set(cnt.values()) <= {q, q + 1} and len(cnt) == n, passes_are_permutations=passes_ok,
        passes_match_seeded_shuffle=stream[:q * n] == exp_pass, extras=len(extras), extras_unique=len(set(extras)) == len(extras),
        nonempty_updates=all(pl['updates']),
        update_tokens_min_max=(min(sum(lengths[i] for i in u) for u in pl['updates']), max(sum(lengths[i] for i in u) for u in pl['updates'])),
        exposures_field_ok=pl['exposures'] == [cnt[i] for i in range(n)])
json.dump(res, open(OUT, 'w'), indent=1, ensure_ascii=False); print(json.dumps(res, indent=1, ensure_ascii=False))
