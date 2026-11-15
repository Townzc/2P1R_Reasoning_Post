"""Owner-approved scheduling reduction; reuse unchanged training and scoring functions."""
from pathlib import Path
import ast, copy, datetime, json, os, subprocess, sys, time, traceback, zipfile
sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import ROOT, PUBLIC, PY, TINKER_PY, ENV, read, sha, lock, publish
sys.path.insert(0, 'reports/p012_20261111/review_46e98da5')
from current_budget import accounting

FOLDER = PUBLIC / 'amendment8_gsm_reduction_v1'
PRIVATE = ROOT / 'gsm_reduction_20261114_v1'
RUNS = ROOT / 'tinker_gsm_runs_v1'
STATE = PRIVATE / 'QUEUE.json'
ORIGINAL = PUBLIC / 'tinker_gsm_training_v1'
AUTHORITY = '5e1f9128180f1dcd222fc1e33fe691ec01030f38'


def category(seed, cell):
    if seed == 29 or cell == 'K4':return 'cancelled'
    if seed == 17 and cell == 'K8':return 'conditional'
    if seed == 17 and cell in ('L', 'P', 'R'):return 'retained'
    raise ValueError((seed, cell))


def qualifies(p_correct, r_correct, questions=1319):
    return 100 * (p_correct - r_correct) >= 3 * questions


def reconcile(event=None):
    policy = read(FOLDER / 'POLICY.json')
    gates = read(FOLDER / 'K8_GATES.json')['models'] if (FOLDER / 'K8_GATES.json').exists() else {}
    admission = read(ORIGINAL / 'ADMISSION.json')
    with lock('BUDGET_ADMISSION.lock'):
        pointer_path = ROOT / 'amendment6_v1/ORIGINAL_T_LEDGER_CURRENT.json'
        before_pointer = read(pointer_path); before = accounting()
        components = []
        for row in read(PUBLIC / 'tinker_gsm_pre_admission_v1/ADMISSION.json')['endpoints']:
            d = ROOT / 'tinker_formal_v1' / row['run_id']
            assert read(d / 'result/COMPLETE.json')['success']
            components.append({'run_id': d.name, 'kind': 'pretraining', 'usd': read(d / 'result/USAGE.json')['upper_token_cost_usd'],
                'complete': True, 'usage_sha256': sha(d / 'result/USAGE.json')})
        cancellation_release = 0
        for name in admission['runs']:
            tr = RUNS / name; r = read(tr / 'request.json')
            mode = category(r['seed'], r['cell'])
            gate = gates.get(r['model'])
            omitted = mode == 'cancelled' or (mode == 'conditional' and gate is not None and not gate['eligible'])
            ev = tr.with_name(name.replace(f'_s{r["seed"]}_', f'_s{r["seed"]}_greedy_'))
            for d, kind in [(tr, 'training'), (ev, 'evaluation')]:
                reserved = r['forecast']['training_buffered_usd' if kind == 'training' else 'reserved_greedy_usd']
                done = (d / 'result/COMPLETE.json').exists()
                if omitted:
                    assert not (d / 'run.log').exists() and not (d / 'result').exists(), 'Never cancel a started call'
                    usd = 0; cancellation_release += reserved
                elif done:
                    assert read(d / 'result/COMPLETE.json')['success']
                    usd = read(d / 'result/USAGE.json')['upper_token_cost_usd'] + (.1 if kind == 'training' else 0)
                else:usd = reserved
                components.append({'run_id': d.name, 'kind': kind, 'category': mode, 'omitted': omitted,
                    'complete': done, 'usd': usd, 'original_reservation_usd': reserved,
                    'usage_sha256': sha(d / 'result/USAGE.json') if done else None})
        gsm = sum(x['usd'] for x in components)
        original_t = admission['original_T_excluding_GSM_usd'] + gsm
        combined = before['combined_reserved_usd'] - before['original_T_accounted_and_reserved_usd'] + original_t
        assert gsm <= 105 and original_t <= 340 and combined <= 485
        folder = FOLDER / 'ledgers'; folder.mkdir(exist_ok=True)
        path = folder / f'{len(list(folder.glob("*.json")))+1:04d}.json'
        row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'authority_commit': AUTHORITY,
            'policy_sha256': sha(FOLDER / 'POLICY.json'), 'components': components,
            'GSM_accounted_and_reserved_usd': gsm, 'combined_reserved_usd': original_t,
            'value_field_scope': 'original T only', 'all_tracks_accounted_and_reserved_usd': combined,
            'original_T_excluding_GSM_usd': admission['original_T_excluding_GSM_usd'],
            'paid_storage_reserved_usd_already_in_base': 30,
            'cumulative_cancelled_call_reservations_released_usd': cancellation_release,
            'previous_original_T_ledger': before_pointer,
            'net_original_T_reduction_since_previous_ledger_usd': before['original_T_accounted_and_reserved_usd']-original_t,
            'conditional_pending_reservations_retained': not bool(gates)}
        with path.open('x') as f:json.dump(row, f, indent=2); f.write('\n')
        commit = publish([path], 'P012 A8: reconcile reduced GSM queue and release omitted reservations')
        tmp = pointer_path.with_suffix('.tmp')
        tmp.write_text(json.dumps({'path': str(path), 'sha256': sha(path), 'value_field': 'combined_reserved_usd'}, indent=2)+'\n')
        tmp.replace(pointer_path)
    if event:event('budget_reconciled', commit=commit, GSM_usd=gsm, original_T_usd=original_t,
        all_tracks_usd=combined, cumulative_released_usd=cancellation_release)
    return row


def reused_functions(path, names, namespace):
    tree = ast.parse(path.read_text())
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    assert {node.name for node in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


def main():
    assert not STATE.exists(), 'No automatic replay'
    policy = read(FOLDER / 'POLICY.json'); assert policy['authority_commit'] == AUTHORITY
    assert read(ROOT / 't_gsm_v1/TRAINING_QUEUE.json')['status'] == 'superseded_by_amendment8'
    state = {'status': 'running', 'controller_pid': os.getpid(), 'authority_commit': AUTHORITY,
        'policy_sha256': sha(FOLDER / 'POLICY.json'), 'events': [], 'automatic_retry': False}
    children = {}
    def event(stage, **kwargs):
        row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'stage': stage, **kwargs}
        state['events'].append(row); tmp=STATE.with_suffix('.tmp')
        tmp.write_text(json.dumps(state,indent=2)+'\n'); tmp.replace(STATE); print(json.dumps(row),flush=True)
    frozen = policy['reused_source_hashes']
    for f,h in frozen.items():assert sha(f) == h
    ns = dict(globals(), PUB=ORIGINAL, frozen=frozen, children=children, event=event)
    reused_functions(ORIGINAL / 'continue.py', ['write','check_sources','start','finish'], ns)
    anno = dict(globals(), POLICY=PUBLIC/'review_46e98da5/T_GSM_INTERPRETATION.json', event=event)
    reused_functions(PUBLIC/'review_46e98da5/annotate_4b_gsm.py', ['annotate'], anno)
    done = set(policy['completed_before_decision'])
    def finish_group(names):
        deadline=time.monotonic()+8*3600
        while True:
            for name,proc in children.items():assert proc.poll() in (None,0), 'Failed; no automatic replay: '+name
            for name in names:
                if name in done:continue
                tr=RUNS/name; req=read(tr/'request.json'); ev=tr.with_name(name.replace('_s17_','_s17_greedy_'))
                for d in (tr,ev):assert not (d/'result/PARTIAL_USAGE.json').exists(), 'Call failed: '+d.name
                if ns['finish'](name):
                    if req['model']=='Qwen/Qwen3.5-4B':assert anno['annotate'](name)
                    done.add(name); event('published',run_id=name)
            if all(n in done for n in names):return
            assert time.monotonic()<deadline, 'Finite batch deadline; model calls preserved'
            time.sleep(10)
    try:
        event('adopted_existing_queue', completed_before_decision=sorted(done), adopted_running_calls=policy['running_calls_at_suspension'])
        finish_group(policy['retained_L_and_P'])
        reconcile(event)
        for name in policy['retained_R']:
            ns['start'](RUNS/name, ORIGINAL/'requests'/(name+'.json'))
        finish_group(policy['retained_R'])
        gates={}
        for name in policy['conditional_K8']:
            req=read(RUNS/name/'request.json'); model=req['model']
            matches=[n for n in policy['retained_L_and_P'] if read(RUNS/n/'request.json')['model']==model and read(RUNS/n/'request.json')['cell']=='P']
            assert len(matches)==1
            pp=PUBLIC/matches[0].replace('_20261114','')/'RESULTS.json'
            rr=PUBLIC/name.replace('_k8_','_r_').replace('_20261114','')/'RESULTS.json'
            p,r=read(pp),read(rr)
            assert p['model']==r['model']==model and p['seed']==r['seed']==17
            assert p['GSM8K']['responses']==r['GSM8K']['responses']==1319
            pc,rc=p['GSM8K']['correct'],r['GSM8K']['correct']
            gates[model]={'P_correct':pc,'R_correct':rc,'questions':1319,'P_minus_R_pp':100*(pc-rc)/1319,
                'eligible':qualifies(pc,rc), 'candidate_run':name,
                'P':{'path':str(pp),'sha256':sha(pp)},'R':{'path':str(rr),'sha256':sha(rr)}}
        gate_path=FOLDER/'K8_GATES.json'
        ns['write'](gate_path,{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'authority_commit':AUTHORITY,'rule':'100*(P_correct-R_correct) >= 3*1319','models':gates,
            'selection_is_outcome_conditional':True,'G1':'not_assessed_K4_cancelled'})
        publish([gate_path], 'P012 A8: record model-specific P minus R gates before any K8 launch')
        reconcile(event)
        selected=[g['candidate_run'] for g in gates.values() if g['eligible']]
        for name in selected:ns['start'](RUNS/name, ORIGINAL/'requests'/(name+'.json'))
        finish_group(selected)
        final_budget=reconcile(event)
        state['status']='complete';event('reduced_GSM_queue_complete',completed=sorted(done),selected_K8=selected)
        ns['write'](FOLDER/'COMPLETION.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'authority_commit':AUTHORITY,'completed_runs':sorted(done),'selected_K8':selected,
            'G1':'not_assessed_K4_cancelled','G2_G3':'remain for independent review per A8',
            'budget':final_budget,'queue_state':state})
        publish([FOLDER/'COMPLETION.json'],'P012 A8: complete owner-reduced GSM queue')
    except BaseException as exc:
        state['status']='stopped_for_inspection';event('stopped',error=str(exc));traceback.print_exc();raise


if __name__ == '__main__':main()
