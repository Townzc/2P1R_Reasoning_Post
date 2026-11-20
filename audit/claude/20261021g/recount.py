"""Independent recount of OT3 completeness diagnostic journals (Claude). Usage: recount.py D DISP OUT"""
import sys, json, gzip, collections, math, hashlib
D, DISP, OUT = sys.argv[1:4]
R = {}
cat = collections.Counter(); tdist = collections.Counter(); starts = 0; n = 0
pids = set(); per = collections.defaultdict(lambda: [0, 0, 0]); chars = collections.defaultdict(list)
bad = collections.Counter()
def expected_cat(r):
    t = r['t']
    if r['complete']: return 'complete'
    if t == 0 and not r['boxed_any']: return 'N1'
    if t == 0 and r['boxed_any'] and not r['boxed_last2000']: return 'N2'
    if t >= 1 and not r['boxed_after_last_think'] and r['boxed_any']: return 'N3'
    if t >= 1 and not r['boxed_any']: return 'N4'
    return 'N5'
for line in gzip.open(f'{D}/RESPONSE_DIAGNOSTICS.jsonl.gz', 'rt'):
    r = json.loads(line); n += 1
    if r['path_id'] in pids: bad['dup_path'] += 1
    pids.add(r['path_id'])
    cat[r['category']] += 1; tdist[r['t']] += 1; starts += r['starts_with_think']
    bad['cat_mismatch'] += expected_cat(r) != r['category']
    # frozen rule: region after last </think> if present else last 2000 chars
    frozen = r['boxed_after_last_think'] if r['t'] >= 1 else r['boxed_last2000']
    bad['complete_flag_vs_rule'] += bool(frozen) != r['complete']
    rp = r['boxed_after_last_think'] if r['t'] >= 1 else r['boxed_any']
    bad['rprime_flag'] += bool(rp) != r['Rprime_complete']
    bad['t0_after_not_null'] += r['t'] == 0 and r['boxed_after_last_think'] is not None
    p = per[r['parent_sha256']]; p[0] += 1; p[1] += r['complete']; p[2] += r['Rprime_complete']
    chars[r['category']].append(r['characters'])
R['responses'] = n; R['unique_path_ids'] = len(pids); R['categories'] = dict(cat)
R['t'] = dict(tdist); R['starts_with_think'] = starts; R['bad'] = dict(bad)
R['parents'] = len(per); R['all_cardinality16'] = all(v[0] == 16 for v in per.values())
R['hist_complete'] = dict(sorted(collections.Counter(v[1] for v in per.values()).items()))
R['rprime_all16'] = sum(v[2] == 16 for v in per.values())
def q(v, p):
    v = sorted(v); a = (len(v) - 1) * p; lo, hi = math.floor(a), math.ceil(a); return v[lo] + (v[hi] - v[lo]) * (a - lo)
R['char_quantiles'] = {k: {str(int(p * 100)): q(v, p) for p in (.1, .5, .9, .99)} for k, v in chars.items()}
R['n1_near_max'] = {'max': max(chars['N1']), 'frac_ge_60000': sum(x >= 60000 for x in chars['N1']) / len(chars['N1'])}
# parent journal consistency
pj = [json.loads(l) for l in open(f'{D}/PARENT_DIAGNOSTICS.jsonl')]
R['parent_journal_rows'] = len(pj)
R['parent_journal_vs_response'] = sum(per[x['parent_sha256']][1] != x['original_complete_count'] or (per[x['parent_sha256']][2] == 16) != x['Rprime_all16_complete'] for x in pj)
# cross-check with original dispositions (independent source)
disp = {json.loads(l)['parent_sha256']: json.loads(l) for l in open(DISP)}
R['disposition_parents_match'] = set(disp) == set(per)
inc = sum(d['flags'].get('incomplete') is True for d in disp.values())
R['orig_incomplete_parents'] = inc; R['diag_parents_lt16_complete'] = sum(v[1] < 16 for v in per.values())
R['incomplete_flag_mismatch'] = sum((per[h][1] < 16) != (d['flags'].get('incomplete') is True) for h, d in disp.items())
elig = {h for h, d in disp.items() if d['eligible']}
over = {h for h, d in disp.items() if d['flags'].get('overlength') is True}
dec = {h for h, d in disp.items() if d['flags'].get('decontamination') is True or d['flags'].get('decontaminated') is True}
R['orig_flag_keys'] = sorted({k for d in disp.values() for k in d['flags']})
rp16 = {h for h, v in per.items() if v[2] == 16}
R['rprime16_and_eligible'] = len(rp16 & elig); R['rprime16_and_overlength'] = len(rp16 & over)
R['rprime16_minus_orig_complete16'] = len(rp16 - {h for h, v in per.items() if v[1] == 16})
R['orig16_not_rprime16'] = len({h for h, v in per.items() if v[1] == 16} - rp16)
R['n2_frac_incomplete'] = cat['N2'] / (n - cat['complete'])
json.dump(R, open(OUT, 'w'), indent=1); print(json.dumps(R, indent=1))
