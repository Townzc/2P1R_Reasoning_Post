"""Claude independent re-decode + re-score of retained teacher outputs (P007A pilot and P007B cells).
Runs on the owner's machine. Requires ~/aud/rescore.py = audit/claude/20261012/rescore_raw_device.py
(only its tokenizer tables and decode() are used)."""
import json, glob, os, re, unicodedata, collections
from fractions import Fraction
exec(open(os.path.expanduser('~/aud/rescore.py')).read().split("gold={}")[0])  # decode() and tokenizer tables only
W = os.path.expanduser('~/mnt/294_288_project/research_tracks/icml_acl_2027')
B = W + '/.local/midpoint_20261011'
gold = {f'gsm8k/train/{i:05d}': json.loads(l)['answer'].split('####')[-1].strip().replace(',', '')
        for i, l in enumerate(open(f'{B}/data_pipeline/reconstruction_r1/sources/gsm8k_train.jsonl'))}
EOS = {151645, 151643}
def num(s):
    s = s.strip().replace(',', '').replace('$', '').rstrip('.').strip()
    s = re.sub(r'\\(?:text|mathrm|textbf)\{[^}]*\}', '', s).replace('\\!', '').replace('\\,', '').strip()
    s = s.replace('\\%', '').replace('%', '').strip()
    if re.fullmatch(r'[-+]?\d+(?:\.\d+)?', s): return Fraction(s)
    m = re.fullmatch(r'[-+]?\\[dt]?frac\{(-?\d+)\}\{(\d+)\}', s) or re.fullmatch(r'(-?\d+)/(\d+)', s)
    return Fraction(int(m.group(1)), int(m.group(2))) if m else None
def boxed(t):
    res, i = [], 0
    while (j := t.find('\\boxed{', i)) >= 0:
        k, d = j + 7, 1
        while k < len(t) and d:
            d += {'{': 1, '}': -1}.get(t[k], 0); k += 1
        res.append(t[j + 7:k - 1]); i = k
    return res
BOUND = re.compile(r'(?im)^[ \t]*(?:problem|question)[ \t]*:')
def judge(text, eos, trunc, g):
    if BOUND.search(text): return False, 'boundary'
    claims = [num(x) for x in boxed(text)] + [num(x) for x in re.findall(r'####\s*([^\n]+)', text)]
    if not claims or None in claims or len(set(claims)) != 1: return False, 'noclaim'
    return (claims[0] == num(g)) and eos and not trunc, 'ok'
def norm(t): return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', t)).strip()
def run(folders):
    out = {}; usable_seen = collections.defaultdict(set)
    for folder in folders:
        for f in sorted(glob.glob(folder + '/raw/*.json')):
            x = json.load(open(f)); w = x['prompt_width']
            for it, ids in zip(x['items'], x['batch_output_ids']):
                gen = ids[w:]
                pos = next((i for i, t in enumerate(gen) if t in EOS), None)
                eos = pos is not None; body = gen[:pos] if eos else gen
                trunc = (not eos) and len(gen) >= 1024
                text = decode(body)
                ok, why = judge(text, eos, trunc, gold[it['problem_id']])
                key = norm(text); pid = it['problem_id']
                usable = ok and key not in usable_seen[pid]
                if usable: usable_seen[pid].add(key)
                out[it['candidate_id']] = dict(usable=usable, why=why, eos=eos, trunc=trunc, tokens=len(body) + (1 if eos else 0))
    return out
res = {'pilot': run([B + '/teacher_pilot_r1/export_r1'])}
E = B + '/teacher_policy_r1/exports'
for c in ('breadth_p0', 'depth_p0', 'depth_p4'): res[c] = run([E + '/' + c])
res['breadth_p4'] = run([E + '/breadth_p4_recovered/parent', E + '/breadth_p4_recovered'])
pk = {}
for l in open(W + '/reports/p007_audit/policy_all_v1/attempts.jsonl'):
    a = json.loads(l); pk[(a['cell'], a['candidate_id'])] = a
for s in glob.glob(B + '/teacher_pilot_r1/export_r1/scored/*.json'):
    for a in json.load(open(s)):
        pk[('pilot', a['candidate_id'])] = dict(usable=a['usable'], text_token_count=a['stop']['token_count'] - (1 if a['stop']['eos'] else 0), eos=a['stop']['eos'])
for cell, d in res.items():
    dis = [(c, v['why'], pk[(cell, c)]['usable']) for c, v in d.items() if v['usable'] != pk[(cell, c)]['usable']]
    tokdis = sum(1 for c, v in d.items() if v['tokens'] != pk[(cell, c)]['text_token_count'] + (1 if pk[(cell, c)]['eos'] else 0))
    print(cell, len(d), sum(v['usable'] for v in d.values()), sum(pk[(cell, c)]['usable'] for c in d), len(dis), dis[:6], tokdis)
