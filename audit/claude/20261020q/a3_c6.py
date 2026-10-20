"""Independent A3 of P010 C6 cue benchmark (Claude).
Usage: python3 -I a3_c6.py SCR REPO OUT   (SCR has inp/ old/ new/ j/ extracted)"""
import sys, json, glob, re, hashlib, collections, tarfile
import numpy as np
SCR, REPO, OUT = sys.argv[1:4]
P = f'{REPO}/reports/p010_20261019'
C = f'{P}/c6_complete_results_v1'; A = f'{P}/c6_analysis_v1'
L = lambda f: json.load(open(f))
sha = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
CELLS = ['base_math', 'base_gsm', 's1_n400_math', 't72_n400_math']
res = {}
for name, d in (('results', C), ('analysis', A)):
    man = L(f'{d}/MANIFEST.json'); import os
    res[f'{name}_manifest_sha'] = sha(f'{d}/MANIFEST.json')
    res[f'{name}_manifest_bad'] = [n for n, v in man.items() if os.path.isfile(f'{d}/{n}') and sha(f'{d}/{n}') != v['sha256']]
    res[f'{name}_manifest_checked'] = sum(os.path.isfile(f'{d}/{n}') for n in man)
res['inputs_archive_sha'] = sha(f'{P}/c6_benchmark_runtime_v1/inputs.tar.gz')
res['no_cue_tables_sha'] = sha(f'{SCR}/inp/EXISTING_NO_CUE_TABLES.json')
EOS = {151645, 151643}
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
NUM = re.compile(r'-?\d[\d,]*\.?\d*')
def gsm_mark(seg):
    b = last_boxed(seg)
    if b is not None: return b
    m = None
    for pat in (r'####\s*', r'(?i)the answer is[:\s]*', r'(?i)\banswer\s*:\s*'):
        for mt in re.finditer(pat, seg): m = mt.end() if m is None or mt.end() > m else m
    if m is None: return None
    ns = NUM.findall(seg[m:].split('\n', 1)[0]); return ns[0] if ns else None
def numeq(a, b):
    try: return a is not None and abs(float(a.replace(',', '').rstrip('.').strip('$')) - float(b.replace(',', ''))) < 1e-9
    except ValueError: return False
qtab = {}
for cell in CELLS:
    r = {}; ros = L(f'{SCR}/inp/{cell}.json'); rows = {x['candidate_id']: x for x in ros['rows']}
    rawdir = f'{SCR}/new/raw' if cell == 't72_n400_math' else f'{SCR}/old/cells/{cell}/raw'
    raw = {}
    for f in sorted(glob.glob(rawdir + '/*.json')):
        for x in L(f):
            assert x['candidate_id'] not in raw; raw[x['candidate_id']] = x
    r['roster_rows'] = len(rows); r['raw_rows'] = len(raw); r['raw_ids_eq_roster'] = set(raw) == set(rows)
    bad = 0; cue_ok = 0; nocue_ok = 0
    for c, x in raw.items():
        q = rows[c]
        if x['prompt_token_ids'] != q['input_ids'] or x['sampling'] != q['sampling'] or int(x['output_count']) != 1: bad += 1
        if q['condition'] == 'cue': cue_ok += q['input_ids'] == q['original_input_ids'] + [1249] and q['cue_token_ids'] == [1249]
        else: nocue_ok += q['input_ids'] == q['original_input_ids'] and q['cue_token_ids'] == []
    r['raw_identity_mismatch'] = bad; r['cue_rows_ok'] = cue_ok; r['nocue_rows_ok'] = nocue_ok
    r['conditions'] = dict(collections.Counter((rows[c]['condition'], rows[c]['evaluation']) for c in raw).most_common())
    r['conditions'] = {f'{k[0]}/{k[1]}': v for k, v in collections.Counter((rows[c]['condition'], rows[c]['evaluation']) for c in raw).items()}
    dec = {d['id']: d for d in L(f'{C}/cells/{cell}/DECODED_ROWS.json')}
    sr = {s['id']: s for s in L(f'{C}/cells/{cell}/SCORING_ROWS.json')}
    r['decoded_ids_eq_raw'] = set(dec) == set(raw) == set(sr)
    k = collections.Counter()
    for c, x in raw.items():
        st = dec[c]['stop']; toks = x['token_ids']; txt = x['backend_text']
        k[st['stop_reason']] += 1
        if st['stop_reason'] == 'native_eos':
            k['eos_last_token'] += bool(toks) and toks[-1] in EOS
            k['eos_seg_eq_stripped'] += st['answer_segment'] == re.sub(r'(<\|im_end\|>|<\|endoftext\|>)$', '', txt)
        elif st['stop_reason'] == 'length_cap':
            k['cap_1024_noeos'] += len(toks) == 1024 and toks[-1] not in EOS
        k['seg_eq_scoring'] += sr[c]['answer_segment'] == st['answer_segment'] and sr[c]['stop_reason'] == st['stop_reason']
    r['stop_checks'] = dict(k)
    # scores
    qc = L(f'{C}/cells/{cell}/QUESTION_CORRECT.json'); jq = L(f'{SCR}/j/{cell}/QUESTION_CORRECT.json')
    r['question_correct_eq_journal'] = qc == jq
    sk = collections.Counter(); ex = collections.defaultdict(list); counts = {}
    cmap = {(x['condition'], x['evaluation'], x['problem_id']): x['candidate_id'] for x in ros['rows']}
    if ros['task'] == 'math':
        for job in sorted(glob.glob(f'{SCR}/j/{cell}/jobs/*/*/payload/ALL_SCORED_ROWS.json')):
            cond, ev = job.split('/jobs/')[1].split('/')[:2]
            sc = L(job); counts[f'{cond}/{ev}'] = sum(bool(s['score'].get('correct')) for s in sc)
            for s in sc:
                pid = s['id'].split('::', 1)[1]
                c = cmap[(cond, ev, pid)]
                v = s['score']; d = dec[c]; seg = d['stop']['answer_segment']; g = sr[c]['gold']; b = last_boxed(seg)
                cor = v.get('correct') is True
                sk['rows'] += 1
                sk['journal_eq_question_table'] += qc[f'{cond}/{ev}'][pid] == cor
                if v.get('box_extracted') and b != v.get('extracted_answer'): sk['box_mismatch'] += 1; ex['box'].append((c, b, v.get('extracted_answer')))
                if cor and d['stop']['stop_reason'] != 'native_eos': sk['non_eos_correct'] += 1
                if not cor and b is not None and d['stop']['stop_reason'] == 'native_eos' and nrm(b) == nrm(g): sk['wrong_but_string_equal'] += 1; ex['wbse'].append((c, b, g))
                if cor and b is not None and nrm(b) != nrm(g): sk['right_string_differs'] += 1; ex['rsd'].append((b, g))
                st = (v.get('symbolic') or {}).get('status')
                if st and st != 'compared': sk['symbolic_' + st] += 1
                sk['status_' + str(v.get('status'))] += 1
    else:
        gold = {}
        for f in glob.glob(f'{SCR}/j/{cell}/new_scores/*/*.json'):
            cond, ev = f.split('/new_scores/')[1][:-5].split('/')
            sc = L(f); counts[f'{cond}/{ev}'] = sum(bool(s['score']['task_answer_correct']) for s in sc)
            for s in sc:
                c = s['id']; d = dec[c]; st = d['stop']; v = s['score']['task_answer_correct']
                mine = st['stop_reason'] != 'length_cap' and numeq(gsm_mark(st['answer_segment']), sr[c]['gold'])
                sk['rows'] += 1; sk['agree_independent_parser'] += mine == v
                sk['journal_eq_question_table'] += qc[f'{cond}/{ev}'][s['problem_id']] == v
                if mine != v: ex['disagree'].append((c, v, mine, st['stop_reason'], st['answer_segment'][-160:]))
    r['score_checks'] = dict(sk); r['correct_counts'] = counts
    r['examples'] = {kk: vv[:12] for kk, vv in ex.items()}
    r['rsd_unique'] = collections.Counter(map(tuple, ex['rsd'])).most_common() if ex.get('rsd') else []
    r['n_disagree'] = len(ex.get('disagree', []))
    res[cell] = r; qtab[cell] = qc
# no-cue tables vs previously audited sources
nc = L(f'{SCR}/inp/EXISTING_NO_CUE_TABLES.json')
t72 = {}
for s in L(f'{P}/student_results_v1/t72_s17_n400_k1/ALL_SCORED_ROWS.json'):
    ev, pid = s['id'].split('::', 1); t72.setdefault(ev, {})[pid] = bool(s['score'].get('correct'))
res['nocue_t72_eq_audited_student_results'] = all(nc['t72_n400_math'][ev] == t72[ev] for ev in nc['t72_n400_math'])
s1 = {}
for s in L(f'{P}/existing_s1_samples_results_v1/s1_s17_n400/ALL_SCORED_ROWS.json'):
    ev, pid = s['id'].split('::', 1); s1.setdefault(ev, {})[pid] = bool(s['score'].get('correct'))
t = tarfile.open(f'{REPO}/reports/p009_20261014/stage1_s1_results_v1/s1_s17_n400/ORIGINAL_SCORING_EVIDENCE.tar.gz')
s1['greedy'] = {r['id'].split('::', 1)[1]: bool(r['score']['correct']) for r in json.load(t.extractfile('job/payload/ALL_SCORED_ROWS.json'))}
res['nocue_s1_eq_audited'] = all(nc['s1_n400_math'][ev] == s1[ev] for ev in nc['s1_n400_math'])
res['nocue_base_totals'] = dict(math=sum(nc['base_math']['greedy'].values()), gsm=sum(nc['base_gsm']['greedy'].values()))
# paired replay
def vec(cell, cond, metric, ids):
    q = dict(qtab[cell]);
    if cond == 'no_cue':
        for ev, tbl in nc[cell].items(): q.setdefault(f'no_cue/{ev}', tbl)
    if metric == 'greedy': return np.array([float(q[f'{cond}/greedy'][p]) for p in ids])
    return np.array([sum(float(q[f'{cond}/sample{i}'][p]) for i in range(4)) / 4 for p in ids])
pair = {}
for task, cells in (('math', ['base_math', 's1_n400_math', 't72_n400_math']), ('gsm', ['base_gsm'])):
    ids = L(f'{SCR}/inp/{cells[0]}.json')['problem_ids']
    for metric in ('greedy', 'sampled_mean_pass_at_1'):
        rng = np.random.default_rng(20261019); smp = rng.integers(0, len(ids), size=(10000, len(ids)))
        for cell in cells:
            d = vec(cell, 'cue', metric, ids) - vec(cell, 'no_cue', metric, ids)
            dr = d[smp].mean(axis=1) * 100; lo, hi = np.quantile(dr, [.025, .975], method='linear')
            pair[f'{task}/{metric}/{cell}'] = (round(float(d.mean() * 100), 6), round(float(lo), 6), round(float(hi), 6))
theirs = {}
import csv
for row in csv.DictReader(open(f'{A}/PAIRED.csv')):
    theirs[f"{row['task']}/{row['metric']}/{row['name'].replace('_cue_minus_no_cue', '')}"] = tuple(round(float(row[k]), 6) for k in ('difference_pp', 'ci_low_pp', 'ci_high_pp'))
res['paired_mine'] = pair; res['paired_theirs'] = theirs
res['paired_point_all_equal'] = all(abs(pair[k][0] - theirs[k][0]) < 1e-6 for k in theirs) and set(pair) == set(theirs)
res['paired_ci_all_equal'] = all(abs(pair[k][1] - theirs[k][1]) < 1e-6 and abs(pair[k][2] - theirs[k][2]) < 1e-6 for k in theirs)
res['numpy_local'] = np.__version__
json.dump(res, open(OUT, 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: (v if not isinstance(v, dict) or k.startswith('paired') else {kk: vv for kk, vv in v.items() if kk not in ('examples', 'rsd_unique')}) for k, v in res.items()}, indent=1, ensure_ascii=False)[:12000])
