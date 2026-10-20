"""P010 Z1: secondary parser + stratified blind sample (Claude, 2026-10-19).

Uniform rules applied identically to base and student outputs. Strict (frozen)
verdicts are copied, never overwritten. Secondary never searches the text for the
gold value: it extracts ONE final-answer candidate by a fixed priority, then compares.
Logical length caps stay incorrect under both rules (diagnostic count reported).
Usage: python3 -I z1_secondary.py DATA_DIR OUT_DIR
"""
import json, re, random, sys, hashlib, collections
from fractions import Fraction

DATA, OUT = sys.argv[1], sys.argv[2]
EXPECTED_SHA256 = {
 'inputs/gsm8k_test1319.jsonl': 'e8e85dd16771c7f3121b061afdb7d9d90ceadb2580137d108b66abf51cb248b3',
 'inputs/math500.jsonl': '132582ca829ff11820b9d739a14c6e3ce383aacb51dba50e406acd2d27d1b95d',
 'p0/LOCAL_ORACLE_AUDIT.json': 'b36d5c3730ec616f8220ebf04be35a3a75a52961028e4ad6d1ba9aca92e001ab',
 'p1/original/ROWS.json': '02fac50dcd0bad0580b425ee13b11cc7ef1a641244bc628fe3a2aadc998db974',
 'p1/original/ALL_SCORED_ROWS.json': '6f3b718f969268d30d44ed4b9d31c466a2a4e91988e809a96943e7d6b09dfd51',
 's1n400_oracle/DECODED_ROWS.json': '677690315ec72ff7c00170d1a1c8333404f6101cd05dc71ef86bcf6351f779b7',
 's1n400_score/job/payload/ALL_SCORED_ROWS.json': 'e285fafadd255a5363f97e5d6611796549b70a96abdee5578a03d05c5dd16d3e'}
for _f, _h in EXPECTED_SHA256.items():
    assert hashlib.sha256(open(f'{DATA}/{_f}', 'rb').read()).hexdigest() == _h, _f
SEED = 20261019

# ---------------- shared helpers ----------------
def last_boxed(s):
    i = max(s.rfind('\\boxed'), s.rfind('\\fbox'))
    if i < 0:
        return None
    j = s.find('{', i)
    if j < 0:
        return None
    d, k = 0, j
    while k < len(s):
        esc = k > 0 and s[k-1] == '\\'
        if s[k] == '{' and not esc: d += 1
        elif s[k] == '}' and not esc:
            d -= 1
            if d == 0:
                return s[j + 1:k]
        k += 1
    return None

MARKERS = [r'####\s*', r'[Tt]he final answer is[:\s]*', r'[Ff]inal [Aa]nswer[:\s]*',
           r'[Tt]he answer is[:\s]*', r'\b[Aa]nswer\s*:\s*']

def last_marker_text(s):
    """Text after the LAST occurrence of any explicit answer marker, to end of line."""
    best = None
    for m in MARKERS:
        for mt in re.finditer(m, s):
            if best is None or mt.end() > best:
                best = mt.end()
    if best is None:
        return None
    line = s[best:].split('\n', 1)[0].strip()
    return line or None

NUM = re.compile(r'-?\d[\d,]*\.?\d*|-?\.\d+')

def to_num(t):
    if t is None:
        return None
    t = t.replace('\\$', '').replace('$', '').replace('\\!', '').replace('\\,', '')
    t = re.sub(r'\\(text|mathrm|textbf)\{[^}]*\}', '', t)
    t = t.replace('dfrac', 'frac').replace('tfrac', 'frac')
    m = re.fullmatch(r'\s*(-?)\\frac\{(-?\d+)\}\{(-?\d+)\}\s*\.?\s*', t)
    if m:
        try:
            v = Fraction(int(m.group(2)), int(m.group(3)))
            return -v if m.group(1) else v
        except ZeroDivisionError:
            return None
    m = re.fullmatch(r'\s*(-?\d+)\s*/\s*(\d+)\s*\.?\s*', t)
    if m:
        try:
            return Fraction(int(m.group(1)), int(m.group(2)))
        except ZeroDivisionError:
            return None
    t2 = re.sub(r'(?i)\b(dollars?|cents?|units?|inches|feet|cups?|minutes?|hours?|days?|years?|students?|miles?|degrees?)\b', '', t)
    t2 = t2.replace('%', '').strip().rstrip('.').strip()
    m = re.fullmatch(r'-?\d[\d,]*\.?\d*|-?\.\d+', t2)
    if not m:
        return None
    try:
        return Fraction(m.group(0).replace(',', '').rstrip('.'))
    except (ValueError, ZeroDivisionError):
        return None

def norm(t):
    if t is None:
        return None
    t = t.strip().rstrip('.').strip()
    t = t.replace('\\left', '').replace('\\right', '').replace('\\!', '').replace('\\,', '')
    t = t.replace('dfrac', 'frac').replace('tfrac', 'frac').replace('$', '')
    t = re.sub(r'\\text\{\s*([^}]*)\}', r'\1', t)
    t = re.sub(r'\s+', '', t)
    t = t.replace('^{\\circ}', '').replace('^\\circ', '')
    return t

def equal(pred, gold):
    if pred is None:
        return False
    a, b = to_num(pred), to_num(gold)
    if a is not None and b is not None:
        return a == b
    return norm(pred) == norm(gold)

LEAK = re.compile(r'^\s*(You are an AI assistant|What was the question\?|What is the step-by-step reasoning process|Source: https?://|Tulee:)', re.M)

def cut_leak(seg):
    """Uniform rule: drop template-leak tail (system-prompt echoes, meta notes) before extraction."""
    m = LEAK.search(seg)
    return seg[:m.start()] if m else seg

def rhs(t):
    if t is not None and '=' in t:
        return t.rsplit('=', 1)[1].strip()
    return t

# ---------------- GSM8K ----------------
def gsm_candidate(seg):
    seg = cut_leak(seg)
    b = last_boxed(seg)
    if b is not None:
        return b, 'box'
    m = last_marker_text(seg)
    if m is not None and re.search(r'(?i)\bnot\b|\bnor\b|\bincorrect\b', m):
        return None, 'marker_negated'
    if m is not None and NUM.search(m):
        v = gsm_value(m)
        return (v, 'marker') if v is not None else (None, 'marker_ambiguous')
    lines = [l for l in seg.strip().split('\n') if l.strip()]
    if lines and NUM.search(lines[-1]):
        v = gsm_value(lines[-1])
        return (v, 'last_line') if v is not None else (None, 'last_line_ambiguous')
    return None, 'none'

def gsm_value(t):
    """v2 policy (C7-4): whole expression first (fractions/units via to_num); then RHS of the
    last '='; otherwise accept only if exactly ONE number remains. Several numbers => ambiguous."""
    t = t.strip().rstrip('.').strip()
    for cand in (t, rhs(t)):
        v = to_num(cand)
        if v is not None:
            return cand
    nums = NUM.findall(rhs(t))
    return nums[0] if len(nums) == 1 else None

def load_gsm():
    gold = {}
    for line in open(f'{DATA}/inputs/gsm8k_test1319.jsonl'):
        r = json.loads(line)
        gold[r['problem_id']] = (r['answer'], r['prompt'])
    sc = json.load(open(f'{DATA}/p0/LOCAL_ORACLE_AUDIT.json'))['scored']
    for key in ('base_638', 'correct_969'):
        ids = [r['problem_id'] for r in sc[key]]
        assert len(ids) == 1319 and len(set(ids)) == 1319 and set(ids) == set(gold), key
    out = {}
    for model, key in (('base', 'base_638'), ('student', 'correct_969')):
        for r in sc[key]:
            pid = r['problem_id']; st = r['stop']
            seg = st['answer_segment']; capped = st['stop_reason'] == 'length_cap'
            cand, rule = gsm_candidate(seg)
            sec = (not capped) and equal(cand, gold[pid][0])
            out.setdefault(pid, {'task': 'gsm8k', 'pid': pid, 'question': gold[pid][1], 'gold': gold[pid][0]})[model] = dict(
                strict=bool(r['score']['task_answer_correct']), secondary=bool(sec), cand=cand, rule=rule,
                stop=st['stop_reason'], capped=capped, capped_marker_correct=capped and equal(cand, gold[pid][0]),
                text=seg)
    return out

# ---------------- MATH-500 ----------------
def math_candidate(seg):
    seg = cut_leak(seg)
    b = last_boxed(seg)
    if b is not None:
        return b, 'box'
    m = last_marker_text(seg)
    if m is not None:
        mm = re.findall(r'\$([^$]+)\$', m)
        return (mm[-1] if mm else m), 'marker'
    lines = [l for l in seg.strip().split('\n') if l.strip()]
    if lines:
        mm = re.findall(r'\$([^$]+)\$', lines[-1])
        if mm:
            return rhs(mm[-1]), 'last_line_last_math'
    return None, 'none'

def load_math():
    q = {}
    for i, line in enumerate(open(f'{DATA}/inputs/math500.jsonl')):
        r = json.loads(line)
        q[f'math500/{i}'] = r['problem']
    p1 = json.load(open(f'{DATA}/p1/original/ROWS.json'))
    p1s_list = json.load(open(f'{DATA}/p1/original/ALL_SCORED_ROWS.json'))
    base_list = [r for r in p1 if r['dataset'] == 'qwen_math_zero']
    stud_list = json.load(open(f'{DATA}/s1n400_oracle/DECODED_ROWS.json'))
    ssc_list = json.load(open(f'{DATA}/s1n400_score/job/payload/ALL_SCORED_ROWS.json'))
    for L, k in ((base_list, 'problem_id'), (stud_list, 'problem_id'), (ssc_list, 'id')):
        ks = [r[k] for r in L]; assert len(ks) == 500 and len(set(ks)) == 500, 'duplicate or missing MATH rows'
    assert len({r['id'] for r in p1s_list}) == len(p1s_list), 'duplicate P1 score ids'
    p1s = {r['id']: r['score'] for r in p1s_list}
    base = {r['problem_id']: r for r in base_list}
    gold = {pid: r['gold'] for pid, r in base.items()}
    stud = {r['problem_id']: r for r in stud_list}
    ssc = {r['id'].split('::', 1)[1]: r['score'] for r in ssc_list}
    assert len(base) == 500 and set(base) == set(stud) == set(ssc), 'MATH id sets differ'
    out = {}
    for pid in base:
        out[pid] = {'task': 'math', 'pid': pid, 'question': q.get(pid), 'gold': gold[pid]}
        for model, seg, stop, sc in (
            ('base', base[pid]['answer_segment'], base[pid]['stop_reason'], p1s['qwen_math_zero::' + pid]),
            ('student', stud[pid]['stop']['answer_segment'], stud[pid]['stop']['stop_reason'], ssc[pid])):
            capped = sc.get('status') == 'length_cap'
            cand, rule = math_candidate(seg)
            if rule == 'box' and sc.get('box_extracted') and cand == sc.get('extracted_answer'):
                sec = bool(sc['correct'])   # identical extraction: frozen math-verify verdict retained
            elif rule == 'box':
                rule = 'box_differs_from_frozen'
                sec = (not capped) and equal(cand, gold[pid])   # v3: no reuse of a non-identical verdict
            else:
                sec = (not capped) and equal(cand, gold[pid])
            out[pid][model] = dict(strict=bool(sc['correct']), secondary=bool(sec), cand=cand, rule=rule,
                                   stop=stop, status=sc.get('status'), capped=capped,
                                   capped_marker_correct=capped and rule != 'box' and equal(cand, gold[pid]),
                                   text=seg)
    return out

def summarize(rows, name):
    n = len(rows)
    s = {}
    for rule in ('strict', 'secondary'):
        b = sum(r['base'][rule] for r in rows.values()); t = sum(r['student'][rule] for r in rows.values())
        s[rule] = dict(base=b, student=t, gap=t - b)
    s['gap_change_count'] = s['strict']['gap'] - s['secondary']['gap']
    s['n'] = n
    s['strata_strict'] = dict(collections.Counter(
        ('B1' if r['base']['strict'] else 'B0') + ('S1' if r['student']['strict'] else 'S0') for r in rows.values()))
    for m in ('base', 'student'):
        s[f'{m}_rules'] = dict(collections.Counter(r[m]['rule'] for r in rows.values()))
        s[f'{m}_capped'] = sum(r[m]['capped'] for r in rows.values())
        s[f'{m}_capped_marker_correct'] = sum(r[m]['capped_marker_correct'] for r in rows.values())
        s[f'{m}_flip_wrong_to_right'] = sum((not r[m]['strict']) and r[m]['secondary'] for r in rows.values())
        s[f'{m}_flip_right_to_wrong'] = sum(r[m]['strict'] and (not r[m]['secondary']) for r in rows.values())
    return s

def sample(rows, task, rng):
    strata = {'A_base0_stud1': [], 'B_base1_stud0': [], 'C_both0': []}
    for pid in sorted(rows):
        r = rows[pid]; b, t = r['base']['strict'], r['student']['strict']
        if not b and t: strata['A_base0_stud1'].append(pid)
        elif b and not t: strata['B_base1_stud0'].append(pid)
        elif not b and not t: strata['C_both0'].append(pid)
    want = {'A_base0_stud1': 24, 'B_base1_stud0': 8, 'C_both0': 8}
    picked = []
    for k, v in strata.items():
        for pid in rng.sample(v, min(want[k], len(v))):
            picked.append((k, pid))
    return picked, {k: len(v) for k, v in strata.items()}

def main():
    import os
    os.makedirs(OUT, exist_ok=False)   # v2: never overwrite an existing output directory
    rng = random.Random(SEED)
    summary, items = {}, []
    for name, rows in (('gsm8k', load_gsm()), ('math', load_math())):
        summary[name] = summarize(rows, name)
        picked, sizes = sample(rows, name, rng)
        summary[name]['stratum_population'] = sizes
        for k, pid in picked:
            r = rows[pid]
            # outputs to label: the output(s) the strict rule marks wrong
            targets = {'A_base0_stud1': ['base'], 'B_base1_stud0': ['student'], 'C_both0': ['base', 'student']}[k]
            for m in targets:
                items.append(dict(task=name, stratum=k, pid=pid, model=m, question=r['question'], gold=r['gold'],
                                  strict=r[m]['strict'], secondary=r[m]['secondary'], cand=r[m]['cand'],
                                  rule=r[m]['rule'], stop=r[m]['stop'], text=r[m]['text']))
    rng2 = random.Random(SEED + 1)
    rng2.shuffle(items)
    for i, it in enumerate(items):
        it['item'] = f'Z{i:03d}'
    json.dump(summary, open(f'{OUT}/Z1_SUMMARY.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(items, open(f'{OUT}/Z1_ITEMS.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    print('items', len(items))

if __name__ == '__main__':
    main()
