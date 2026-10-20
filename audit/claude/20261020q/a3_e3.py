"""Independent A3 of P010 E3 results (Claude).
Usage: python3 -I a3_e3.py RESULT_DIR RAW_EXTRACT FROZEN_IN T72RAW SOURCE_DIR OUT"""
import sys, json, glob, re, hashlib, collections, itertools
R, X, IN, T72, SRC, OUT = sys.argv[1:7]
sys.path.insert(0, SRC)
from experiments.p010.e3_metrics import rouge_l, equation_set   # primitives validated in 20261020o
from experiments.p010.dataset_selection import text_key
L = lambda f: json.load(open(f))
sha = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
res = {}
# ---------- manifest / bindings
man = L(f'{R}/MANIFEST.json')
res['manifest_sha'] = sha(f'{R}/MANIFEST.json')
import os
res['manifest_files_checked'] = sum(1 for n in man if os.path.isfile(f'{R}/{n}'))
res['manifest_files_bad'] = [n for n, v in man.items() if os.path.isfile(f'{R}/{n}') and sha(f'{R}/{n}') != v['sha256']]
res['manifest_entries'] = len(man)
res['spec_sha'] = sha(f'{R}/ORIGINAL_SPEC.json')
res['t08_rows_sha'] = sha(f'{R}/ORIGINAL_T08_ROWS.json')
res['t08_rows_identical_to_A1_frozen_copy'] = sha(f'{R}/ORIGINAL_T08_ROWS.json') == sha(f'{IN}/ORIGINAL_T08_ROWS.json')
res['roster_identical'] = sha(f'{R}/ORIGINAL_ROSTER.json') == sha(f'{IN}/ROSTER.json')
res['gold_identical'] = sha(f'{R}/ORIGINAL_GOLD_SOURCE.json') == sha(f'{IN}/GOLD_SOURCE.json')
# ---------- raw identity vs frozen requests
req = {}
for lab in ('t06', 't10'):
    for r in L(f'{IN}/{lab}_requests.json'): req[r['candidate_id']] = r
raw = {}
for f in sorted(glob.glob(f'{X}/raw/*/*.json')):
    for x in L(f):
        assert x['candidate_id'] not in raw; raw[x['candidate_id']] = x
res['raw_rows'] = len(raw); res['raw_ids_equal_requests'] = set(raw) == set(req)
idbad = [c for c, x in raw.items() if x['prompt_token_ids'] != req[c]['prompt_token_ids'] or x['sampling'] != req[c]['sampling'] or int(x['output_count']) != 1]
res['raw_identity_mismatch'] = len(idbad)
# ---------- decode/stop independent checks
EOS = {151645, 151643}
dec = {d['candidate_id']: d for d in L(f'{R}/DECODED_ROWS.json')}
chk = collections.Counter(); ex = collections.defaultdict(list)
for c, x in raw.items():
    d = dec[c]; st = d['stop']; toks = x['token_ids']; txt = x['backend_text']
    chk['len_match'] += d['physical_returned_tokens'] == len(toks)
    last_eos = bool(toks) and toks[-1] in EOS
    if st['stop_reason'] == 'native_eos':
        ok = last_eos and txt.endswith(('<|im_end|>', '<|endoftext|>'))
        stripped = re.sub(r'(<\|im_end\|>|<\|endoftext\|>)$', '', txt)
        chk['eos_ok'] += ok; chk['eos_seg_equal_stripped'] += st['answer_segment'] == stripped
        if st['answer_segment'] != stripped: ex['eos_seg_diff'].append(c)
        chk['eos_retained_eq_len_minus1'] += st['retained_tokens'] == len(toks) - 1
    elif st['stop_reason'] == 'length_cap':
        chk['cap_ok'] += len(toks) == 1024 and not last_eos
        chk['cap_seg_prefix'] += txt.startswith(st['answer_segment'])
        if not (len(toks) == 1024 and not last_eos): ex['cap_bad'].append(c)
    else:
        chk['other_' + st['stop_reason']] += 1
        sp = [t for t in toks if t >= 151643]
        if not sp or (last_eos and sp == [toks[-1]]): ex['invalid_special_unexplained'].append(c)
        chk['other_seg_prefix'] += txt.startswith(st['answer_segment'])
    chk['answer_text_eq_segment'] += d['answer_text'] == st['answer_segment']
res['decode_checks'] = dict(chk); res['decode_examples'] = {k: v[:5] for k, v in ex.items()}
# ---------- scoring
def last_boxed(s):
    i = max(s.rfind('\\boxed'), s.rfind('\\fbox'))
    if i < 0: return None
    j = s.find('{', i); d = 0
    if j < 0: return None
    for k in range(j, len(s)):
        e = s[k - 1] == '\\'
        if s[k] == '{' and not e: d += 1
        elif s[k] == '}' and not e:
            d -= 1
            if d == 0: return s[j + 1:k]
    return None
nrm = lambda t: re.sub(r'\s+', '', (t or '').replace('\\left', '').replace('\\right', '').replace('dfrac', 'frac').replace('\\!', '').replace('$', '')).rstrip('.')
gold_src = {g['problem_id']: g for g in L(f'{IN}/GOLD_SOURCE.json')}
srows = {r['id']: r for r in L(f'{R}/SCORING_ROWS.json')}
sc = {s['id']: s for s in L(f'{R}/ALL_SCORED_ROWS.json')}
res['scored_rows'] = len(sc); res['score_ids_equal'] = set(sc) == set(raw) == set(srows)
sk = collections.Counter(); sex = collections.defaultdict(list); correct = collections.Counter(); status = collections.Counter()
for c, s in sc.items():
    v = s['score']; d = dec[c]; seg = d['stop']['answer_segment']; g = srows[c]['gold']; lab = d['temperature_label']
    gb = last_boxed(gold_src[d['problem_id']]['solution'])
    sk['gold_eq_lastbox_solution'] += g == gb
    sk['scoring_seg_eq_decoded'] += srows[c]['answer_segment'] == seg and srows[c]['stop_reason'] == d['stop']['stop_reason']
    b = last_boxed(seg); cor = v.get('correct') is True
    correct[lab] += cor; status[v.get('status')] += 1
    if v.get('box_extracted') and b != v.get('extracted_answer'): sk['box_mismatch'] += 1; sex['box_mismatch'].append((c, b, v.get('extracted_answer')))
    if cor and d['stop']['stop_reason'] != 'native_eos': sk['non_eos_marked_correct'] += 1
    if (not cor) and b is not None and d['stop']['stop_reason'] == 'native_eos' and nrm(b) == nrm(g): sk['wrong_but_string_equal'] += 1; sex['wrong_but_string_equal'].append((c, b, g))
    if cor and b is not None and nrm(b) != nrm(g): sk['right_string_differs'] += 1; sex['right_string_differs'].append((b, g))
    sym = (v.get('symbolic') or {}).get('status')
    if sym in ('symbolic_timeout', 'tool_error', 'outer_timeout', 'parse_failure'): sk['symbolic_' + sym] += 1
    if v.get('fallback_used'): sk['fallback_used'] += 1
    if v.get('string_symbolic_disagreement'): sk['string_symbolic_disagreement'] += 1
res['score_checks'] = dict(sk); res['correct_by_temp'] = dict(correct); res['status_counts'] = dict(status)
rnd = collections.defaultdict(list)
for k, v in sex.items(): rnd[k] = v[:25]
res['score_examples'] = rnd
# ---------- T0.8 physical lengths vs original T72 raw archive
t72 = {}
for f in glob.glob(f'{T72}/raw/*.json'):
    for x in L(f): t72[x['candidate_id']] = x
pl = L(f'{R}/ORIGINAL_T08_PHYSICAL_LENGTHS.json')
res['t08_lengths_n'] = len(pl)
res['t08_lengths_match_original_raw'] = sum(p['physical_returned_tokens'] == len(t72[p['candidate_id']]['token_ids']) for p in pl)
# ---------- independent metric aggregation
rows = []
for x in L(f'{R}/ORIGINAL_T08_ROWS.json'):
    o = x['original_record']; rows.append(dict(o, temperature_label='t08'))
plen = {p['candidate_id']: p['physical_returned_tokens'] for p in pl}
for c, d in dec.items(): rows.append(dict(d, score=sc[c]))
def usable(r):
    v = r['score']['score']
    return r['stop']['stop_reason'] == 'native_eos' and v.get('box_extracted') is True and v.get('parsed') is True and v.get('correct') is True and r.get('gold_supported', True)
mine = {}
for lab in ('t06', 't08', 't10'):
    part = [r for r in rows if r['temperature_label'] == lab]
    byq = collections.defaultdict(list)
    for r in part: byq[r['problem_id']].append(r)
    phys = sum(plen[r['candidate_id']] if lab == 't08' else r['physical_returned_tokens'] for r in part)
    uu = 0; allp = []; uup = []; qall = []; quu = []
    for q, v in byq.items():
        v = sorted(v, key=lambda r: r['attempt']); assert [r['attempt'] for r in v] == list(range(1, 9))
        seen = set(); uniq = []
        for r in v:
            k = text_key(r['answer_text'])
            if usable(r) and k not in seen: seen.add(k); uniq.append(r)
        uu += len(uniq)
        def sims(rs):
            out = []
            for a, b in itertools.combinations(rs, 2):
                A, B = equation_set(a['answer_text']), equation_set(b['answer_text']); U = A | B
                out.append((rouge_l(a['answer_text'], b['answer_text']), len(A & B) / len(U) if U else 1.0))
            return out
        s1 = sims(v); s2 = sims(uniq); allp += s1; uup += s2
        qall.append(sum(x[0] for x in s1) / len(s1))
        if s2: quu.append(sum(x[0] for x in s2) / len(s2))
    mine[lab] = dict(n=len(part), native_eos=sum(r['stop']['stop_reason'] == 'native_eos' for r in part),
        correct=sum(bool(r['score']['score'].get('correct')) for r in part), usable_unique=uu, physical_tokens=phys,
        tokens_per_uu=phys / uu, pooled_rougeL_all=sum(x[0] for x in allp) / len(allp), pooled_jacc_all=sum(x[1] for x in allp) / len(allp),
        uu_pairs=len(uup), uu_q_with_pairs=len(quu), pooled_rougeL_uu=sum(x[0] for x in uup) / len(uup), pooled_jacc_uu=sum(x[1] for x in uup) / len(uup),
        eqq_rougeL_uu=sum(quu) / len(quu))
M = L(f'{R}/METRICS.json')['temperatures']
cmp = {}
for lab, m in mine.items():
    t = M[lab]; s = t['similarities']
    pairs = dict(native_eos=(m['native_eos'], t['native_eos']), correct=(m['correct'], t['correct']), usable_unique=(m['usable_unique'], t['usable_unique']),
        physical_tokens=(m['physical_tokens'], t['physical_tokens']), tokens_per_uu=(m['tokens_per_uu'], t['physical_tokens_per_usable_unique']),
        rougeL_all=(m['pooled_rougeL_all'], s['all']['pooled_rouge_L']), jacc_all=(m['pooled_jacc_all'], s['all']['pooled_equation_jaccard']),
        uu_pairs=(m['uu_pairs'], s['usable_unique']['pair_count']), uu_q=(m['uu_q_with_pairs'], s['usable_unique']['questions_with_pairs']),
        rougeL_uu=(m['pooled_rougeL_uu'], s['usable_unique']['pooled_rouge_L']), jacc_uu=(m['pooled_jacc_uu'], s['usable_unique']['pooled_equation_jaccard']),
        eqq_rougeL_uu=(m['eqq_rougeL_uu'], s['usable_unique']['equal_question_rouge_L']))
    cmp[lab] = {k: dict(mine=a, theirs=b, ok=abs(a - b) < 1e-9) for k, (a, b) in pairs.items()}
res['metrics_replay'] = cmp
res['metrics_all_ok'] = all(v['ok'] for c in cmp.values() for v in c.values())
# ---------- seeds/questions shared across temps
seeds = collections.defaultdict(set)
for c, x in raw.items(): seeds[c.split('/', 2)[2]].add(x['sampling']['seed'])
for x in L(f'{R}/ORIGINAL_T08_ROWS.json'):
    cid = x['original_candidate_id']; seeds[cid].add(t72[cid]['sampling']['seed'])
res['same_seed_all_three_temps'] = all(len(v) == 1 for v in seeds.values()) and len(seeds) == 1600
json.dump(res, open(OUT, 'w'), indent=1, ensure_ascii=False); print(json.dumps({k: v for k, v in res.items() if k not in ('score_examples',)}, indent=1, ensure_ascii=False)[:9000])
