"""Independent G3 of the published P008 final CPU integrity packet (git objects only)."""
import hashlib, json, subprocess, sys, collections
R = '/home/claude/2P1R_Reasoning_Post'
C = sys.argv[1]           # packet commit
EXE = sys.argv[2]         # execution commit (ee1100bd)
X = sys.argv[3]           # extracted compact tar dir
P = 'reports/p008_20261013/final_cpu_integrity_v1'
CAMP = 'midpoint/p008-students-completion-20261013-r1/'

def blob(c, p):
    r = subprocess.run(['git', '-C', R, 'show', f'{c}:{p}'], capture_output=True)
    if r.returncode: raise SystemExit(f'missing {c}:{p}')
    return r.stdout
def J(c, p): return json.loads(blob(c, p))
def H(b): return hashlib.sha256(b).hexdigest()
def D(v): return H(json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
out = collections.OrderedDict(); fails = []
def check(name, ok, info=None):
    out[name] = {'ok': bool(ok), 'info': info}
    if not ok: fails.append(name)

AM = J(C, P + '/ARTIFACT_MANIFEST.json'); E = J(C, P + '/ENVELOPE.json'); L = J(C, P + '/LEDGER.json')
rec, res = E['receipt'], E['result']
# 1. artifact bytes
cont = {'compact_evidence.tar.gz', 'compact_manifest.json', 'bundle_receipt.json'}
bad = []
for n, v in AM.items():
    b = blob(C, P + '/' + n) if n in cont else open(f'{X}/{n}', 'rb').read()
    if H(b) != v['sha256'] or len(b) != v['bytes']: bad.append(n)
check('artifact_manifest_78_bytes', len(AM) == 78 and not bad, {'n': len(AM), 'bad': bad})
check('artifact_manifest_eq_envelope', AM == E['artifact_manifest'])
check('evidence_digest_eq_receipt', D(AM) == rec['evidence_sha256'], D(AM))
CM = J(C, P + '/compact_manifest.json')
import os
xf = {os.path.relpath(os.path.join(dp, f), X) for dp, _, fs in os.walk(X) for f in fs}
cmf = CM.get('files', CM)
check('compact_manifest_eq_tar', set(cmf) == xf and all(H(open(f'{X}/{n}', 'rb').read()) == (v['sha256'] if isinstance(v, dict) else v) for n, v in cmf.items()), {'tar': len(xf), 'manifest': len(cmf)})
check('result_eq_envelope', json.load(open(f'{X}/result.json')) == res)
# 2. sources / admission / binding
intent = json.load(open(f'{X}/intent.json')); adm = json.load(open(f'{X}/admission.json'))
rel = intent['release']; src = rel['source_files']
srcbad = [p for p, h in src.items() if H(blob(EXE, p)) != h]
check('19_sources_eq_exec_commit', len(src) == 19 and not srcbad and rel['commit'].startswith(EXE[:8]), {'commit': rel['commit'], 'digest': D(src), 'bad': srcbad})
check('sources_eq_published_bundle', src == J(C, P + '/SOURCE_BUNDLE.json') == J(C, P + '/ADMISSION.json')['source_files'])
check('binding_digest', D(intent['binding']) == '08416dc337201295fc5ae5a4cfa682f12db8a40165f7cb45d03f84c653d1a2a5', D(intent['binding']))
check('admission_digest', D(adm) == 'feba9e73118862e87a5a1272a294b1e97ee7afcaae5187a95dfde3954011d27a', D(adm))
# 3. ledger: CPU claim/intent/terminal/attempt
cl, it, te = (L[CAMP + k + '/audit'] for k in ('claim', 'intent', 'terminal'))
att = {k: v for k, v in L.items() if k.startswith(CAMP + 'attempt/audit/')}
plan = L[CAMP + 'campaign']
check('cpu_intent', it == dict(run_id='audit', config_sha256=D(intent['binding']), source_sha256=D(src), data_sha256=D(intent['binding']['input_manifest'])))
check('cpu_claim', cl['intent_sha256'] == D(it) and cl['plan_sha256'] == D(plan) and cl['reserved_cents'] == 500 and cl['deadline_epoch'] - cl['claimed_epoch'] == 3300)
check('one_attempt', list(att.values()) == [cl] and list(att)[0].endswith(cl['attempt_id']))
check('terminal_eq_receipt', te == rec and te['status'] == 'completed' and te['claim_sha256'] == D(cl) and te['actual_cost_cents'] == 500)
hs = min(intent['started_epoch'] + 3300, plan['deadline_epoch'] - 30)
check('clocks', intent['hard_stop_epoch'] == hs and intent['started_epoch'] <= cl['claimed_epoch'] <= te['finished_epoch'] <= min(hs, cl['deadline_epoch']),
      {'entry_to_terminal': te['finished_epoch'] - intent['started_epoch'], 'claim_to_terminal': te['finished_epoch'] - cl['claimed_epoch'], 'result_wall': res['wall_seconds']})
# 4. journal
roster = sorted(intent['binding']['labels'])
units = {k[len(CAMP + 'audit/unit/'):]: v for k, v in L.items() if k.startswith(CAMP + 'audit/unit/')}
dones = {k[len(CAMP + 'audit/done/'):]: v for k, v in L.items() if k.startswith(CAMP + 'audit/done/')}
jb = []
for n in roster:
    pb = open(f'{X}/proofs/{n}.json', 'rb').read()
    if json.load(open(f'{X}/intents/{n}.json')) != units.get(n): jb.append((n, 'unit'))
    if dones.get(n, {}).get('proof_sha256') != H(pb) or json.load(open(f'{X}/completed/{n}.json')) != dones.get(n): jb.append((n, 'done'))
    if json.loads(pb) != res['labels'][n]: jb.append((n, 'aggregate'))
check('journal_24', len(roster) == 24 and set(units) == set(dones) == set(roster) == set(res['labels']) and not jb, jb)
# 5. per-proof against ORIGINAL published packets (not CPU inputs)
pk = {}
for n in roster:
    base = n.replace('_replacement_r1', '')
    if n.endswith('_replacement_r1'): pk[n] = f'reports/p008_20261013/student_t1_replacements_v1/{n}'
    elif n.endswith('_t8'): pk[n] = f'reports/p008_20261013/t8_results_v1/{n}'
    elif n.endswith('_t1'): pk[n] = f'reports/p008_20261013/student_t1_eight_v1/{n}'
states = {}; pb_ = []; copied = 0; state_bytes = 0; statuses = {}
for n in roster:
    p = res['labels'][n]
    if not (p['passed'] is True and p['new_model_calls'] == 0): pb_.append((n, 'pass'))
    statuses[n] = p.get('original_status', 'completed')
    if n in pk and statuses[n] != 'failed':
        am = J(C, pk[n] + '/artifact_manifest.json'); orc = J(C, pk[n] + '/LOCAL_ORACLE_AUDIT.json')
        want = {k.split('/')[0].split('_')[1].lstrip('0'): v['sha256'] for k, v in am.items() if k.endswith('/state.pt')}
        if p['checkpoint_sha256'] != want: pb_.append((n, 'state', p['checkpoint_sha256'], want))
        if p['original_artifact_digest'] != D(am) or p['files_verified'] != len(am): pb_.append((n, 'artifact'))
        if p['local_oracle_sha256'] != D(orc): pb_.append((n, 'oracle'))
        if 'not repeated' not in p['raw_rescoring_scope']: pb_.append((n, 'scope'))
        cs = p['timings']['copy_and_sha']
        if p['copied_bytes'] != sum(v['bytes'] for v in cs.values()): pb_.append((n, 'bytes'))
        for k, v in cs.items():
            if k in am and am[k]['bytes'] != v['bytes']: pb_.append((n, 'copybytes', k))
        states[n] = p['checkpoint_sha256']; copied += p['copied_bytes']
        state_bytes += sum(v['bytes'] for k, v in cs.items() if k.endswith('state.pt'))
        if n.endswith('_t8'):
            w = dict(effective_worker_seconds=9600, original_config_seconds=9560, original_reserved_cents=1253, supplement_reserved_cents=5, total_reserved_cents=1258, original_N2_passed=False, post_hoc_engineering_deviation=True, cap_spec_sha256='4ca2c55deb53307ddc96b8f6b631127958dd40ddbdc6d536986e38e7798a0044')
            if {k: p[k] for k in w} != w: pb_.append((n, 't8amend'))
    else:
        copied += p.get('copied_bytes', 0) or sum(v.get('bytes', 0) for v in (p.get('timings') or {}).get('copy_and_sha', {}).values()) if isinstance(p.get('timings'), dict) and 'copy_and_sha' in p['timings'] else 0
nstate = sum(len(v) for v in states.values())
check('proofs_vs_original_packets', not pb_, pb_)
check('26_states', nstate == 26 and sum(1 for n in states if n.endswith('_t8')) == 8, {'states': nstate, 'state_bytes': state_bytes, 'student_copied_bytes': copied})
failed = sorted(n for n, s in statuses.items() if s == 'failed')
fz = {n: (res['labels'][n].get('attempted_updates'), res['labels'][n].get('endpoint_outputs')) for n in failed}
check('3_failed_retained', failed == ['d1_b1_p0_breadth_t1', 'd1_b1_p0_depth_t1', 'pool_d2_parent'] and fz['d1_b1_p0_breadth_t1'] == (0, 0) == fz['d1_b1_p0_depth_t1'], fz)
# 6. original physical claims/terminals unchanged + T8 amendment records
lb = []
for n, item in intent['binding']['labels'].items():
    for kind in ('claim', 'terminal'):
        hit = [k for k, v in L.items() if k.endswith(f'/{kind}/{item["run_id"]}') and v == item[kind]]
        if not hit: lb.append((n, kind))
check('original_claims_terminals_in_ledger', not lb, lb)
am9 = [k for k in L if 't8_cap_9600_amendment' in k]
check('9_t8_amendment_records', len(am9) == 9, len(am9))
check('no_reset_extra_audit_claims', sum(1 for k in L if k.endswith('/claim/audit')) == 1)
# 7. provider
pv = J(C, P + '/PROVIDER.json')
check('provider_stopped', [a['app_id'] for a in pv['apps']] == ['ap-Ks3n5PzR1MpauTeQwueUQe'] and pv['apps'][0]['lifecycle']['state'] == 'stopped' and pv['owned_containers'] == [])
# 8. aggregate fields
w = dict(passed=True, t8_operational_amendment_verified=True, original_N2_passed=False, post_hoc_engineering_deviation=True, logical_runs=21, physical_sources=24, original_d2_status='failed', child_status='completed', reserved_cost_usd=5, provider_invoice_usd=None, new_model_calls=0)
check('aggregate_scope', {k: res[k] for k in w} == w)
O = J(C, P + '/OBSERVED_PROOF_ROSTER.json')
check('observed_roster', O['state_identities'] == states and O['retained_failed_sources'] == failed and O['counts'] == dict(completed_physical_sources=21, failed_physical_sources=3, physical_sources=24, state_binaries=26))
print(json.dumps({'fails': fails, 'checks': out}, indent=1, default=str))
