"""Independent A1 of P011 long A/D runtime inputs (Claude). Usage: a1_long.py NEW OT3X AMX OUT"""
import sys, json, hashlib, math, collections, unicodedata
NEW, OT3, AM, OUT = sys.argv[1:5]
shaf = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
dumps = lambda v: json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False)
dig = lambda v: hashlib.sha256(dumps(v).encode()).hexdigest()
R = {}
man = json.load(open(f'{NEW}/MANIFEST.json'))
R['new_manifest_bad'] = [n for n, v in man.items() if __import__('os').path.exists(f'{NEW}/{n}') and shaf(f'{NEW}/{n}') != v['sha256']]
R['new_manifest_missing_in_public_archive'] = sorted(n for n in man if not __import__('os').path.exists(f'{NEW}/{n}'))

def offsets(path):
    off = {}; pos = 0
    with open(path, 'rb') as f:
        for line in f:
            pid = json.loads(line[:400].split(b'"path_id": "')[1].split(b'"')[0].decode()) if False else None
            off_line = pos; pos += len(line)
            # parse path_id cheaply
            i = line.find(b'"path_id": "'); j = line.find(b'"', i + 12)
            off[line[i + 12:j].decode()] = (off_line, len(line))
    return off

def peak(updates, arm_peak):
    U = updates; warm = max(1, math.ceil(.05 * U))
    return [arm_peak * s / warm if s <= warm else arm_peak * (.1 + .45 * (1 + math.cos(math.pi * (s - warm) / (U - warm)))) for s in range(1, U + 1)]
PEAK = {'S-L15': 1e-4, 'S-F15': 1e-5, 'S-L3': 1e-4}

res = {}
for src, cells in ((OT3, [f'A{i}' for i in range(1, 9)]), (AM, ['D1', 'D2'])):
    enc_path = f'{src}/ENCODED.jsonl'; off = offsets(enc_path); enc_sha = shaf(enc_path)
    fh = open(enc_path, 'rb')
    for c in cells:
        r = {}
        plan_bytes = open(f'{NEW}/{c}/plan.json', 'rb').read()
        orig_bytes = open(f'{src}/{c}_PLAN.json', 'rb').read()
        r['plan_bytes_equal'] = plan_bytes == orig_bytes
        plan = json.loads(plan_bytes); rows = json.load(open(f'{NEW}/{c}/ORIGINAL_ROWS.json'))
        r['ordered_ids_eq_plan'] = rows['ordered_path_ids'] == plan['row_path_ids']
        r['source_encoded_sha_ok'] = rows['source_encoded_sha256'] == enc_sha
        r['plan_file_sha_ok'] = rows['plan_file_sha256'] == shaf(f'{src}/{c}_PLAN.json')
        r['training_tokenizations'] = rows['training_tokenizations']
        h = hashlib.sha256(); h.update(b'[')
        for k, pid in enumerate(plan['row_path_ids']):
            o, n = off[pid]; fh.seek(o); obj = json.loads(fh.read(n))
            if k: h.update(b',')
            h.update(dumps(obj).encode())
        h.update(b']')
        r['row_values_sha_recomputed_eq'] = h.hexdigest() == rows['original_row_values_sha256']
        r['n_rows'] = len(plan['row_path_ids']); r['U'] = plan['optimizer_updates']; r['B'] = plan['supervised_tokens']
        for arm, pk in PEAK.items():
            rates = json.load(open(f'{NEW}/{c}/rates_{arm}.json'))
            mine = peak(plan['optimizer_updates'], pk)
            r[f'rates_{arm}'] = len(rates) == len(mine) and max(abs(a - b) for a, b in zip(rates, mine)) < 1e-15
        res[c] = r
R['cells'] = res

# endpoints and gold
bench = json.load(open(f'{OT3}/BENCHMARKS.json'))
R['am_benchmarks_bytes_equal_ot3'] = open(f'{AM}/BENCHMARKS.json', 'rb').read() == open(f'{OT3}/BENCHMARKS.json', 'rb').read()
gold = json.load(open(f'{NEW}/ORIGINAL_GOLD_PROJECTION.json'))
bkey = {(b['benchmark'], b['source_row']): b for b in bench}
gbad = collections.Counter(); types = collections.Counter()
for g in gold:
    b = bkey[(g['benchmark'], g['source_row'])]; a = b['answer']; types[type(a).__name__] += 1
    gbad['orig'] += g['original_answer'] != a or g['original_answer_type'] != type(a).__name__ or g['original_row_sha256'] != dig(b)
    exp = a if isinstance(a, str) else str(a) if type(a) is int else (str(int(a)) if isinstance(a, float) and a.is_integer() else None)
    gbad['canon'] += g['canonical_gold'] != exp
    gbad['projected_sha'] += g['projected_row_sha256'] != dig({**b, 'answer': exp})
R['gold'] = dict(n=len(gold), types=dict(types), bad=dict(gbad))
local = json.load(open(f'{NEW}/baseline/ENDPOINT_LOCAL.json')); gpu = json.load(open(f'{NEW}/baseline/ENDPOINT_GPU.json'))
roster = json.load(open(f'{NEW}/ENDPOINT_ROSTER.json'))
R['roster_eq_local'] = roster == local
expected_ids = [f'{b}:{i:04d}:{m}:{s}' for b, n in (('math500', 500), ('aime24', 30), ('aime25', 30), ('amc23', 40)) for i in range(n)
                for m, ss in ([('sample', range(4)), ('greedy', [0])] if b == 'math500' else [('sample', range(8))]) for s in ss]
R['ids_set_eq'] = set(r['id'] for r in local) == set(expected_ids) and len(local) == 3300
ebad = collections.Counter(); prompts = {}
canon = {(g['benchmark'], g['source_row']): g['canonical_gold'] for g in gold}
for l, g in zip(local, gpu):
    ebad['gpu_proj'] += g != {**{k: v for k, v in l.items() if k != 'gold'}, 'request_sha256': dig(l)}
    ebad['gold'] += l['gold'] != canon[(l['benchmark'], l['source_row'])]
    ebad['ctx'] += l['required_context'] != len(l['prompt_token_ids']) + 16384
    p = (tuple(l['prompt_token_ids']), l['prompt_text_sha256'], l['raw_prompt_text_sha256'], l['native_NFC_changed'])
    ebad['prompt_consistency'] += prompts.setdefault(l['problem_id'], p) != p
    ebad['gold_in_gpu'] += 'gold' in g
R['endpoint_bad'] = dict(ebad); R['max_context'] = max(r['required_context'] for r in local)
R['nfc_changed_prompts'] = sum(p[3] for p in prompts.values())
R['prompt_head'] = collections.Counter(p[0][:3] for p in prompts.values()).most_common(2)
R['unique_problems'] = len(prompts)
# raw prompt text sha vs native template (default system) text reconstruction
SYS = 'You are Qwen, created by Alibaba Cloud. You are a helpful assistant.'
pbad = 0; nbad = 0
for b in bench:
    pid = f"{b['benchmark']}:{b['source_row']:04d}"; t = f'<|im_start|>system\n{SYS}<|im_end|>\n<|im_start|>user\n{b["problem"]}<|im_end|>\n<|im_start|>assistant\n'
    p = prompts[pid]; pbad += p[2] != dig(t); nbad += p[1] != dig(unicodedata.normalize('NFC', t))
R['raw_prompt_text_sha_mismatch'] = pbad; R['nfc_prompt_text_sha_mismatch'] = nbad
c = json.load(open(f'{NEW}/COMPLETED.json'))
R['completed'] = dict(max_context=c['max_context'], endpoint_count=c['endpoint_count'], training_tokenizations=c['training_tokenizations'],
                      endpoint_input_ids_sha_ok=c['endpoint_input_ids_sha256'] == dig(local), proofs=len(c['proofs']))
json.dump(R, open(OUT, 'w'), indent=1); print(json.dumps(R, indent=1))
