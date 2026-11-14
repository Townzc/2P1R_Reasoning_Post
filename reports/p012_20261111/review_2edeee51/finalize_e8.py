"""Bind the approved export receipt into the existing E8 evidence and eval request."""
from pathlib import Path
import copy, datetime, json, shutil, subprocess, sys

sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import ROOT, PUBLIC, read, sha, lock
from experiments.p012.tinker_export_recovery import validate_training

plan = read(PUBLIC / 'review_2edeee51/PLAN.json')
recovery = Path(plan['output'])
receipt = read(recovery / 'COMPLETE.json')
assert receipt['success'] and receipt['operation'] == 'export_only'
assert all(receipt[k] == 0 for k in ['new_training_updates', 'new_forward_calls', 'new_sampling_calls'])
for spec in plan['files'].values():
    assert sha(spec['path']) == spec['sha256']
tr = Path(plan['files']['request']['path']).parent
res = tr / 'result'
req = read(tr / 'request.json')
losses = [json.loads(x) for x in (res / 'train_loss.jsonl').open()]
validate_training(req, losses, read(res / 'ROW_ORDER.json'), read(res / 'STATE.json'),
                  read(res / 'PARTIAL_USAGE.json'), plan['expected_state_path'])
assert receipt['source_state_path'] == read(res / 'STATE.json')['path']
assert receipt['original_request_sha256'] == sha(tr / 'request.json')
before = read(recovery / 'WEIGHTS_INFO.json')
after = read(recovery / 'EXPORTED_WEIGHTS_INFO.json')
assert all(before[k] == after[k] for k in ['base_model', 'is_lora', 'lora_rank',
                                         'train_mlp', 'train_attn', 'train_unembed'])
sampler = read(recovery / 'SAMPLER.json')
assert '/sampler_weights/' in sampler['path']


def write(p, value):
    with p.open('x') as f:
        json.dump(value, f, indent=2); f.write('\n')


with lock('BUDGET_ADMISSION.lock'):
    assert not (res / 'COMPLETE.json').exists() and not (res / 'SAMPLER.json').exists()
    shutil.copytree(recovery, res / 'export_recovery')
    shutil.copyfile(recovery / 'SAMPLER.json', res / 'SAMPLER.json')
    usage = read(res / 'PARTIAL_USAGE.json')
    usage.update(upper_token_cost_usd=usage['training_input_tokens'] * req['prices_per_million']['train'] / 1e6,
                 includes_cache_discount=False, storage_not_in_token_cost=True)
    write(res / 'USAGE.json', usage)
    binding = {'accepted_recovery_review_commit': plan['accepted_recovery_review_commit'],
        'source_state_path': receipt['source_state_path'], 'exported_sampler_path': sampler['path'],
        'receipt_sha256': sha(recovery / 'COMPLETE.json'),
        'exported_weights_info_sha256': sha(recovery / 'EXPORTED_WEIGHTS_INFO.json'),
        'preserved_partial_usage_sha256': sha(res / 'PARTIAL_USAGE.json'),
        'new_training_updates': 0, 'training_retry_count': 1, 'export_only_recovery_count': 1,
        'weight_identity_basis': 'Platform restore/export semantics and remote identity, not a weight-byte hash.'}
    write(res / 'EXPORT_RECOVERY_BINDING.json', binding)
    write(res / 'COMPLETE.json', {'success': True, 'smoke_is_not_scientific_result': False,
        'recovered_after_completed_training': True, 'updates': 1024,
        'completed_utc': receipt['finished_utc'], 'export_recovery': binding})

evaluation = copy.deepcopy(req)
inp = ROOT / 'main_eval/inputs_v1/math5000.jsonl'
evaluation.update(run_id=tr.name.replace('_s17_', '_s17_greedy_'), mode='generate', n=1,
    code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    sampler_path=sampler['path'], evaluation={'path': str(inp), 'sha256': sha(inp), 'task': 'math'})
for key in ['dataset', 'dose', 'cell']:
    evaluation.pop(key)
evaluation['forecast'] = {'admitted': True, 'reserved_greedy_usd': req['forecast']['reserved_greedy_usd'],
    'admission_file': req['forecast']['admission_file'], 'admission_sha256': req['forecast']['admission_sha256'],
    'sampling_rule': 'Measured token cost x1.5, already reserved with training'}
evaluation['training_evidence'] = {'run_id': tr.name, 'updates': 1024,
    'train_loss_sha256': sha(res / 'train_loss.jsonl'), 'row_order_sha256': sha(res / 'ROW_ORDER.json'),
    'state_manifest_sha256': sha(res / 'STATE.json'), 'sampler_manifest_sha256': sha(res / 'SAMPLER.json'),
    'input_token_count_verified': True, 'export_recovery': binding,
    'export_recovery_binding_sha256': sha(res / 'EXPORT_RECOVERY_BINDING.json')}
assert evaluation['source_sha256'] == sha('experiments/p012/tinker_lora.py')
assert evaluation['prediction_commit'] == '18f64e2df34944da9b8fc6378609ccbdeed1c587'
out = tr.parent / evaluation['run_id']
out.mkdir(exist_ok=False)
write(out / 'request.json', evaluation)
write(PUBLIC / 'tinker_lora_post_requests_v2' / (out.name + '.json'), evaluation)
for spec in plan['files'].values():
    assert sha(spec['path']) == spec['sha256'], 'Original failed evidence changed'
print(out, flush=True)
