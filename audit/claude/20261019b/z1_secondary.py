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
SEED = 20261019

# ---------------- shared helpers ----------------
def last_boxed(s):
    i = s.rfind('\\boxed')
    if i < 0:
        i = s.rfind('\\fbox')
        if i < 0:
            return None
    j = s.find('{', i)
    if j < 0:
        return None
    d, k = 0, j
    while k < len(s):
        if s[k] == '{': d += 1
        elif s[k] == '}':
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

LEAK = re.compile(r'^\s*(You are an AI assistant|What was the question|What is the (problem|step-by-step)|Note:|Source:|Comment:|Explain how|Solve this problem|Tulee:)', re.M)

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
    if m is not None and NUM.search(m):
        return NUM.findall(m)[0], 'marker'
    lines = [l for l in seg.strip().split('\n') if l.strip()]
    if lines:
        ns = NUM.findall(lines[-1])
        if ns:
            return ns[-1], 'last_line_last_number'
    return None, 'none'

def load_gsm():
    gold = {}
    for line in open(f'{DATA}/inputs/gsm8k_test1319.jsonl'):
        r = json.loads(line)
        gold[r['problem_id']] = (r['answer'], r['prompt'])
    sc = json.load(open(f'{DATA}/p0/LOCAL_ORACLE_AUDIT.json'))['scored']
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
    p1s = {r['id']: r['score'] for r in json.load(open(f'{DATA}/p1/original/ALL_SCORED_ROWS.json'))}
    base = {r['problem_id']: r for r in p1 if r['dataset'] == 'qwen_math_zero'}
    gold = {pid: r['gold'] for pid, r in base.items()}
    stud = {r['problem_id']: r for r in json.load(open(f'{DATA}/s1n400_oracle/DECODED_ROWS.json'))}
    ssc = {r['id'].split('::', 1)[1]: r['score'] for r in json.load(open(f'{DATA}/s1n400_score/job/payload/ALL_SCORED_ROWS.json'))}
    out = {}
    for pid in base:
        out[pid] = {'task': 'math', 'pid': pid, 'question': q.get(pid), 'gold': gold[pid]}
        for model, seg, stop, sc in (
            ('base', base[pid]['answer_segment'], base[pid]['stop_reason'], p1s['qwen_math_zero::' + pid]),
            ('student', stud[pid]['stop']['answer_segment'], stud[pid]['stop']['stop_reason'], ssc[pid])):
            capped = sc.get('status') == 'length_cap'
            cand, rule = math_candidate(seg)
            if rule == 'box':
                sec = bool(sc['correct'])   # same extraction as strict; math-verify verdict retained
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
    os.makedirs(OUT, exist_ok=True)
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
