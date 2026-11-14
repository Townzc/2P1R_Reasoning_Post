"""Finite original T-GSM queue. All model, scoring and termination code is unchanged."""
from pathlib import Path
import copy, datetime, json, os, subprocess, sys, time, traceback, zipfile

sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import ROOT, PUBLIC, PY, TINKER_PY, ENV, read, sha, lock, publish, accounting

PUB = PUBLIC / 'tinker_gsm_training_v1'
RUNS = ROOT / 'tinker_gsm_runs_v1'
STATE = ROOT / 't_gsm_v1/TRAINING_QUEUE.json'
assert not STATE.exists()
admission = read(PUB / 'ADMISSION.json')
state = {'status': 'running', 'controller_pid': os.getpid(), 'events': [], 'automatic_retry': False}
children = {}
frozen = {str(p): sha(p) for p in [Path('experiments/p012/tinker_lora.py'),
    Path('experiments/p012/scoring.py'), Path('experiments/p012/termination_summary.py'),
    ROOT / 'amendment5_v1/score_endpoint.py']}


def write(p, value):
    with p.open('x') as f:
        json.dump(value, f, indent=2); f.write('\n')


def event(stage, **kwargs):
    item = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'stage': stage, **kwargs}
    state['events'].append(item)
    tmp = STATE.with_suffix('.tmp'); tmp.write_text(json.dumps(state, indent=2) + '\n'); tmp.replace(STATE)
    print(json.dumps(item), flush=True)


def check_sources():
    for path, digest in frozen.items():
        assert sha(path) == digest, path


def refresh_budget():
    with lock('BUDGET_ADMISSION.lock'):
        components = []
        for row in read(PUBLIC / 'tinker_gsm_pre_admission_v1/ADMISSION.json')['endpoints']:
            d = ROOT / 'tinker_formal_v1' / row['run_id']
            done = (d / 'result/COMPLETE.json').exists()
            usd = read(d / 'result/USAGE.json')['upper_token_cost_usd'] if done else row['forecast_usd']
            components.append({'run_id': d.name, 'kind': 'pretraining', 'complete': done, 'usd': usd})
        for name in admission['runs']:
            tr = RUNS / name; r = read(tr / 'request.json')
            ev = tr.with_name(name.replace(f'_s{r["seed"]}_', f'_s{r["seed"]}_greedy_'))
            for d, kind in [(tr, 'training'), (ev, 'evaluation')]:
                done = (d / 'result/COMPLETE.json').exists()
                if done:
                    assert read(d / 'result/COMPLETE.json')['success']
                    usd = read(d / 'result/USAGE.json')['upper_token_cost_usd'] + (0.1 if kind == 'training' else 0)
                else:
                    usd = r['forecast']['training_buffered_usd' if kind == 'training' else 'reserved_greedy_usd']
                components.append({'run_id': d.name, 'kind': kind, 'complete': done, 'usd': usd,
                    'usage_sha256': sha(d / 'result/USAGE.json') if done else None})
        gsm = sum(x['usd'] for x in components)
        original = admission['original_T_excluding_GSM_usd'] + gsm
        previous = accounting()
        combined = previous['combined_reserved_usd'] - previous['original_T_accounted_and_reserved_usd'] + original
        assert gsm <= 105 and original <= 340 and combined <= 485, ('Budget stop', gsm, original, combined)
        folder = PUB / 'ledgers'; folder.mkdir(exist_ok=True)
        target = folder / f'{len(list(folder.glob("*.json"))) + 1:04d}.json'
        write(target, {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'components': components,
            'GSM_accounted_and_reserved_usd': gsm, 'original_T_excluding_GSM_usd': admission['original_T_excluding_GSM_usd'],
            'paid_storage_reserved_usd_already_in_base': 30, 'combined_reserved_usd': original,
            'value_field_scope': 'original T only', 'all_tracks_accounted_and_reserved_usd': combined})
        pointer = ROOT / 'amendment6_v1/ORIGINAL_T_LEDGER_CURRENT.json'
        pointer.write_text(json.dumps({'path': str(target), 'sha256': sha(target), 'value_field': 'combined_reserved_usd'}, indent=2) + '\n')
    commit = publish([target], 'P012: reconcile original T-GSM reservations and paid storage')
    event('budget_reconciled', GSM_usd=gsm, original_T_usd=original, all_tracks_usd=combined, commit=commit)


def start(d, public_request):
    check_sources()
    r = read(d / 'request.json')
    assert r['forecast']['admitted'] and r['source_sha256'] == frozen['experiments/p012/tinker_lora.py']
    assert r['prediction_commit'] == '8bbf06a7ef19f56ace1b23dde4607b02bc10b389'
    assert sha(r['forecast']['admission_file']) == r['forecast']['admission_sha256']
    assert (d / 'request.json').read_bytes() == subprocess.check_output(['git', 'show', 'HEAD:' + str(public_request)])
    assert not (d / 'result').exists() and not (d / 'run.log').exists(), 'Refuse replay'
    with (d / 'run.log').open('x') as log:
        proc = subprocess.Popen([TINKER_PY, str(ROOT / 'amendment4_v1/launch_tinker_private.py'), str(d)],
            env=ENV, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    children[d.name] = proc
    event('launched', run_id=d.name, pid=proc.pid)


def finish(name):
    tr = RUNS / name; r = read(tr / 'request.json')
    if not (tr / 'result/COMPLETE.json').exists():
        return False
    assert read(tr / 'result/COMPLETE.json')['success']
    ev = tr.with_name(name.replace(f'_s{r["seed"]}_', f'_s{r["seed"]}_greedy_'))
    out = PUBLIC / name.replace('_20261114', '')
    if out.exists():
        return True
    check_sources()
    if not (ev / 'request.json').exists():
        result = tr / 'result'
        losses = [json.loads(x) for x in (result / 'train_loss.jsonl').open()]
        assert [x['step'] for x in losses] == list(range(1, r['dose']['expected_updates'] + 1))
        assert [i for x in losses for i in x['row_indices']] == read(result / 'ROW_ORDER.json')
        assert read(result / 'USAGE.json')['training_input_tokens'] == r['cpu_counts']['full_training_input_tokens']
        sampler = read(result / 'SAMPLER.json'); training_state = read(result / 'STATE.json')
        assert sampler['path'].split('/')[2] == training_state['path'].split('/')[2]
        inp = PUBLIC / 'tinker_gsm_preparation_v1/inputs/gsm8k1319.jsonl'
        e = copy.deepcopy(r)
        e.update(run_id=ev.name, mode='generate', n=1, sampler_path=sampler['path'],
            evaluation={'path': str(inp), 'sha256': sha(inp), 'task': 'gsm8k'},
            code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip())
        e['training_evidence'] = {'run_id': name, 'cell': r['cell'], 'seed': r['seed'], 'model': r['model'],
            'dataset_sha256': r['dataset']['sha256'], 'updates': len(losses), 'request_sha256': sha(tr / 'request.json'),
            'train_loss_sha256': sha(result / 'train_loss.jsonl'), 'row_order_sha256': sha(result / 'ROW_ORDER.json'),
            'sampler_manifest_sha256': sha(result / 'SAMPLER.json'), 'state_manifest_sha256': sha(result / 'STATE.json')}
        for k in ['dataset', 'dose', 'cell']:
            e.pop(k)
        ev.mkdir(exist_ok=False); write(ev / 'request.json', e)
        folder = PUB / 'evaluation_requests'; folder.mkdir(exist_ok=True)
        target = folder / (ev.name + '.json'); write(target, e)
        commit = publish([target], 'P012: bind reserved GSM greedy evaluation ' + name)
        event('evaluation_prepared', run_id=ev.name, commit=commit)
        start(ev, target)
    if not (ev / 'result/COMPLETE.json').exists():
        return False
    assert read(ev / 'result/COMPLETE.json')['success']
    assert read(ev / 'result/generation/GENERATION_COMPLETE.json')['draws'] == 1319
    write(ev / 'PREDICTION_BEFORE_SCORE.json', {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'prediction_commit': r['prediction_commit'], 'raw_sha256': sha(ev / 'result/generation/raw.jsonl')})
    subprocess.run([PY, str(ROOT / 'amendment5_v1/score_endpoint.py'), str(ev.relative_to(ROOT))], env=ENV, check=True)
    termination = read(ev / 'TERMINATION.json')['all']
    out.mkdir(exist_ok=False)
    row = {'run_id': name, 'model': r['model'], 'task': 'gsm8k', 'track': 'tinker_lora',
        'cell': r['cell'], 'seed': r['seed'], 'exploratory': True, 'excluded_from_H0_H3': True,
        'dose': r['dose'], 'dataset_sha256': r['dataset']['sha256'], 'GSM8K': termination,
        'training_evidence': read(ev / 'request.json')['training_evidence'],
        'training_usage': read(tr / 'result/USAGE.json'), 'evaluation_usage': read(ev / 'result/USAGE.json'),
        'prediction_before_score': read(ev / 'PREDICTION_BEFORE_SCORE.json'),
        'raw_sha256': sha(ev / 'result/generation/raw.jsonl'), 'labels_sha256': sha(ev / 'score_v1/labels.jsonl'),
        'independent_result_audit': 'pending'}
    write(out / 'RESULTS.json', row)
    with zipfile.ZipFile(out / 'evidence.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for folder, prefix in [(tr / 'result', 'training'), (ev / 'result', 'evaluation'), (ev / 'score_v1', 'scores')]:
            for f in folder.rglob('*'):
                if f.is_file():
                    assert b'/Users/' not in f.read_bytes()
                    archive.write(f, prefix + '/' + str(f.relative_to(folder)))
        for f in ['TERMINATION.json', 'PREDICTION_BEFORE_SCORE.json']:
            archive.write(ev / f, f)
    (out / 'README.md').write_text('# Tinker / LoRA GSM8K result\n\n' +
        f'{r["model"]}, {r["cell"]}, seed {r["seed"]}: {termination["correct"]}/1319. '
        'Accuracy, truncation, loops and normal-termination denominators are in RESULTS.json. '
        'Exploratory; excluded from H0–H3. Independent result audit pending.\n')
    commit = publish([out], 'P012: publish original T-GSM result ' + name)
    event('published', run_id=name, commit=commit)
    return True


try:
    assert read(PUBLIC / 'review_2edeee51/PAID_STORAGE_VERIFIED.json')['effective_rate_usd_per_gigabyte_month'] > 0
    event('waiting_for_three_reserved_NLL')
    deadline = time.monotonic() + 8 * 3600
    while read(ROOT / 't_gsm_v1/NLL_QUEUE_after_storage.json')['status'] != 'complete':
        assert read(ROOT / 't_gsm_v1/NLL_QUEUE_after_storage.json')['status'] == 'running'
        assert time.monotonic() < deadline
        time.sleep(10)
    for seed in [17, 29]:
        for cell in (['L', 'P', 'R', 'K8', 'K4'] if seed == 17 else ['L', 'P', 'R', 'K8']):
            group = [name for name in admission['runs'] if read(RUNS / name / 'request.json')['seed'] == seed
                     and read(RUNS / name / 'request.json')['cell'] == cell]
            assert len(group) == 3
            refresh_budget()
            for name in group:
                start(RUNS / name, PUB / 'requests' / (name + '.json'))
            deadline = time.monotonic() + 8 * 3600
            while True:
                for name, proc in children.items():
                    assert proc.poll() in (None, 0), name + ': failed; no automatic replay'
                done = [finish(name) for name in group]
                if all(done):
                    break
                assert time.monotonic() < deadline, 'Finite batch deadline; calls are preserved'
                time.sleep(10)
    refresh_budget()
    state['status'] = 'complete'; event('all_27_original_GSM_cells_complete')
except BaseException as exc:
    state['status'] = 'stopped_for_inspection'; event('stopped', error=str(exc))
    traceback.print_exc()
    raise
