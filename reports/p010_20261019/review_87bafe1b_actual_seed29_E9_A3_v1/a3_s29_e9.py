import json, sys, re, random, collections
REPO, Z, OUT = sys.argv[1:4]
P = f'{REPO}/reports/p010_20261019'
exec(open(sys.argv[0].replace('a3_s29_e9.py','a3_all.py')).read().split("cells = {}; checks = {}")[0].split("REPO, Z, OUT")[0])
REPO, Z, OUT = sys.argv[1:4]; P = f'{REPO}/reports/p010_20261019'
gold = {r['problem_id']: r['gold'] for r in json.load(open(f'{Z}/p1/original/ROWS.json')) if r['dataset'] == 'qwen_math_zero'}
PIDS = sorted(gold)
src = open(sys.argv[0].replace('a3_s29_e9.py','a3_all.py')).read()
ns = {}; exec(src.split("cells = {}; checks = {}")[0].replace("REPO, Z, OUT = sys.argv[1:4]", "REPO, Z, OUT = %r, %r, %r" % (REPO, Z, OUT)), ns)
load = ns['load']; S = [f'sample{i}' for i in range(4)]
cells, checks = {}, {}
for c in ('t15_s29_n400_k1','t15_s29_n3200_k1','t72_s29_n400_k1','t72_s29_n3200_k1'):
    v, ch = load(f'{P}/seed29_results_v1/{c}/', ['greedy'] + S); cells[c] = v; checks[c] = ch
for c in ('e9_base_math','e9_s17_n400','e9_s17_n3200'):
    v, ch = load(f'{P}/e9_results_v1/{c}/', ['greedy']); cells[c] = v; checks[c] = ch
summ = {c: dict(greedy=sum(v['greedy'].values()), sampled=(sum(sum(v[s].values()) for s in S) if 'sample0' in v else None)) for c, v in cells.items()}
rng = random.Random(20261020); idx = [[rng.randrange(500) for _ in range(500)] for _ in range(10000)]
def con(a, b, m):
    if m == 'greedy': x = [cells[a]['greedy'][p] for p in PIDS]; y = [cells[b]['greedy'][p] for p in PIDS]
    else: x = [sum(cells[a][s][p] for s in S)/4 for p in PIDS]; y = [sum(cells[b][s][p] for s in S)/4 for p in PIDS]
    d = [yy-xx for xx, yy in zip(x, y)]; bs = sorted(100*sum(d[i] for i in ii)/500 for ii in idx)
    return dict(diff_pp=round(100*sum(d)/500, 2), ci95=(round(bs[250], 2), round(bs[9749], 2)))
res = dict(checks=checks, summary=summ, contrasts={
 'dP_T15_s29': {m: con('t15_s29_n400_k1','t15_s29_n3200_k1',m) for m in ('greedy','sampled')},
 'dP_T72_s29': {m: con('t72_s29_n400_k1','t72_s29_n3200_k1',m) for m in ('greedy','sampled')},
 'dT_n400_s29': {m: con('t15_s29_n400_k1','t72_s29_n400_k1',m) for m in ('greedy','sampled')},
 'dT_n3200_s29': {m: con('t15_s29_n3200_k1','t72_s29_n3200_k1',m) for m in ('greedy','sampled')},
 'E9_dP': {'greedy': con('e9_s17_n400','e9_s17_n3200','greedy')},
 'E9_n400_vs_base': {'greedy': con('e9_base_math','e9_s17_n400','greedy')}})
json.dump(res, open(OUT,'w'), indent=1); print(json.dumps(res, indent=1))
