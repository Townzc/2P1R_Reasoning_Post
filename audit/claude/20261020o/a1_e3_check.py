"""Independent A1 of P010 E3 inputs (Claude).
Usage: python3 -I a1_e3_check.py E3_IN T72RAW_DIR T72_EV_DIR REPO OUT
Compares frozen E3 inputs against the original T72 raw records (seed, prompt ids, sampling),
the frozen MATH_ROSTERS hash200 rule, and the A1-audited T72 RECORD_INDEX."""
import json, sys, glob, hashlib, collections
IN, RAW, EV, REPO, OUT = sys.argv[1:6]
P = f'{REPO}/reports/p010_20261019'
L = lambda f: json.load(open(f))
res = {}
ros = L(f'{P}/t72_data_candidate_v1/MATH_ROSTERS.json')
s1 = L(f'{REPO}/reports/p009_20261014/stage1_s1_inputs_v1/ROSTER_s17.json')['selections']
q400 = [p.split('::')[0] for p in s1['400']['path_ids']]
mine = sorted(q400, key=lambda pid: hashlib.sha256(('p010-e3:20261019:' + pid).encode()).hexdigest())[:200]
R = L(f'{IN}/ROSTER.json')
res['roster_sha_matches_frozen'] = hashlib.sha256(open(f'{P}/t72_data_candidate_v1/MATH_ROSTERS.json', 'rb').read()).hexdigest() == R['original_frozen_roster_sha256']
res['hash200_reproduced_exact_order'] = mine == ros['e3_hash200'] == R['problem_ids']
res['hash200_subset_of_n400'] = set(mine) <= set(q400) and len(set(mine)) == 200
raw = {}
for f in glob.glob(f'{RAW}/raw/*.json'):
    for r in L(f):
        assert r['candidate_id'] not in raw; raw[r['candidate_id']] = r
res['t72_raw_records'] = len(raw)
chk = collections.Counter(); bad = []
for lab, temp in (('t06', .6), ('t10', 1.0)):
    rows = L(f'{IN}/{lab}_requests.json'); chk[f'{lab}_rows'] = len(rows)
    ids = set()
    for r in rows:
        cid = r['original_seed_candidate_id']; o = raw[cid]
        ids.add(r['candidate_id'])
        ok = (r['candidate_id'] == f'p010_e3/{lab}/{cid}' and r['problem_id'] == o['problem_id'] and r['prompt_token_ids'] == o['prompt_token_ids']
              and r['seed'] == o['sampling']['seed'] == r['sampling']['seed'] and r['temperature'] == temp == r['sampling']['temperature']
              and {k: v for k, v in r['sampling'].items() if k != 'temperature'} == {k: v for k, v in o['sampling'].items() if k != 'temperature'}
              and o['sampling']['temperature'] == 0.8 and 1 <= r['attempt'] <= 8 and cid.endswith(f"::attempt{r['attempt']:02d}")
              and len(r['prompt_token_ids']) + 1024 <= 2048)
        if not ok: bad.append(r['candidate_id'])
    chk[f'{lab}_unique_ids'] = len(ids)
    per = collections.Counter(r['problem_id'] for r in rows)
    chk[f'{lab}_each_q_8'] = int(set(per.values()) == {8} and set(per) == set(mine))
res['request_checks'] = dict(chk); res['request_mismatches'] = len(bad); res['mismatch_examples'] = bad[:5]
t6 = {r['original_seed_candidate_id']: r['seed'] for r in L(f'{IN}/t06_requests.json')}
t10 = {r['original_seed_candidate_id']: r['seed'] for r in L(f'{IN}/t10_requests.json')}
res['same_seed_across_temps'] = t6 == t10
res['distinct_seeds_within_temp'] = len(set(t6.values())) == 1600
# reused T0.8 rows vs audited RECORD_INDEX
idx = L(f'{EV}/RECORD_INDEX.json'); T8 = L(f'{IN}/ORIGINAL_T08_ROWS.json')
dig = lambda o: hashlib.sha256(json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
res['t08_rows'] = len(T8)
res['t08_identical_to_audited_index'] = all(x['original_record'] == idx[x['original_candidate_id']] for x in T8)
res['t08_cover_attempt1_8_of_hash200'] = sorted(x['original_candidate_id'] for x in T8) == sorted(f'{p}::attempt{a:02d}' for p in mine for a in range(1, 9))
res['t08_record_digest_consistent_any'] = sum(x['original_record_sha256'] == dig(x['original_record']) for x in T8)
res['t08_usable'] = sum(bool(x['original_record']['usable']) for x in T8)
res['t08_correct'] = sum(bool(x['original_record']['score']['score'].get('correct')) for x in T8 if x['original_record'].get('score'))
res['t08_stop_reasons'] = dict(collections.Counter(x['original_record']['stop']['stop_reason'] for x in T8))
# prompt texts / gold
pt = L(f'{IN}/PROMPT_TEXTS.json'); gs = L(f'{IN}/GOLD_SOURCE.json')
res['prompt_text_ids_match'] = [x['problem_id'] for x in pt] == mine and all(x['prompt_token_ids'] == raw[x['problem_id'] + '::attempt01']['prompt_token_ids'] for x in pt)
src = {x['problem_id']: x for x in L(f'{P}/t72_data_candidate_v1/MATH_SOURCE.json')}
res['gold_source_rows_equal_frozen_source'] = [x['problem_id'] for x in gs] == mine and all(x == src[x['problem_id']] for x in gs)
json.dump(res, open(OUT, 'w'), indent=1); print(json.dumps(res, indent=1))
