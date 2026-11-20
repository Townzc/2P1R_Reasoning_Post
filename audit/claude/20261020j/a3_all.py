"""Independent A3 for all P010 MATH student cells + independent paired bootstrap (Claude).
Usage: python3 -I a3_all.py REPO Z1DATA OUT"""
import json, sys, re, random, collections
REPO, Z, OUT = sys.argv[1:4]
P = f'{REPO}/reports/p010_20261019'
def last_boxed(s):
    i = max(s.rfind('\\boxed'), s.rfind('\\fbox'))
    if i < 0: return None
    j = s.find('{', i); d = 0
    if j < 0: return None
    for k in range(j, len(s)):
        esc = s[k-1] == '\\'
        if s[k] == '{' and not esc: d += 1
        elif s[k] == '}' and not esc:
            d -= 1
            if d == 0: return s[j+1:k]
nrm = lambda t: re.sub(r'\s+', '', (t or '').replace('\\left', '').replace('\\right', '').replace('dfrac', 'frac').replace('\\!', '').replace('$', '')).rstrip('.')
gold = {r['problem_id']: r['gold'] for r in json.load(open(f'{Z}/p1/original/ROWS.json')) if r['dataset'] == 'qwen_math_zero'}
PIDS = sorted(gold)
def load(dirp, endpoints):
    dec = {(r['evaluation'], r['problem_id']): r for r in json.load(open(dirp + 'DECODED_ROWS.json'))}
    sc = {}
    for s in json.load(open(dirp + 'ALL_SCORED_ROWS.json')):
        ev, pid = s['id'].split('::', 1); assert (ev, pid) not in sc; sc[(ev, pid)] = s['score']
    assert set(dec) == set(sc) == {(e, p) for e in endpoints for p in PIDS}, dirp
    chk = collections.Counter(); v = collections.defaultdict(dict)
    for (ev, pid), s in sc.items():
        st = dec[(ev, pid)]['stop']; b = last_boxed(st['answer_segment']); c = bool(s.get('correct'))
        if s.get('box_extracted') and b != s.get('extracted_answer'): chk['box_mismatch'] += 1
        if c and st['stop_reason'] == 'length_cap': chk['capped_marked_correct'] += 1
        if (not c) and b is not None and st['stop_reason'] == 'native_eos' and nrm(b) == nrm(gold[pid]): chk['wrong_but_string_equal'] += 1
        if c and b is not None and nrm(b) != nrm(gold[pid]): chk['right_string_differs'] += 1
        v[ev][pid] = int(c)
    return v, dict(chk)
cells = {}; checks = {}
S = [f'sample{i}' for i in range(4)]
for c in ('t15_s17_n400_k4', 't15_s17_n400_k8', 't7_s17_n400_k1', 't7_s17_n3200_k1', 't72_s17_n400_k1', 't72_s17_n3200_k1', 't72_s17_e1d_n3200_k1'):
    v, ch = load(f'{P}/student_results_v1/{c}/', ['greedy'] + S); cells[c] = v; checks[c] = ch
# S1 parents: greedy from P009 scored rows (n400 in Z1 data; n3200 from repo), samples from new packages
def p009_greedy(run):
    import tarfile, io
    t = tarfile.open(f'{REPO}/reports/p009_20261014/stage1_s1_results_v1/{run}/ORIGINAL_SCORING_EVIDENCE.tar.gz')
    rows = json.load(t.extractfile('job/payload/ALL_SCORED_ROWS.json'))
    return {r['id'].split('::', 1)[1]: int(bool(r['score']['correct'])) for r in rows}
for run, name in (('s1_s17_n400', 't15_s17_n400_k1'), ('s1_s17_n3200', 't15_s17_n3200_k1')):
    v, ch = load(f'{P}/existing_s1_samples_results_v1/{run}/', S); v['greedy'] = p009_greedy(run); cells[name] = v; checks[name] = ch
summary = {c: dict(greedy=sum(v['greedy'].values()), sampled=sum(sum(v[s].values()) for s in S)) for c, v in cells.items()}
rng = random.Random(20261020)
idx = [[rng.randrange(500) for _ in range(500)] for _ in range(10000)]
def contrast(a, b, metric):
    if metric == 'greedy': x = [cells[a]['greedy'][p] for p in PIDS]; y = [cells[b]['greedy'][p] for p in PIDS]
    else: x = [sum(cells[a][s][p] for s in S)/4 for p in PIDS]; y = [sum(cells[b][s][p] for s in S)/4 for p in PIDS]
    d = [yy - xx for xx, yy in zip(x, y)]; obs = 100*sum(d)/500
    bs = sorted(100*sum(d[i] for i in ii)/500 for ii in idx)
    return dict(diff_pp=round(obs, 2), ci95=(round(bs[250], 2), round(bs[9749], 2)))
pairs = dict(delta_P_T15=('t15_s17_n400_k1', 't15_s17_n3200_k1'), delta_P_T7=('t7_s17_n400_k1', 't7_s17_n3200_k1'),
    delta_P_T72=('t72_s17_n400_k1', 't72_s17_n3200_k1'), delta_K_T15_K4=('t15_s17_n400_k1', 't15_s17_n400_k4'),
    delta_K_T15_K8=('t15_s17_n400_k1', 't15_s17_n400_k8'), delta_T_T72_n400=('t15_s17_n400_k1', 't72_s17_n400_k1'),
    delta_T_T72_n3200=('t15_s17_n3200_k1', 't72_s17_n3200_k1'), delta_T_T7_n400=('t15_s17_n400_k1', 't7_s17_n400_k1'),
    delta_T_T7_n3200=('t15_s17_n3200_k1', 't7_s17_n3200_k1'), delta_diag_T15=('t15_s17_n3200_k1', 't15_s17_n400_k8'),
    delta_diff_E1d=('t72_s17_n3200_k1', 't72_s17_e1d_n3200_k1'))
res = dict(checks=checks, summary=summary, contrasts={k: dict(greedy=contrast(a, b, 'greedy'), sampled=contrast(a, b, 'sampled')) for k, (a, b) in pairs.items()})
# T72-vs-T15 agreement by question: share of questions where T72 student loses
json.dump(res, open(OUT, 'w'), indent=1)
print(json.dumps(res, indent=1))
