"""Independent A3 for P010 T1.5 K4/K8 (MATH) and E4 (GSM8K). Claude.
Usage: python3 -I a3_check.py REPO Z1DATA OUT"""
import json, sys, re, random, collections, hashlib
REPO, Z, OUT = sys.argv[1:4]
P = f'{REPO}/reports/p010_20261019'
rng = random.Random(20261020)

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
    return None
nrm = lambda t: re.sub(r'\s+', '', (t or '').replace('\\left', '').replace('\\right', '').replace('dfrac', 'frac').replace('\\!', '').replace('$', '')).rstrip('.')

def boot(a, b, n=10000):
    """paired bootstrap over questions; a,b dict pid->0/1; returns diff (b-a) count, pp, 95% CI pp"""
    ids = sorted(a); assert set(ids) == set(b)
    d = [b[i] - a[i] for i in ids]; N = len(d); obs = sum(d)
    bs = sorted(sum(d[rng.randrange(N)] for _ in range(N)) for _ in range(n))
    return dict(diff=obs, pp=round(100*obs/N, 2), ci95_pp=(round(100*bs[int(.025*n)]/N, 2), round(100*bs[int(.975*n)]/N, 2)),
                discordant=sum(x != 0 for x in d), n=N)

res = {}
# ---- MATH gold ----
p1 = json.load(open(f'{Z}/p1/original/ROWS.json'))
gold = {r['problem_id']: r['gold'] for r in p1 if r['dataset'] == 'qwen_math_zero'}
assert len(gold) == 500
# reference K1 (S1 n400) per-row
k1 = {r['id'].split('::', 1)[1]: int(bool(r['score']['correct'])) for r in json.load(open(f'{Z}/s1n400_score/job/payload/ALL_SCORED_ROWS.json'))}
greedy = {'K1': k1}
for cell in ('t15_s17_n400_k4', 't15_s17_n400_k8'):
    q = f'{P}/student_results_v1/{cell}/'
    dec = json.load(open(q + 'DECODED_ROWS.json')); sc = json.load(open(q + 'ALL_SCORED_ROWS.json'))
    decm = {}
    for r in dec:
        key = (r['evaluation'], r['problem_id']); assert key not in decm; decm[key] = r
    scm = {}
    for s in sc:
        ev, pid = s['id'].split('::', 1); assert (ev, pid) not in scm; scm[(ev, pid)] = s['score']
    assert set(decm) == set(scm) and len(scm) == 2500
    c = dict(box_mismatch=0, judged_wrong_but_string_equal=0, judged_right_string_differs=0, capped_marked_correct=0)
    per_ev = collections.Counter(); per = collections.defaultdict(dict); diffs = []
    for (ev, pid), s in scm.items():
        st = decm[(ev, pid)]['stop']; seg = st['answer_segment']; b = last_boxed(seg)
        if s.get('box_extracted') and b != s.get('extracted_answer'): c['box_mismatch'] += 1
        if s.get('correct') and st['stop_reason'] == 'length_cap': c['capped_marked_correct'] += 1
        if not s.get('correct') and b is not None and st['stop_reason'] == 'native_eos' and nrm(b) == nrm(gold[pid]): c['judged_wrong_but_string_equal'] += 1
        if s.get('correct') and b is not None and nrm(b) != nrm(gold[pid]): c['judged_right_string_differs'] += 1; diffs.append((b, gold[pid]))
        per_ev[ev] += int(bool(s.get('correct'))); per[ev][pid] = int(bool(s.get('correct')))
    c['correct_by_endpoint'] = dict(per_ev)
    c['sampled_mean_pass1'] = round(sum(per_ev[f'sample{i}'] for i in range(4)) / 2000, 4)
    c['greedy_caps'] = sum(decm[('greedy', p)]['stop']['stop_reason'] == 'length_cap' for p in gold)
    rng2 = random.Random(1); rng2.shuffle(diffs); c['equiv_spotcheck_30'] = diffs[:30]
    res[cell] = c; greedy[cell.split('_')[-1].upper()] = per['greedy']
    res[cell]['sampled_per_question_mean'] = {p: sum(per[f'sample{i}'][p] for i in range(4)) / 4 for p in gold}
res['contrasts_greedy'] = {
    'K4_minus_K1': boot(greedy['K1'], greedy['K4']), 'K8_minus_K1': boot(greedy['K1'], greedy['K8']),
    'K8_minus_K4': boot(greedy['K4'], greedy['K8'])}
# sampled: K8 vs K4 per-question means
a = res['t15_s17_n400_k4']['sampled_per_question_mean']; b = res['t15_s17_n400_k8']['sampled_per_question_mean']
ids = sorted(a); d = [b[i] - a[i] for i in ids]; bs = sorted(sum(d[rng.randrange(500)] for _ in range(500)) for _ in range(10000))
res['contrasts_sampled'] = {'K8_minus_K4_pp': round(100*sum(d)/500, 2), 'ci95_pp': (round(100*bs[250]/500, 2), round(100*bs[9750]/500, 2))}
for cell in ('t15_s17_n400_k4', 't15_s17_n400_k8'): del res[cell]['sampled_per_question_mean']

# ---- E4 GSM8K ----
gsm = {}
for line in open(f'{Z}/inputs/gsm8k_test1319.jsonl'):
    r = json.loads(line); gsm[r['problem_id']] = r['answer']
NUM = re.compile(r'-?\d[\d,]*\.?\d*')
def gsm_last_marked(seg):
    b = last_boxed(seg)
    if b is not None: return b
    m = None
    for pat in (r'####\s*', r'(?i)the answer is[:\s]*', r'(?i)\banswer\s*:\s*'):
        for mt in re.finditer(pat, seg): m = mt.end() if m is None or mt.end() > m else m
    if m is None: return None
    ns = NUM.findall(seg[m:].split('\n', 1)[0]); return ns[0] if ns else None
def numeq(a, b):
    try: return a is not None and abs(float(a.replace(',', '').rstrip('.')) - float(b.replace(',', ''))) < 1e-9
    except ValueError: return False
e4 = {}
for run in ('e4_s17_n400', 'e4_s17_n3200'):
    rows = json.load(open(f'{P}/e4_endpoint_results_v1/{run}/DECODED_ROWS.json'))
    ids = [r['problem_id'] for r in rows]; assert len(ids) == 1319 and set(ids) == set(gsm)
    verdict = {}; agree = 0; disagree = []; caps = 0
    for r in rows:
        v = bool(r['score']['task_answer_correct']) if 'task_answer_correct' in r['score'] else bool(r['score'].get('correct'))
        verdict[r['problem_id']] = int(v)
        st = r['stop']; caps += st['stop_reason'] == 'length_cap'
        mine = (st['stop_reason'] != 'length_cap') and numeq(gsm_last_marked(st['answer_segment']), gsm[r['problem_id']])
        if mine == v: agree += 1
        else: disagree.append((r['problem_id'], v, mine, st['answer_segment'][-200:]))
    oracle = json.load(open(f'{P}/e4_endpoint_results_v1/{run}/ENDPOINT_ORACLE.json'))
    e4[run] = dict(correct=sum(verdict.values()), oracle_correct=oracle.get('correct'), logical_caps=caps,
                   independent_parser_agreement=f'{agree}/1319', disagreements_sample=disagree[:8], n_disagree=len(disagree))
    e4[run + '_v'] = verdict
res['E4'] = {k: v for k, v in e4.items() if not k.endswith('_v')}
res['E4']['n3200_minus_n400'] = boot(e4['e4_s17_n400_v'], e4['e4_s17_n3200_v'])
json.dump(res, open(OUT, 'w'), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:6000])
