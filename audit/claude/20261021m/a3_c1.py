"""Independent A3 of C1 r2 NLL results (Claude). Usage: a3_c1.py PAYLOAD C1INPUTS OUT"""
import sys, json, hashlib, math, collections, os, glob
X, IN, OUT = sys.argv[1:4]
shaf = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
dig = lambda v: hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
R = {}
mem = json.load(open(f'{X}/COMPACT_MEMBERS.json'))
R['members'] = len(mem); R['member_bad'] = sum(shaf(f'{X}/{n}') != v['sha256'] for n, v in mem.items())
# independent task reconstruction from original inputs
tasks = {}; memb = {}
for g in sorted(os.listdir(IN)):
    if not os.path.isdir(f'{IN}/{g}'): continue
    rows = json.load(open(f'{IN}/{g}/rows.json')); enc = json.load(open(f'{IN}/{g}/encoded.json'))
    ms = []
    for r, e in zip(rows, enc):
        k = dig({'input_ids': e['input_ids'], 'labels': e['labels']})
        tasks[k] = (e['input_ids'], e['n_prompt'])
        fb = False if g.startswith('t15') else r['unverified_fallback']
        ms.append((r['path_id'], k, fb))
    memb[g] = ms
saved_m = json.load(open(f'{X}/MEMBERSHIPS.json'))
R['memberships_match'] = {g: [(m['path_id'], m['sequence_sha256'], m['unverified_fallback']) for m in saved_m[g]] == memb[g] for g in memb}
intent = json.load(open(f'{X}/INTENT.json'))
R['task_ids_eq'] = intent['task_ids'] == sorted(tasks); R['chunk_size'] = intent['chunk_size']
# collect all results
res = {}; bad = collections.Counter(); chunks = sorted(os.listdir(f'{X}/chunks'))
for c in chunks:
    ack = json.load(open(f'{X}/chunks/{c}/CONFIRMED.json'))
    plan = json.load(open(f'{X}/chunks/{c}/INTENT.json'))
    bad['chunk_ack_ids'] += [r['sequence_sha256'] for r in ack['records']] != plan['sequence_ids']
    for r in ack['records']:
        p = f'{X}/chunks/{c}/{r["sequence_sha256"]}.RESULT.json'
        bad['result_sha'] += shaf(p) != r['result_file_sha256']
        o = json.load(open(p))['result']; k = o['sequence_sha256']
        ids, P = tasks[k]; n = len(ids) - P; v = o['token_nll']
        bad['len'] += len(v) != n or o['supervised_tokens'] != n or o['target_positions'] != list(range(P, len(ids)))
        bad['finite'] += any((not math.isfinite(x)) or x < 0 for x in v)
        bad['sum'] += abs(math.fsum(v) - o['nll_sum']) > 1e-9 or abs(o['mean_nll'] - math.fsum(v) / n) > 1e-12
        res[k] = (math.fsum(v), n, math.fsum(v) / n, v[-1])
R['chunks'] = len(chunks); R['chunk_sizes'] = collections.Counter(len(json.load(open(f'{X}/chunks/{c}/INTENT.json'))['sequence_ids']) for c in chunks)
R['results'] = len(res); R['all_tasks_covered'] = set(res) == set(tasks); R['bad'] = dict(bad)
def q(vals, p):
    s = sorted(vals); a = (len(s) - 1) * p; lo, hi = math.floor(a), math.ceil(a); return s[lo] + (s[hi] - s[lo]) * (a - lo)
summ = json.load(open(f'{X}/DESCRIPTIVE_SUMMARY.json'))
mine = {}; diffs = collections.Counter()
for g, ms in memb.items():
    mine[g] = {}
    for sub, sel in (('all', ms), ('nonfallback', [m for m in ms if not m[2]]), ('fallback', [m for m in ms if m[2]])):
        if not sel:
            mine[g][sub] = None; diffs['null_mismatch'] += summ['groups'][g][sub]['answers'] != 0; continue
        tok = sum(res[m[1]][1] for m in sel); nll = math.fsum(res[m[1]][0] for m in sel) / tok
        means = [res[m[1]][2] for m in sel]
        qs = {p: q(means, p) for p in (0., .1, .25, .5, .75, .9, 1.)}
        mine[g][sub] = dict(answers=len(sel), tokens=tok, nll=nll, ppl=math.exp(nll), median_answer=qs[.5], eos_mean=sum(res[m[1]][3] for m in sel) / len(sel))
        s = summ['groups'][g][sub]
        diffs['answers'] += s['answers'] != len(sel); diffs['tokens'] += s['supervised_tokens'] != tok
        diffs['nll'] += abs(s['token_weighted_nll'] - nll) > 1e-12
        diffs['quant'] += any(abs(s['answer_mean_nll_quantiles'][str(p)] - v) > 1e-12 for p, v in qs.items())
R['summary_recompute_diffs'] = dict(diffs); R['recomputed'] = mine
tim = json.load(open(f'{X}/COMPLETE_ITERATION_TIMES.json'))['cycles']
R['cycles'] = dict(n=len(tim), max=max(c['elapsed_seconds'] for c in tim), sum=sum(c['elapsed_seconds'] for c in tim))
R['load_window'] = json.load(open(f'{X}/LOAD_WINDOW.json'))
ml = json.load(open(f'{X}/MODEL_LOADED.json')); R['model_loaded'] = {k: ml[k] for k in ('model', 'forward', 'optimizer_created', 'adapter_loaded', 'new_tokenization', 'device')}
json.dump(R, open(OUT, 'w'), indent=1, default=str); print(json.dumps({k: v for k, v in R.items() if k != 'recomputed'}, indent=1, default=str))
for g in sorted(mine): print(g, {s: (None if v is None else (v['answers'], v['tokens'], round(v['nll'], 4), round(v['median_answer'], 4))) for s, v in mine[g].items()})
