"""Independent A1 of P011 long preflight saved-token subset (Claude). Usage: a1_pf.py SUBSET OT3X LONGIN OUT"""
import sys, json, hashlib, math, collections
X, OT3, LI, OUT = sys.argv[1:5]
shaf = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
dumps = lambda v: json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False)
dig = lambda v: hashlib.sha256(dumps(v).encode()).hexdigest()
R = {}
man = json.load(open(f'{X}/MANIFEST.json'))
R['manifest_entries'] = len(man)
R['manifest_bad'] = [n for n, v in man.items() if shaf(f'{X}/{n}') != (v['sha256'] if isinstance(v, dict) else v)]
# rebuild original A8 ordered rows from OT3 ENCODED.jsonl
plan8 = json.load(open(f'{LI}/A8/plan.json')); orig_rows = json.load(open(f'{LI}/A8/ORIGINAL_ROWS.json'))
want = set(plan8['row_path_ids']); got = {}
with open(f'{OT3}/ENCODED.jsonl', 'rb') as f:
    for line in f:
        i = line.find(b'"path_id": "'); j = line.find(b'"', i + 12); pid = line[i + 12:j].decode()
        if pid in want: got[pid] = json.loads(line)
a8 = [got[p] for p in plan8['row_path_ids']]
R['a8_rows'] = len(a8); R['a8_digest_eq_original_row_values'] = dig(a8) == orig_rows['original_row_values_sha256']
a8dig = dig(a8)
gpu = json.load(open(f'{LI}/baseline/ENDPOINT_GPU.json')); local = json.load(open(f'{LI}/baseline/ENDPOINT_LOCAL.json'))
gdig = dig(gpu)
# independent selection
mine_rows = sorted(a8, key=lambda r: (-r['n_processed'], r['path_id']))[:2]
counts = {'math500': 500, 'aime24': 30, 'aime25': 30, 'amc23': 40}
mine_req = []
for b, n in counts.items():
    src = sorted((r for r in gpu if r['benchmark'] == b and r['mode'] == 'sample' and r['seed'] == 0), key=lambda r: (-len(r['prompt_token_ids']), r['id']))
    assert len(src) == n
    ch = [src[(i * (n - 1)) // 7] for i in range(8)]
    if b == 'math500':
        g = [r for r in gpu if r['benchmark'] == b and r['mode'] == 'greedy' and r['problem_id'] == ch[0]['problem_id']]; assert len(g) == 1; ch[-1] = g[0]
    mine_req += ch
def peak(U, pk):
    warm = max(1, math.ceil(.05 * U))
    return [pk * s / warm if s <= warm else pk * (.1 + .45 * (1 + math.cos(math.pi * (s - warm) / (U - warm)))) for s in range(1, U + 1)]
PEAK = {'S-L15': 1e-4, 'S-F15': 1e-5, 'S-L3': 1e-4}
lkey = {r['id']: r for r in local}
arms = {}
for arm, pk in PEAK.items():
    a = {}
    enc = json.load(open(f'{X}/{arm}/encoded.json')); plan = json.load(open(f'{X}/{arm}/plan.json'))
    rates = json.load(open(f'{X}/{arm}/rates_{arm}.json')); eg = json.load(open(f'{X}/{arm}/ENDPOINT_GPU.json')); el = json.load(open(f'{X}/{arm}/ENDPOINT_LOCAL.json'))
    proof = json.load(open(f'{X}/{arm}/SUBSET_PROOF.json'))
    a['encoded_eq_independent_two_longest'] = enc == mine_rows
    a['rows_in_A8_plan_bytes'] = all(r['path_id'] in want for r in enc)
    a['n_processed'] = [r['n_processed'] for r in enc]; a['n_supervised'] = [r['n_supervised'] for r in enc]
    a['third_longest_n_processed'] = sorted(a8, key=lambda r: (-r['n_processed'], r['path_id']))[2]['n_processed']
    bad = 0
    for r in enc:
        ids, lab, s, e = r['input_ids'], r['labels'], r['assistant_start'], r['assistant_end']
        bad += not (len(ids) == len(lab) == r['n_processed'] <= 16384 and lab == [-100] * s + ids[s:e] + [-100] * (len(ids) - e)
                    and r['n_supervised'] == e - s and ids[e - 1] == 151645 and r['eos_token_id'] == 151645)
    a['row_mask_bad'] = bad
    a['B'] = plan['supervised_tokens']; a['B_ok'] = plan['supervised_tokens'] == 2 * sum(r['n_supervised'] for r in enc)
    a['processed_ok'] = plan['processed_tokens'] == 2 * sum(r['n_processed'] for r in enc)
    a['plan_fields_ok'] = (plan['optimizer_updates'] == 2 and plan['updates'] == [[0, 1], [0, 1]] and plan['seed'] == 17
                           and plan['row_path_ids'] == [r['path_id'] for r in enc] and plan['engineering_preflight'] is True and plan['scientific_cell_result'] is False)
    a['plan_source_encoded_eq_A8'] = plan['source_encoded_sha256'] == a8dig and proof['source_encoded_sha256'] == a8dig
    a['plan_source_requests_eq_GPU'] = plan['source_requests_sha256'] == gdig and proof['source_requests_sha256'] == gdig
    a['rates'] = rates; a['rates_ok'] = len(rates) == 2 and max(abs(x - y) for x, y in zip(rates, peak(2, pk))) < 1e-18
    a['gpu_eq_independent_selection'] = eg == mine_req
    a['local_eq_original_local'] = el == [lkey[r['id']] for r in mine_req]
    a['gpu_no_gold'] = not any('gold' in r for r in eg)
    a['gpu_is_projection_of_local'] = all(g == {**{k: v for k, v in l.items() if k != 'gold'}, 'request_sha256': dig(l)} for g, l in zip(eg, el))
    a['bench_counts'] = dict(collections.Counter(r['benchmark'] for r in eg)); a['modes'] = dict(collections.Counter(r['mode'] for r in eg))
    a['max_required_context'] = max(r['required_context'] for r in eg)
    a['proof_digests_ok'] = proof['selected_training_sha256'] == dig(enc) and proof['plan_sha256'] == dig(plan) and proof['selected_requests_sha256'] == dig(eg)
    a['file_shas'] = {n: shaf(f'{X}/{arm}/{n}') for n in ('encoded.json', 'plan.json', f'rates_{arm}.json', 'ENDPOINT_GPU.json', 'ENDPOINT_LOCAL.json', 'SUBSET_PROOF.json')}
    arms[arm] = a
R['arms'] = arms
R['cross_arm_encoded_plan_endpoint_identical'] = len({(v['file_shas']['encoded.json'], v['file_shas']['plan.json'], v['file_shas']['ENDPOINT_GPU.json']) for v in arms.values()}) == 1
c = json.load(open(f'{X}/COMPLETED.json'))
R['completed'] = {k: c.get(k) for k in ('model_calls', 'owner_decision_sha256', 'actual_A1_accepted', 'completed_epoch')}
R['completed_proof_file_shas_ok'] = all(c['proofs'][arm]['local_input_files'][n]['sha256'] == arms[arm]['file_shas'][n] for arm in arms for n in arms[arm]['file_shas'])
json.dump(R, open(OUT, 'w'), indent=1); print(json.dumps(R, indent=1)[:6000])
