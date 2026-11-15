"""Bind existing T evidence for review; no model calls, rescoring or statistical fit."""
from pathlib import Path
import datetime
import hashlib
import json
import math
import subprocess
import sys
import zipfile

P = Path('reports/p012_20261111')
L = Path('.local/p012_20261111')
SOURCE = P / 'amendment8_tinker_review_v1'
OUT = P / 'amendment8_T_results_review_v1'
AUTH = '5e1f9128180f1dcd222fc1e33fe691ec01030f38'
REVIEW = 'b24f787a4c92eab9993eb03702df161a6c64c989'
RELEASE = '204ad0ae932f90579cc285ff41483e6b295007a4'
RUNNER = '050a9f43d81c7a610dfc9ca30c901103e145fff28384d2efd1f13247fc60f5ee'
OLD = '61163c22d2e3d37c0bf2592cf7d95ea5569cf2acf6c5cb24606a14ab87bb7696'
NEW = '845af0841bc22aabecf5589b20b7d80d72659aebab622b40832107a5661dec4c'
read = lambda p: json.loads(Path(p).read_text())
digest = lambda b: hashlib.sha256(b).hexdigest()
sha = lambda p: digest(Path(p).read_bytes())
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()


def bind_file(p):
    return {'path': str(p), 'sha256': sha(p)}


def endpoint(name, prediction, event):
    folder = P / (name + '_results')
    result = read(folder / 'RESULTS.json')
    archive = folder / 'evidence.zip'
    for path in [folder / 'RESULTS.json', archive]:
        assert subprocess.check_output(['git', 'hash-object', str(path)]).strip() == subprocess.check_output(['git', 'rev-parse', 'HEAD:' + str(path)]).strip()
    archive_hash = sha(archive)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        roles = {
            'raw': 'evaluation/generation/raw.jsonl', 'labels': 'scores/labels.jsonl',
            'training_request': 'training/REQUEST.json', 'training_loss': 'training/train_loss.jsonl',
            'row_order': 'training/ROW_ORDER.json', 'sampler': 'training/SAMPLER.json',
            'state': 'training/STATE.json', 'server_model': 'training/SERVER_MODEL_INFO.json',
            'training_usage': 'training/USAGE.json', 'evaluation_usage': 'evaluation/USAGE.json',
            'evaluation_request': 'evaluation/REQUEST.json', 'generation_manifest': 'evaluation/generation/MANIFEST.json',
            'generation_complete': 'evaluation/generation/GENERATION_COMPLETE.json',
            'prescore_prediction': 'PREDICTION_BEFORE_SCORE.json', 'termination': 'TERMINATION.json',
        }
        evidence = {role: {'archive': str(archive), 'archive_sha256': archive_hash,
                          'member': member, 'sha256': digest(z.read(member))} for role, member in roles.items()}
        tr = json.loads(z.read(roles['training_request']))
        ev = json.loads(z.read(roles['evaluation_request']))
        assert tr['run_id'] == ev['training_run_id'] == result['run_id'] == name
        assert tr['model'] == ev['model'] == result['model'] == 'Qwen/Qwen3.5-4B'
        assert tr['seed'] == ev['seed'] == result['seed'] == 17 and tr['rank'] == ev['rank'] == 32
        assert tr['source_sha256'] == ev['source_sha256'] == RUNNER
        assert tr['cell'] == result['cell'] and tr['dose'] == result['dose']
        assert tr['accepted_review_commit'] == ev['accepted_review_commit'] == REVIEW
        assert tr['A_result_release_commit'] == ev['A_result_release_commit'] == RELEASE
        assert tr['prediction_commit'] == ev['prediction_commit'] == AUTH
        assert tr['execution_training_config_sha256'] == (NEW if name.startswith('a8_t02_') else OLD)
        if name.startswith('a8_t02_'):
            assert tr['code_commit'] == read(P / 'amendment8_T_admission_v1/T02_PATCH_RECEIPT.json')['source_commit']
        assert json.loads(z.read('training/COMPLETE.json'))['success']
        assert json.loads(z.read('evaluation/COMPLETE.json'))['success']
        server = json.loads(z.read(roles['server_model']))
        assert server['is_lora'] and server['lora_rank'] == 32
        assert server['model_data']['model_name'] == tr['model']
        order = json.loads(z.read(roles['row_order']))
        losses = [json.loads(x) for x in z.read(roles['training_loss']).splitlines()]
        dose = tr['dose']; steps = dose['expected_updates']; rows = dose['distinct_rows']
        assert [dose[k] for k in ('parents', 'paths_per_parent', 'epochs')] == prediction['cell']
        assert rows == dose['parents'] * dose['paths_per_parent']
        assert steps == prediction['steps'] == rows * dose['epochs'] // 8
        assert [x['step'] for x in losses] == list(range(1, steps + 1))
        assert [i for x in losses for i in x['row_indices']] == order
        assert all(len(x['row_indices']) == 8 for x in losses)
        assert len(order) == dose['presentations'] == rows * dose['epochs']
        assert digest(json.dumps(order).encode()) == tr['cpu_counts']['order_sha256']
        for epoch in range(dose['epochs']):
            assert sorted(order[epoch * rows:(epoch + 1) * rows]) == list(range(rows))
        for i, row in enumerate(losses):
            expected = tr['learning_rate'] * (1 + math.cos(math.pi * i / steps)) / 2
            assert math.isclose(row['learning_rate'], expected, rel_tol=1e-12, abs_tol=1e-15)
        assert json.loads(z.read(roles['training_usage']))['training_input_tokens'] == tr['cpu_counts']['training_input_tokens']
        sampler = json.loads(z.read(roles['sampler']))
        state = json.loads(z.read(roles['state']))
        assert sampler['path'] == ev['sampler_path']
        assert sampler['path'].split('/')[2] == state['path'].split('/')[2]
        te = ev['training_evidence']; assert te == result['training_evidence']
        for key, role in [('train_loss_sha256', 'training_loss'), ('row_order_sha256', 'row_order'),
                          ('sampler_manifest_sha256', 'sampler'), ('state_manifest_sha256', 'state')]:
            assert te[key] == evidence[role]['sha256']
        request = L / 'amendment8_tinker_runs_v1' / name / 'request.json'
        assert te['request_sha256'] == sha(request) and read(request) == tr
        generation = json.loads(z.read(roles['generation_manifest']))
        conf = generation['config']
        assert (conf['n'], conf['temperature'], conf['max_tokens'], conf['max_model_len']) == (1, 0, 4096, 8192)
        raw = [json.loads(x) for x in z.read(roles['raw']).splitlines()]
        labels = [json.loads(x) for x in z.read(roles['labels']).splitlines()]
        assert len(raw) == len(labels) == len({x['id'] for x in raw}) == 5000
        assert {(x['id'], x['draw']) for x in raw} == {(x['id'], x['draw']) for x in labels}
        assert {x['draw'] for x in raw} == {0}
        assert evidence['raw']['sha256'] == result['raw_sha256']
        assert evidence['labels']['sha256'] == result['labels_sha256']
        assert sum(x['correct'] for x in labels) == result['MATH']['correct']
        assert result['MATH']['accuracy'] == result['MATH']['correct'] / 5000
        assert result['MATH'] == json.loads(z.read(roles['termination']))['all']
        complete = json.loads(z.read(roles['generation_complete']))
        assert complete['draws'] == 5000 and complete['raw_sha256'] == result['raw_sha256']
        assert result['training_usage'] == json.loads(z.read(roles['training_usage']))
        assert result['evaluation_usage'] == json.loads(z.read(roles['evaluation_usage']))
        prescore = json.loads(z.read(roles['prescore_prediction']))
        assert prescore == result['prediction_before_score'] and prescore['prediction'] == prediction
        assert prescore['prediction_commit'] == AUTH and prescore['raw_sha256'] == result['raw_sha256']
        assert datetime.datetime.fromisoformat(prescore['utc']).tzinfo is not None
        assert prescore['utc'] < event['utc']
    source_archive = SOURCE / 'candidate_datasets.zip'
    inputs = {}
    with zipfile.ZipFile(source_archive) as z:
        for role, member, expected in [
            ('training', 'candidate/' + Path(tr['dataset']['path']).name, tr['dataset']['sha256']),
            ('evaluation', 'evaluation/math5000.jsonl', ev['evaluation']['sha256']),
        ]:
            data = z.read(member); assert digest(data) == expected
            inputs[role] = {'archive': str(source_archive), 'archive_sha256': sha(source_archive), 'member': member, 'sha256': expected}
            if role == 'training':
                assert len(data.splitlines()) == rows and expected == result['dataset_sha256']
            else:
                assert {json.loads(x)['id'] for x in data.splitlines()} == {x['id'] for x in raw}
                assert generation['input_sha256'] == expected
    return {'run_id': name, 'result': bind_file(folder / 'RESULTS.json'), 'public_evidence': evidence,
            'frozen_inputs': inputs, 'dose': dose, 'metrics': result['MATH'], 'prediction': prescore,
            'source_result_commit': event['commit'], 'exploratory': True, 'excluded_from_H0_H3': True,
            'independent_result_audit': 'pending', 'training_order_and_cosine_verified': True}


def main():
    queue = read(L / 'amendment8_tinker_v1/QUEUE.json')
    arms = read(P / 'amendment8_T_admission_v1/ADMISSION.json')['arms']
    names = [a['run_id'] for a in arms]; assert len(names) == 4
    published = {e['run_id']: e for e in queue['events'] if e['stage'] == 'result_published'}
    predictions = read(SOURCE / 'A8_PREDICTIONS.json')['tinker_4b_math']['rows']
    if '--check-published' in sys.argv:
        rows = [endpoint(n, predictions[i], published[n]) for i, n in enumerate(names) if n in published]
        print(json.dumps({'utc': utc(), 'verified_completed_endpoints': len(rows), 'outputs': len(rows) * 5000,
                          'queue_status': queue['status'], 'full_packet_created': False}))
        return
    assert queue['status'] == 'complete' and set(published) == set(names), 'Wait for all four original T endpoints'
    assert not OUT.exists(), 'Preserve frozen packet'
    rows = [endpoint(n, predictions[i], published[n]) for i, n in enumerate(names)]
    receipt = P / 'amendment8_T_admission_v1/T02_PATCH_RECEIPT.json'
    assert read(receipt)['after_sha256'] == NEW and read(receipt)['all_modal_calls_complete']
    OUT.mkdir()
    def write(name, value):
        (OUT / name).write_text(json.dumps(value, indent=2) + '\n')
    write('ENDPOINTS.json', {'utc': utc(), 'authority_commit': AUTH, 'accepted_source_review_commit': REVIEW,
                            'A_result_release_commit': RELEASE, 'endpoint_count': 4, 'outputs': 20000,
                            'endpoints': rows, 'T02_R1': bind_file(receipt), 'T02_R1_audit': 'e84611a756c67fab41095db0e632cb48593dca86',
                            'new_model_calls_or_rescoring': 0, 'new_bootstrap_runs': 0})
    for name in ['A8_PREDICTIONS.json', 'P012_PLAN_v1_AMENDMENT_8.md']:
        (OUT / name).write_bytes((SOURCE / name).read_bytes())
    sys.path.insert(0, str(P / 'review_204ad0ae'))
    from current_budget import accounting, enforce
    from a7_ops import lock
    with lock('BUDGET_ADMISSION.lock'):
        budget = accounting(); enforce(budget); write('BUDGET_SNAPSHOT.json', budget)
    table = []
    for i, r in enumerate(rows):
        m = r['metrics']; d = r['dose']; pred = r['prediction']['prediction']
        table.append(f"| T{i+1:02d} | {d['parents']},{d['paths_per_parent']},{d['epochs']} | {d['expected_updates']} | {m['correct']}/5000 | {100*m['accuracy']:.2f}% | {pred['pred']:.2f}% | {100*m['length_cap_rate']:.2f}% | {m['loop_count']} | {m['normally_terminated_correct']}/{m['normally_terminated_count']} |")
    (OUT / 'README.md').write_text('# A8 T group: four complete MATH endpoints\n\n'
        'All four original Qwen3.5-4B LoRA rank32 seed17 endpoints completed, with20,000 raw outputs. Exploratory, outsideH0–H3. Source/data acceptedb24f787a; A release204ad0ae; frozen predictions5e1f9128.\n\n'
        '| Cell | P,K,E | Updates | Correct | Accuracy | Frozen prediction | Capped | Loops | Normal correct/n |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---:|\n' + '\n'.join(table) + '\n\n'
        'ENDPOINTS.json binds all training steps, complete epoch permutations, cosine learning rates, model/rank, frozen inputs, sampler/state, generation settings, raw outputs and unchanged labels. Timestamped predictions bind the original raw hashes before scoring. T02 used the exact reviewed patch after C05 completion; e84611a7 already accepted that timing.\n\n'
        'Please independently score the four endpoints and apply frozen A8 §5 and SL-8: MATH hit threshold2.5pp, group hit rate and mean residual, K>1 comparison with both fixed alternatives, and E=2 versus E!=2 subsets. A/B/C and reduced GSM results are already audited and are reference-only. No refit, new bootstrap or label change was introduced. Retain all A8 checkpoints. No additional experiment is authorized.\n')
    (OUT / 'build_packet.py').write_bytes(Path(__file__).read_bytes())
    print(OUT)


if __name__ == '__main__':
    main()
