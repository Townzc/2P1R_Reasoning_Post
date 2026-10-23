"""Independent A3 for the two-cell forced-answer probe on the ~3B extension.

Streams archives from git (no extraction to disk) and checks:
  - new continuation decode / native stop / first balanced forced box (own BPE decoder)
  - published DECODED rows agree with own decode
  - new P1 labels vs gold (string-normalised agreement; disagreements listed for review)
  - joined forced labels = saved natural Booleans + new labels
  - per-cell counts / accuracies, loop breakdown
  - paired-question bootstrap for SMALL-LARGE (forced) and A6-A7 (forced)
"""
import json, sys, tarfile, subprocess, collections
import numpy as np

REPO, REV, TOK, OUT = sys.argv[1:5]
D = 'reports/p011_20261020/'
CELLS = ('long_R3024xE3_S-F15_s17', 'long_R9072x1_S-F15_s17')
EOS = (151645, 151643)

T = json.load(open(TOK)); id2tok = {v: k for k, v in T['model']['vocab'].items()}
for a in T['added_tokens']: id2tok[a['id']] = a['content']
special = {a['id'] for a in T['added_tokens'] if a.get('special')}
bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256)); cs = bs[:]; k = 0
for b in range(256):
    if b not in bs: bs.append(b); cs.append(256 + k); k += 1
dec = {chr(c): b for b, c in zip(bs, cs)}


def decode(ids):
    out = bytearray(); parts = []
    for i in ids:
        t = id2tok[i]
        if i in special:
            parts.append(out.decode('utf-8', 'replace')); out = bytearray(); parts.append(t)
        else:
            out.extend(dec[ch] for ch in t)
    parts.append(out.decode('utf-8', 'replace')); return ''.join(parts)


def escaped(t, i):
    n = 0; j = i - 1
    while j >= 0 and t[j] == '\\': n += 1; j -= 1
    return n % 2 == 1


def forced_box(t):
    d = 1
    for i, c in enumerate(t):
        if not escaped(t, i): d += (c == '{') - (c == '}')
        if d == 0: return t[:i], True
    return t, False


def stream(paths):
    cmd = 'cat ' + ' '.join(f'<(git -C {REPO} show {REV}:{p})' for p in paths)
    proc = subprocess.Popen(cmd, shell=True, executable='/bin/bash', stdout=subprocess.PIPE)
    return tarfile.open(fileobj=proc.stdout, mode='r|gz')


def norm(s):
    s = s.strip().replace(' ', '').replace('\\!', '').replace('\\,', '').replace('\\left', '').replace('\\right', '')
    s = s.replace('dfrac', 'frac').replace('tfrac', 'frac').replace('^{\\circ}', '').replace('^\\circ', '')
    s = s.replace('\\text{', '{').replace('\\mathrm{', '{').rstrip('.').replace('$', '')
    return s


# ---------- 1. new forced results
R = collections.defaultdict(dict); results = None
tf = stream([D + 'forced_answer_ext3b_actual_results_v1/NEW_RESULTS.tar.gz.part000'])
for m in tf:
    if not m.isfile(): continue
    nm = m.name; p = nm.split('/')
    if nm.startswith('collect/cells/') and '/raw/' in nm:
        cell = p[2]
        for r in json.load(tf.extractfile(m)):
            a = r['answers'][0]; ids = a['token_ids']
            stop = next(((i, 'native_eos' if t in EOS else 'invalid_special_token')
                         for i, t in enumerate(ids) if t in EOS or t in special), None)
            vis = ids[:stop[0]] if stop else ids
            native = stop[1] if stop else ('length_cap' if len(ids) == 64 else 'BAD')
            s, closed = forced_box(decode(vis))
            R[cell].setdefault('mine', {})[r['id']] = dict(native=native, closed=closed, seg=s, n=len(ids))
    elif nm.startswith('audit/') and nm.endswith('DECODED.json'):
        R[p[1]]['decoded'] = {r['id']: r for r in json.load(tf.extractfile(m))}
    elif nm.startswith('audit/') and nm.endswith('SCORING_ROWS.json'):
        R[p[1]]['rows'] = {r['id']: r for r in json.load(tf.extractfile(m))}
    elif nm.startswith('score/') and nm.endswith('ALL_SCORED_ROWS.json'):
        R[p[1]]['score'] = {r['id']: r['score']['correct'] for r in json.load(tf.extractfile(m))}
    elif nm.startswith('analysis/') and nm.endswith('_FORCED_LABELS.json'):
        R[p[1].replace('_FORCED_LABELS.json', '')]['joined'] = json.load(tf.extractfile(m))
    elif nm == 'analysis/RESULTS.json':
        results = json.load(tf.extractfile(m))

# ---------- 2. saved natural Booleans for the two extension cells
natural = {}
parts = [D + f'ext3b_complete_actual_results_v1/original_scientific_bytes.tar.gz.part00{i}' for i in range(4)]
tf = stream(parts)
for m in tf:
    if m.isfile() and m.name.endswith('ALL_SCORED_ROWS.json'):
        cell = next((c for c in CELLS if c in m.name), None)
        if cell:
            natural[cell] = {r['id']: r['score']['correct'] for r in json.load(tf.extractfile(m))
                             if r['id'].startswith('math500:')}

# ---------- 3. A6 / A7 joined forced labels from the seven-cell relaunch
seven = {}
tf = stream([D + f'forced_answer_relaunch_actual_results_v1/NEW_RESULTS.tar.gz.part00{i}' for i in range(2)])
for m in tf:
    if m.isfile() and m.name.startswith('analysis/') and m.name.endswith('_FORCED_LABELS.json'):
        c = m.name.split('/')[-1].replace('_FORCED_LABELS.json', '')
        if c in ('A6', 'A7'): seven[c] = json.load(tf.extractfile(m))

# ---------- checks
report = {}
for cell in CELLS:
    v = R[cell]; mine, decd, rows, score, joined = v['mine'], v['decoded'], v['rows'], v['score'], v['joined']
    nat = natural[cell]
    selected = set(mine)
    out = {'continuations': len(mine), 'not_64_or_eos': sum(1 for x in mine.values() if x['native'] == 'BAD')}
    # decode agreement
    out['closed_mismatch'] = [i for i in mine if mine[i]['closed'] != (decd[i]['forced_box_completion_category'] != 'forced_box_unclosed')]
    out['unclosed'] = sum(1 for x in mine.values() if not x['closed'])
    # answer agreement with gold for new labels
    agree_true = agree_false = 0; check = []
    for i in selected:
        gold = rows[i]['gold']; ans = mine[i]['seg'] if mine[i]['closed'] else None
        eq = ans is not None and norm(ans) == norm(str(gold))
        lab = score[i]
        if lab and eq: agree_true += 1
        elif not lab and not eq: agree_false += 1
        else: check.append((i, lab, ans, gold))
    out.update(label_true=sum(score[i] for i in selected), string_eq_and_true=agree_true,
               string_neq_and_false=agree_false, disagreements=len(check))
    report.setdefault('disagreements', {})[cell] = check
    # joined = natural (non-selected) + new (selected)
    out['joined_ids_ok'] = set(joined) == set(nat)
    out['natural_preserved'] = all(joined[i] == nat[i] for i in nat if i not in selected)
    out['selected_natural_all_false'] = not any(nat[i] for i in selected)
    out['new_labels_used'] = all(joined[i] == score[i] for i in selected)
    for mode in ('sample', 'greedy'):
        ids = [i for i in nat if i.split(':')[2] == mode]
        out[mode] = dict(n=len(ids), capped=sum(i in selected for i in ids),
                         natural_acc=round(100 * sum(nat[i] for i in ids) / len(ids), 2),
                         forced_acc=round(100 * sum(joined[i] for i in ids) / len(ids), 2))
    report[cell] = out


def vec(lab, mode):
    return np.array([np.mean([lab[f'math500:{q:04d}:sample:{s}'] for s in range(4)]) if mode == 'sample'
                     else float(lab[f'math500:{q:04d}:greedy:0']) for q in range(500)])


def interval(left, right, seed=20261021, draws=10000):
    x = right - left; rng = np.random.default_rng(seed); means = []
    for _ in range(draws // 1000):
        means.append(x[rng.integers(0, 500, size=(1000, 500))].mean(1))
    m = np.concatenate(means)
    return round(100 * x.mean(), 2), [round(100 * float(np.quantile(m, q)), 2) for q in (0.025, 0.975)]


S, L = R[CELLS[0]]['joined'], R[CELLS[1]]['joined']
report['contrasts'] = {
    'SMALL_minus_LARGE_forced': {m: interval(vec(L, m), vec(S, m)) for m in ('sample', 'greedy')},
    'SMALL_minus_LARGE_natural': {m: interval(vec(natural[CELLS[1]], m), vec(natural[CELLS[0]], m)) for m in ('sample', 'greedy')},
    'A6_minus_A7_forced': {m: interval(vec(seven['A7'], m), vec(seven['A6'], m)) for m in ('sample', 'greedy')},
}
report['published'] = results.get('contrasts') if results else None
json.dump(report, open(OUT, 'w'), indent=1, default=str)
print(json.dumps({k: v for k, v in report.items() if k not in ('disagreements', 'published')}, indent=1, default=str))
for c, lst in report['disagreements'].items():
    print(c, 'disagreements', len(lst))
    for row in lst[:40]: print('  ', row)
