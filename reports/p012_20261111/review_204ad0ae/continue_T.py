"""Execute only the four accepted A8 requests using unchanged scientific runners."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
import zipfile

sys.path.insert(0, '.')
sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import publish, lock
from current_budget import accounting, enforce

ROOT = Path('.local/p012_20261111')
PUBLIC = Path('reports/p012_20261111')
PUB = PUBLIC / 'amendment8_T_admission_v1'
REVIEW = PUBLIC / 'review_204ad0ae'
SOURCE = PUBLIC / 'amendment8_tinker_review_v1'
RUNS = ROOT / 'amendment8_tinker_runs_v1'
META = ROOT / 'amendment8_tinker_v1'
QUEUE = META / 'QUEUE.json'
CONFIG = Path('experiments/p012/training_config.py')
OLD = '61163c22d2e3d37c0bf2592cf7d95ea5569cf2acf6c5cb24606a14ab87bb7696'
NEW = '845af0841bc22aabecf5589b20b7d80d72659aebab622b40832107a5661dec4c'
ACCEPTED = 'b24f787a4c92eab9993eb03702df161a6c64c989'
RELEASE = '204ad0ae932f90579cc285ff41483e6b295007a4'
PRED = '5e1f9128180f1dcd222fc1e33fe691ec01030f38'
PY = str(ROOT / 'venv/bin/python')
TPY = str(ROOT / 'tinker_venv312/bin/python')
ENV = dict(os.environ, PYTHONPATH='.')
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, value):
    Path(p).write_text(json.dumps(value, indent=2) + '\n')


def storage_check():
    import tinker
    from experiments.p012.tinker_export_recovery import storage_receipt
    os.environ['TINKER_API_KEY'] = (ROOT / 'credentials/tinker_api_key').read_text().strip()
    usage = tinker.AdminClient().get_current_checkpoint_storage_usage().result().model_dump(mode='json')
    receipt = storage_receipt(usage, True)
    assert receipt['admitted'], 'Storage API guard failed; no settings mutation or model call'
    return receipt


def main():
    assert not QUEUE.exists(), 'Refuse a second controller'
    admission = read(PUB / 'ADMISSION.json')
    assert admission['A_result_release_commit'] == RELEASE
    assert admission['accepted_source_review_commit'] == ACCEPTED
    names = [row['run_id'] for row in admission['arms']]
    assert len(names) == 4
    t02 = next(n for n in names if n.startswith('a8_t02_'))
    source_files = [Path('experiments/p012/tinker_lora.py'), Path('experiments/p012/scoring.py'),
                    Path('experiments/p012/termination_summary.py'), ROOT / 'amendment5_v1/score_endpoint.py']
    frozen = {str(p): sha(p) for p in source_files}
    state = {'utc': utc(), 'status': 'running', 'controller_pid': os.getpid(),
             'accepted_source_review_commit': ACCEPTED, 'A_result_release_commit': RELEASE,
             'prediction_commit': PRED, 'automatic_retries': False, 'events': []}
    children = {}

    def event(stage, **fields):
        item = {'utc': utc(), 'stage': stage, **fields}
        state['events'].append(item)
        tmp = QUEUE.with_suffix('.tmp'); write(tmp, state); tmp.replace(QUEUE)
        print(json.dumps(item), flush=True)

    def check_sources():
        for p, h in frozen.items():
            assert sha(p) == h, 'Scientific source changed: ' + p

    def budget_snapshot(stage):
        with lock('BUDGET_ADMISSION.lock'):
            snapshot = accounting(); enforce(snapshot)
            folder = PUB / 'ledgers'; folder.mkdir(exist_ok=True)
            p = folder / f'{len(list(folder.glob("*.json")))+1:04d}.json'
            assert not p.exists()
            write(p, {'utc': utc(), 'stage': stage, **snapshot})
            commit = publish([p], 'P012 A8 T: reconcile reserved and actual costs ' + stage)
        event('budget_reconciled', commit=commit, A8_usd=snapshot['A8_accounted_and_reserved_usd'],
              combined_usd=snapshot['combined_reserved_usd'])

    def start(d, public_request):
        check_sources()
        request = read(d / 'request.json')
        assert request['accepted_review_commit'] == ACCEPTED and request['prediction_commit'] == PRED
        assert request['forecast']['admitted']
        assert sha(request['forecast']['admission_file']) == request['forecast']['admission_sha256']
        assert (d / 'request.json').read_bytes() == subprocess.check_output(['git', 'show', 'HEAD:' + str(public_request)])
        if request['mode'] == 'train':
            assert sha(CONFIG) == request['execution_training_config_sha256']
        assert not (d / 'run.log').exists() and not (d / 'result').exists(), 'Never replay a model call'
        budget_snapshot('before_' + d.name)
        if request['mode'] == 'train':
            receipt = storage_check()
            write(d / 'STORAGE_BEFORE_TRAINING.json', receipt)
            target = PUB / 'storage_checks' / (d.name + '.json')
            target.parent.mkdir(exist_ok=True); write(target, receipt)
            publish([target], 'P012 A8 T: record actual storage API guard before ' + d.name)
        with (d / 'run.log').open('x') as log:
            child = subprocess.Popen([TPY, str(ROOT / 'amendment4_v1/launch_tinker_private.py'), str(d)],
                env=ENV, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        children[d.name] = child
        event('launched', run_id=d.name, pid=child.pid, request_sha256=sha(d / 'request.json'),
              actual_training_config_sha256=sha(CONFIG))

    def apply_T02_when_BC_complete():
        if (RUNS / t02 / 'run.log').exists():
            return
        bc = read(ROOT / 'amendment8_v1/BC_QUEUE.json')
        if bc['status'] != 'BC_complete_T_waits_Claude_A_verdict':
            assert bc['status'] == 'running', 'B/C stopped; inspect before changing shared source'
            return
        apps = json.loads(subprocess.check_output([str(ROOT.parent / 'midpoint_20261011/venv/bin/modal'),
            'app', 'list', '--json'], env=dict(os.environ, MODAL_PROFILE='tangzhice'), text=True))
        if any(a['state'] != 'stopped' for a in apps):
            return  # A completed local call may briefly remain active in the control plane.
        assert sha(CONFIG) == OLD
        candidate = SOURCE / 'candidate/training_config.py'
        assert sha(candidate) == NEW
        temporary = CONFIG.with_suffix('.a8.tmp'); temporary.write_bytes(candidate.read_bytes()); temporary.replace(CONFIG)
        commit = publish([CONFIG], 'P012 A8 T: apply b24f787a one-tuple patch after all B/C calls complete')
        request = read(PUB / 'requests' / (t02 + '.json'))
        request.update(code_commit=commit, execution_training_config_sha256=NEW)
        d = RUNS / t02; write(d / 'request.json', request)
        public_request = PUB / 'requests' / (t02 + '.json'); write(public_request, request)
        proof = PUB / 'T02_PATCH_RECEIPT.json'
        write(proof, {'utc': utc(), 'accepted_review_commit': ACCEPTED, 'source_commit': commit,
            'before_sha256': OLD, 'after_sha256': NEW, 'BC_status': bc['status'],
            'all_modal_calls_complete': True, 'active_modal_apps': [],
            'R1_option': 'Wait until all22 Modal cells complete, then apply accepted candidate'})
        publish([public_request, proof], 'P012 A8 T: bind T02 to accepted patch and completed Modal queue')
        event('T02_patch_applied', source_commit=commit, before_sha256=OLD, after_sha256=NEW)
        start(d, public_request)

    def finish(name):
        tr = RUNS / name; request = read(tr / 'request.json')
        if not (tr / 'result/COMPLETE.json').exists():
            return False
        assert read(tr / 'result/COMPLETE.json')['success']
        ev = tr.with_name(name.replace('_s17_', '_s17_greedy_'))
        output = PUBLIC / (name + '_results')
        if (output / 'RESULTS.json').exists():
            return True
        check_sources()
        if not (ev / 'request.json').exists():
            # Serialize evaluations so each completed cost is reconciled before the next.
            if any(n != ev.name and '_greedy_' in n and proc.poll() is None for n, proc in children.items()):
                return False
            result = tr / 'result'
            losses = [json.loads(x) for x in (result / 'train_loss.jsonl').read_text().splitlines()]
            assert [r['step'] for r in losses] == list(range(1, request['dose']['expected_updates'] + 1))
            order = read(result / 'ROW_ORDER.json')
            assert [i for r in losses for i in r['row_indices']] == order
            assert hashlib.sha256(json.dumps(order).encode()).hexdigest() == request['cpu_counts']['order_sha256']
            n = request['dose']['distinct_rows']
            assert len(order) == n * request['dose']['epochs']
            for e in range(request['dose']['epochs']):
                assert sorted(order[e*n:(e+1)*n]) == list(range(n))
            assert read(result / 'USAGE.json')['training_input_tokens'] == request['cpu_counts']['training_input_tokens']
            sampler = read(result / 'SAMPLER.json'); saved = read(result / 'STATE.json')
            assert sampler['path'].split('/')[2] == saved['path'].split('/')[2]
            evaluated = read(SOURCE / 'evaluation_templates' / (ev.name + '.json'))
            evaluated.update(accepted_review_commit=ACCEPTED, A_result_release_commit=RELEASE,
                code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                sampler_path=sampler['path'], execution_training_config_sha256=sha(CONFIG),
                authority='Owner-approved A8; sourceb24f787a, A verdict/release204ad0ae')
            evaluated['forecast'] = dict(request['forecast'], forecast_usd=request['forecast']['reserved_greedy_usd'])
            evaluated['training_evidence'] = {'run_id': name, 'cell': request['cell'], 'seed': 17,
                'model': request['model'], 'dataset_sha256': request['dataset']['sha256'],
                'updates': len(losses), 'request_sha256': sha(tr / 'request.json'),
                'train_loss_sha256': sha(result / 'train_loss.jsonl'), 'row_order_sha256': sha(result / 'ROW_ORDER.json'),
                'sampler_manifest_sha256': sha(result / 'SAMPLER.json'), 'state_manifest_sha256': sha(result / 'STATE.json'),
                'each_epoch_complete_permutation': True}
            ev.mkdir(exist_ok=False); write(ev / 'request.json', evaluated)
            target = PUB / 'evaluation_requests' / (ev.name + '.json'); target.parent.mkdir(exist_ok=True)
            write(target, evaluated); publish([target], 'P012 A8 T: bind reserved greedy sampler ' + name)
            start(ev, target)
        if not (ev / 'result/COMPLETE.json').exists():
            return False
        assert read(ev / 'result/COMPLETE.json')['success']
        assert read(ev / 'result/generation/GENERATION_COMPLETE.json')['draws'] == 5000
        prediction = {'utc': utc(), 'prediction_commit': PRED, 'accepted_source_review_commit': ACCEPTED,
            'A_result_release_commit': RELEASE, 'raw_sha256': sha(ev / 'result/generation/raw.jsonl'),
            'prediction': request['prediction_binding'], 'training_run_id': name}
        write(ev / 'PREDICTION_BEFORE_SCORE.json', prediction)
        target = PUB / 'predictions_before_score' / (name + '.json'); target.parent.mkdir(exist_ok=True)
        write(target, prediction); publish([target], 'P012 A8 T: record timestamped frozen prediction before scoring ' + name)
        subprocess.run([PY, str(ROOT / 'amendment5_v1/score_endpoint.py'), str(ev.relative_to(ROOT))], env=ENV, check=True)
        term = read(ev / 'TERMINATION.json')['all']
        output.mkdir(exist_ok=False)
        write(output / 'RESULTS.json', {'run_id': name, 'model': request['model'], 'task': 'math',
            'track': 'Tinker_LoRA_A8_exploratory', 'cell': request['cell'], 'seed': 17, 'dose': request['dose'],
            'exploratory': True, 'excluded_from_H0_H3': True, 'MATH': term,
            'dataset_sha256': request['dataset']['sha256'], 'prediction_before_score': prediction,
            'training_evidence': read(ev / 'request.json')['training_evidence'],
            'training_usage': read(tr / 'result/USAGE.json'), 'evaluation_usage': read(ev / 'result/USAGE.json'),
            'accepted_source_review_commit': ACCEPTED, 'A_result_release_commit': RELEASE,
            'raw_sha256': prediction['raw_sha256'], 'labels_sha256': sha(ev / 'score_v1/labels.jsonl'),
            'independent_result_audit': 'pending'})
        with zipfile.ZipFile(output / 'evidence.zip', 'x', zipfile.ZIP_DEFLATED) as z:
            for folder, prefix in [(tr / 'result', 'training'), (ev / 'result', 'evaluation'), (ev / 'score_v1', 'scores')]:
                for f in folder.rglob('*'):
                    if f.is_file():
                        assert b'/Users/' not in f.read_bytes()
                        z.write(f, prefix + '/' + str(f.relative_to(folder)))
            z.write(ev / 'TERMINATION.json', 'TERMINATION.json')
            z.write(ev / 'PREDICTION_BEFORE_SCORE.json', 'PREDICTION_BEFORE_SCORE.json')
        commit = publish([output], 'P012 A8 T: publish full MATH output and training evidence ' + name)
        event('result_published', run_id=name, commit=commit, accuracy=term['accuracy'])
        budget_snapshot('after_' + name)
        return True

    try:
        event('accepted_four_arm_scope', run_ids=names, R1_policy='T01/T03/T04 now; T02 after B/C completes')
        for name in names:
            if name != t02:
                start(RUNS / name, PUB / 'requests' / (name + '.json'))
        deadline = time.monotonic() + 12 * 3600
        done = set()
        while len(done) < 4:
            assert time.monotonic() < deadline, 'Finite controller deadline; preserve running calls for inspection'
            for name, child in children.items():
                assert child.poll() in (None, 0), 'Failed call; no automatic retry: ' + name
                assert not (RUNS / name / 'result/PARTIAL_USAGE.json').exists(), 'Partial call: ' + name
            apply_T02_when_BC_complete()
            for name in names:
                if name not in done and finish(name):
                    done.add(name)
            time.sleep(10)
        state['status'] = 'complete'; event('all_four_T_endpoints_complete', endpoints=4)
    except BaseException as exc:
        state['status'] = 'stopped_for_inspection'; event('stopped', error=str(exc))
        traceback.print_exc(); raise


if __name__ == '__main__':
    main()
