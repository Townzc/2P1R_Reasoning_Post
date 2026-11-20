"""Independent re-decode (pure-Python byte-level BPE) and re-parse of retained raw endpoint
token IDs. Runs where the private .local artifacts live; see rescore notes in the audit report.
Parser is deliberately different from analyses/gsm8k_answer_audit.py: last \\boxed{} -> '####' ->
'answer is' (anywhere in line), cut at '\\nProblem:'."""
import json, glob, os, re, collections
from fractions import Fraction
B = os.path.expanduser('~/mnt/294_288_project/research_tracks/icml_acl_2027/.local/midpoint_20261011')
tok = json.load(open(f'{B}/data_pipeline/reconstruction_r1/tokenizer/tokenizer.json'))
id2tok = {v: k for k, v in tok['model']['vocab'].items()}
special = set()
for a in tok['added_tokens']:
    id2tok[a['id']] = a['content']; special.add(a['id'])
def b2u():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]; n = 0
    for b in range(256):
        if b not in bs: bs.append(b); cs.append(256 + n); n += 1
    return {chr(c): b for b, c in zip(bs, cs)}
U = b2u()
def decode(ids):
    out = bytearray()
    for i in ids:
        if i in special: break
        out += bytes(U[ch] for ch in id2tok[i])
    return out.decode('utf-8', errors='replace')
gold = {f'gsm8k/train/{i:05d}': json.loads(l)['answer'].split('####')[-1].strip().replace(',', '')
        for i, l in enumerate(open(f'{B}/data_pipeline/reconstruction_r1/sources/gsm8k_train.jsonl'))}
def num(s):
    s = s.strip().replace(',', '').replace('$', '').rstrip('.')
    s = re.sub(r'\\(?:text|mathrm)\{[^}]*\}', '', s).strip()
    if re.fullmatch(r'-?\d+(?:\.\d+)?', s): return Fraction(s)
    m = re.fullmatch(r'\\[dt]?frac\{(-?\d+)\}\{(\d+)\}', s) or re.fullmatch(r'(-?\d+)/(\d+)', s)
    return Fraction(int(m.group(1)), int(m.group(2))) if m else None
def boxed(t):
    res, i = [], 0
    while (j := t.find('\\boxed{', i)) >= 0:
        k, d = j + 7, 1
        while k < len(t) and d:
            d += {'{': 1, '}': -1}.get(t[k], 0); k += 1
        res.append(t[j + 7:k - 1]); i = k
    return res
def parse(t):
    t = re.split(r'\n\s*Problem:', t)[0]
    if (bx := boxed(t)): return num(bx[-1]), 'boxed'
    if (m := re.findall(r'####\s*([^\n]+)', t)): return num(m[-1]), 'hash'
    if (m := re.findall(r'answer is[:\s]*\$?\\?\(?\s*([-\d.,/]+)', t)): return num(m[-1]), 'answeris'
    return None, 'none'
runs = {'base': 'grid_completion_export/base', 'breadth_17': 'grid_completion_export/breadth_17_resume',
        'mixed_17': 'grid_completion_export/mixed_17', 'mixed_23': 'grid_completion_export/mixed_23'}
for r in ['breadth_23', 'repeat_17', 'solutions_17', 'repeat_23', 'solutions_23']:
    runs[r] = 'grid_export_r2/' + r
res = {}
for r, p in runs.items():
    d = {}
    for f in sorted(glob.glob(f'{B}/{p}/endpoint431/*_raw.json')):
        x = json.load(open(f))
        for pid, ids in zip(x['problem_ids'], x['batch_output_ids']):
            v, how = parse(decode(ids))
            d[pid] = {'mine': v is not None and v == num(gold[pid]), 'how': how}
    res[r] = d
json.dump(res, open(os.path.expanduser('~/aud/mine.json'), 'w'))
print({r: (len(d), sum(v['mine'] for v in d.values())) for r, d in res.items()})
