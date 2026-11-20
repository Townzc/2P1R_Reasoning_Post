"""Independent A1 of P011 OT3 NFC complete inputs (Claude).
Usage: python3 -I a1_ot3.py X_DIR FAIL_DIR DISPOSITIONS REPO OUT"""
import sys, json, hashlib, unicodedata, collections, random, os
X, FAIL, DISP, REPO, OUT = sys.argv[1:6]
L = lambda d, f: json.load(open(f'{d}/{f}'))
shaf = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
hs = lambda t: hashlib.sha256(t.encode('utf-8')).hexdigest()
pk = lambda t: unicodedata.normalize('NFKC', t).strip()
res = {}
man = L(X, 'MANIFEST.json')['files']
res['manifest_files'] = len(man)
res['manifest_bad'] = [n for n, v in man.items() if shaf(f'{X}/{n}') != v['sha256'] or os.path.getsize(f'{X}/{n}') != v['bytes']]
res['manifest_sha'] = shaf(f'{X}/MANIFEST.json')

raw_lines = [l for l in open(f'{X}/SELECTED_RAW.jsonl', 'rb').read().split(b'\n') if l]
raws = [json.loads(l) for l in raw_lines]; raw = {r['path_id']: r for r in raws}
pk0 = lambda t: unicodedata.normalize('NFKC', t).strip()
IM_END, NL = 151645, 198
bad = collections.Counter(); prefixes = collections.defaultdict(set); encs = []; enc_line_sha = []
with open(f'{X}/ENCODED.jsonl', 'rb') as fh:
    for line in fh:
        line = line.rstrip(b'\n')
        if not line: continue
        enc_line_sha.append(hashlib.sha256(line).hexdigest())
        e = json.loads(line); p = e['path_id']
        ids, lab = e['input_ids'], e['labels']; s, t = e['assistant_start'], e['assistant_end']
        ok = (len(ids) == len(lab) == e['n_processed'] <= 16384 and all(x == -100 for x in lab[:s]) and lab[s:t] == ids[s:t]
              and all(x == -100 for x in lab[t:]) and ids[t - 1] == IM_END and t - s == e['n_supervised'] and s > 0
              and len(ids) - t == 1 and ids[-1] == NL and IM_END not in ids[s:t - 1] and e['eos_token_id'] == IM_END
              and e['template_final_newline_supervised'] is False)
        bad['structure'] += not ok
        bad['parent_sha'] += p not in raw or e['parent_sha256'] != hashlib.sha256(pk0(raw[p]['question']).encode()).hexdigest()
        prefixes[e['parent_sha256']].add(tuple(ids[:s]))
        del e['input_ids'], e['labels']; encs.append(e)
enc = {e['path_id']: e for e in encs}
norm = [json.loads(l) for l in open(f'{X}/NATIVE_NORMALIZATION.jsonl')]
res['counts'] = dict(raw=len(raws), raw_unique=len(raw), enc=len(encs), enc_unique=len(enc), norm=len(norm))
res['raw_sorted_by_path_id'] = [r['path_id'] for r in raws] == sorted(raw)
res['enc_order_equals_raw_order'] = [e['path_id'] for e in encs] == [r['path_id'] for r in raws]
res['norm_order_equals_raw_order'] = [n['path_id'] for n in norm] == [r['path_id'] for r in raws]

# 965 confirmed prefix: byte equality with failed partial outputs
f_raw = [l for l in open(f'{FAIL}/SELECTED_RAW.jsonl', 'rb').read().split(b'\n') if l]
f_enc = [hashlib.sha256(l).hexdigest() for l in open(f'{FAIL}/ENCODED.jsonl', 'rb').read().split(b'\n') if l]
res['failed_partial_lines'] = (len(f_raw), len(f_enc))
res['first965_raw_bytes_equal'] = raw_lines[:965] == f_raw[:965]
res['first965_enc_bytes_equal'] = enc_line_sha[:965] == f_enc[:965]
res['failed_raw_966th_equals_new_966th'] = len(f_raw) > 965 and f_raw[965] == raw_lines[965]
res['reused_flags_exactly_first965'] = [n['encoding_reused'] for n in norm] == [True] * 965 + [False] * (len(norm) - 965)

# parent order
reuse = L(X, 'CONFIRMED_PARENT_REUSE.json')
disp = [json.loads(l) for l in open(DISP)]
elig = [d['parent_sha256'] for d in disp if d['eligible']]
res['dispositions'] = (len(disp), len(elig))
res['all_confirmed_equals_disposition_eligible_order'] = reuse['all_confirmed_hashes'] == elig
res['selected_is_first4032'] = reuse['selected_hashes'] == elig[:4032]
res['unused_tail_is_last6'] = reuse['unused_tail_hashes'] == elig[4032:] and len(elig[4032:]) == 6
sel = reuse['selected_hashes']

# cells & nesting
inv = L(X, 'CELL_INVENTORY.json'); cells = inv['cells']
GRID = {'A1': (252, 1), 'A2': (252, 2), 'A3': (252, 4), 'A4': (252, 8), 'A5': (252, 16), 'A6': (1008, 1), 'A7': (4032, 1), 'A8': (1008, 4)}
par = lambda p: hs(pk(raw[p]['question']))
by_parent = collections.defaultdict(list)  # fullest observed per-parent response order
for c in ('A5', 'A8', 'A7'):
    for p in cells[c]:
        if p not in by_parent[par(p)]:
            by_parent[par(p)].append(p)
nest_ok = {}
for c, (P, K) in GRID.items():
    exp = [p for h in sel[:P] for p in by_parent[h][:K]]
    nest_ok[c] = (cells[c] == exp, len(cells[c]) == P * K, all(len(by_parent[h]) >= K for h in sel[:P]))
res['cell_nesting_ok'] = nest_ok
res['union_cells_equals_raw'] = set().union(*map(set, cells.values())) == set(raw)
res['parents_in_raw'] = len({par(p) for p in raw}); res['parents_equal_selected'] = {par(p) for p in raw} == set(sel)
res['per_parent_counts'] = dict(collections.Counter(len(v) for v in by_parent.values()))
# within-parent response order: recompute seeded shuffle for the 252 full-16 parents
SQL = lambda p: (raw[p]['source_file'], raw[p]['source_row'])
shuf_ok = 0
for h in sel[:252]:
    rows = sorted(by_parent[h], key=SQL)
    key = pk(raw[rows[0]]['question'])
    random.Random(hs(key + 'p011')[:16]).shuffle(rows)
    shuf_ok += rows == by_parent[h]
res['seeded_response_shuffle_ok_of_252'] = shuf_ok
res['source_row_int'] = all(type(r['source_row']) is int for r in raws)
res['path_id_format_ok'] = all(r['path_id'] == f"ot3:{r['source_file']}:{r['source_row']}" for r in raws)

# completeness, decontamination
region = lambda t: t.rsplit('</think>', 1)[-1] if '</think>' in t else t[-2000:]
res['all_complete'] = sum('\\boxed{' in region(r['response']) for r in raws)
res['think_closed'] = sum('</think>' in r['response'] for r in raws)
bench = L(X, 'BENCHMARKS.json')
res['benchmark_counts'] = dict(collections.Counter(b['benchmark'] for b in bench))
def grams(t):
    w = pk(t).split(); return {tuple(w[i:i + 13]) for i in range(max(0, len(w) - 12))}
bidx = set().union(*(grams(b['problem']) for b in bench)); bexact = {pk(b['problem']) for b in bench}
qs = {par(p): raw[p]['question'] for p in raw}
res['benchmarks_equal_original_failure'] = shaf(f'{X}/BENCHMARKS.json') == shaf(os.path.dirname(DISP) + '/BENCHMARKS.json')
res['decontam_hits'] = sum(pk(q) in bexact or bool(grams(q) & bidx) for q in qs.values())
res['difficulty_values'] = dict(collections.Counter(str(r['metadata'].get('difficulty')) for r in raws).most_common(3))

res['encoding_bad'] = dict(bad)
res['one_prefix_per_parent'] = all(len(v) == 1 for v in prefixes.values())
heads = {v2[:5] for v in prefixes.values() for v2 in v}
res['prefix_heads'] = [list(h) for h in heads]
res['max_processed'] = max(e['n_processed'] for e in encs)
res['min_supervised'] = min(e['n_supervised'] for e in encs)

# native text / NFC proof records (independent template string)
SYS = 'You are Qwen, created by Alibaba Cloud. You are a helpful assistant.'
nfc = lambda t: unicodedata.normalize('NFC', t)
nb = collections.Counter(); changed = []
for n in norm:
    r = raw[n['path_id']]; q, a = r['question'], r['response']
    prefix = f'<|im_start|>system\n{SYS}<|im_end|>\n<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n'
    full = prefix + a + '<|im_end|>\n'
    normalized = nfc(prefix) + nfc(a + '<|im_end|>') + nfc('\n')
    if n['encoding_reused']:
        nb['reused_but_raw_not_nfc'] += full != normalized
        nb['reused_flag_changed'] += n['normalization_changed_text'] is not False
        continue
    nb['raw_sha'] += n['raw_native_text_sha256'] != hs(full)
    nb['norm_sha'] += n['normalized_native_text_sha256'] != hs(normalized)
    nb['decoded_ne_norm'] += n['decoded_text_sha256'] != n['normalized_native_text_sha256']
    nb['q_sha'] += n['original_question_sha256'] != hs(q)
    nb['a_sha'] += n['original_response_sha256'] != hs(a)
    nb['flag'] += n['normalization_changed_text'] != (full != normalized)
    nb['chars'] += (n['raw_characters'], n['normalized_characters']) != (len(full), len(normalized))
    nb['rewritten'] += n['raw_text_rewritten'] is not False
    if full != normalized:
        diffs = sorted({unicodedata.name(ch, hex(ord(ch))) for ch in a if unicodedata.combining(ch)})
        changed.append(dict(path_id=n['path_id'], in_prefix=nfc(prefix) != prefix, chars=(len(full), len(normalized)), combining=diffs[:6]))
res['norm_mismatches'] = dict(nb); res['nfc_changed'] = changed

# dose & plans
dose = L(X, 'FROZEN_DOSE.json')
once = {c: sum(enc[p]['n_supervised'] for p in v) for c, v in cells.items()}
res['once_recomputed_equal'] = once == dose['once_pass_tokens']; res['once'] = once
res['B_max_U'] = (dose['B'] == max(once.values()), dose['U'] == -(-dose['B'] // 64000), dose['B'], dose['U'])
plans = {}
for c in GRID:
    pl = L(X, f'{c}_PLAN.json'); rows = pl['row_path_ids']; n = len(rows)
    lengths = [enc[p]['n_supervised'] for p in rows]
    stream = [i for u in pl['updates'] for i in u]; q = pl['q']; cnt = collections.Counter(stream)
    exp = []
    for ep in range(q):
        o = list(range(n)); random.Random(f'17:pass:{ep}').shuffle(o); exp += o
    extras = stream[q * n:]
    plans[c] = dict(rows_eq_cell=rows == cells[c], q=q, q_expected=dose['B'] // once[c], n=n, updates=len(pl['updates']),
        U_ok=len(pl['updates']) == dose['U'] == pl['optimizer_updates'], tokens_eq_B=sum(lengths[i] for i in stream) == dose['B'] == pl['supervised_tokens'],
        exposures_q_q1=set(cnt.values()) <= {q, q + 1} and len(cnt) == n, passes_match_seed=stream[:q * n] == exp,
        extras=len(extras), extras_unique=len(set(extras)) == len(extras),
        extras_sum_eq_remainder=sum(lengths[i] for i in extras) == dose['B'] - q * once[c],
        nonempty=all(pl['updates']), exposures_field=pl['exposures'] == [cnt[i] for i in range(n)],
        upd_tok_min_max=(min(sum(lengths[i] for i in u) for u in pl['updates']), max(sum(lengths[i] for i in u) for u in pl['updates'])))
res['plans'] = plans

# rerun the CR-accepted scheduler (deterministic replay) and compare full plan
sys.path.insert(0, REPO)
from experiments.p011 import data_contract as rules
replay = {}
for c in GRID:
    pl = L(X, f'{c}_PLAN.json'); rows = [enc[p] for p in pl['row_path_ids']]
    out = rules.whole_schedule(rows, dose['B'])
    replay[c] = (out == pl, out['updates'] == pl['updates'])
res['scheduler_replay_equal'] = replay
json.dump(res, open(OUT, 'w'), indent=1, ensure_ascii=False); print(json.dumps(res, indent=1, ensure_ascii=False))
