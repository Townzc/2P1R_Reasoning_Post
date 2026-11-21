"""Prepare non-executable A10 requests after S1; no model or account calls."""
import copy
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent.relative_to(Path.cwd())
LOCAL = Path('.local/p012_20261111/amendment10_v1')
AUTHORITY = 'f42dcd1595807406f67ff694e5235447c6814ebc'
LENGTH_REVIEW = 'f0369f2590dfd4f70dab909c81a9d386bde672ae'
CAP_AUTHORITY = 'c9a534808e65ec648da1995ba26ee52929509de9'
CELL_NAMES = {'L':'L', 'P':'P', 'R':'R', 'S2':'A8_P2048_K2_E2',
              'S4':'K4', 'K4s':'A8_P512_K4_E2', 'R8':'A10_R8'}
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    state = read(LOCAL/'RECOVERY_QUEUE.json')
    assert state['status'] == 'generation_complete_data_and_training_review_required'
    assert state['active_batch'] is None
    data = read(HERE/'DATA_MANIFEST.json')
    evaluation = read(HERE/'EVALUATION_MANIFEST.json')
    generation = read('reports/p012_20261111/amendment10_s1_v1/MANIFEST.json')
    assert data['length_review_commit'] == LENGTH_REVIEW
    assert data['training_max_length'] == 8192
    assert data['authority_commit'] == AUTHORITY
    assert sha(evaluation['private_input_path']) == evaluation['private_input_sha256']
    spec = importlib.util.spec_from_file_location('a10_review_config', HERE/'candidate/training_config.py')
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    source_sha = sha(HERE/'candidate/tinker_lora.py')
    config_sha = sha(HERE/'candidate/training_config.py')
    templates = []
    training_estimates = []
    student = generation['student']
    student_eval = next(x for x in evaluation['baseline_forecasts'] if x['model'] == student['model'])['prediction_usd']
    evidence = {'path':evaluation['private_input_path'], 'sha256':evaluation['private_input_sha256'], 'task':'logiqa'}
    base = {'task':'logiqa', 'authority_commit':AUTHORITY, 'prediction_commit':AUTHORITY,
        'length_review_commit':LENGTH_REVIEW, 'cap_authority_commit':CAP_AUTHORITY,
        'source_sha256':source_sha, 'execution_training_config_sha256':config_sha,
        'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'accepted_review_commit':None, 'review_status':'candidate_only_not_executable',
        'track':'tinker_lora', 'exploratory':True, 'excluded_from_H0_H3':True,
        'rank':32, 'sampling_concurrency':32, 'training_max_length':8192,
        'cookbook_commit':'8486b8df2fc32e9713cf96dd5f75d43c7ef70a17'}
    for model in [generation['student'], generation['teacher']]:
        req=copy.deepcopy(base)
        size='4b' if model['model'].endswith('-4B') else '9b'
        forecast=next(x for x in evaluation['baseline_forecasts'] if x['model']==model['model'])['prediction_usd']
        req.update(run_id=f'a10_logiqa_{size}_baseline4096_s17_v1', mode='generate', seed=17,
            model=model['model'], asset=model['asset'], learning_rate=model['learning_rate'],
            prices_per_million=model['prices_per_million'], evaluation=evidence, n=1,
            forecast={'admitted':False, 'forecast_usd':forecast, 'subcap_usd':6, 'overall_cap_usd':200,
                'basis':evaluation['forecast_basis']})
        templates.append(req)
    for cell in data['cells']:
        arm=cell['arm']; p,k,e=cell['P'],cell['K'],cell['E']
        dataset=data['datasets'][f'p{p}_k{k}']
        assert sha(dataset['private_path'])==dataset['sha256']==cell['dataset_sha256']
        identities=read(dataset['public_identities'])
        assert sha(dataset['public_identities'])==dataset['public_identities_sha256']
        dose=config.grid_dose(CELL_NAMES[arm])
        assert (dose['parents'],dose['paths_per_parent'],dose['epochs'],dose['expected_updates'])==(p,k,e,cell['updates'])
        assert sum(x['training_input_tokens'] for x in identities)*e==cell['training_input_tokens']
        assert sum(x['supervised_target_tokens'] for x in identities)*e==cell['supervised_tokens']
        training_raw=cell['training_input_tokens']*student['prices_per_million']['train']/1e6
        training_forecast=training_raw*1.5+0.10
        req=copy.deepcopy(base)
        req.update(run_id=f'a10_tinker_lora_4b_logiqa_{arm.lower()}_s{cell["seed"]}_v1',
            mode='train', model=student['model'], asset=student['asset'], seed=cell['seed'],
            learning_rate=student['learning_rate'], prices_per_million=student['prices_per_million'],
            cell=CELL_NAMES[arm], A10_arm=arm, dose=dose,
            dataset={'path':dataset['private_path'], 'sha256':dataset['sha256']},
            cpu_counts={'training_input_tokens':dataset['training_input_tokens_one_epoch'],
                'supervised_target_tokens':dataset['supervised_tokens_one_epoch'],
                'max_sequence_tokens':max(x['full_sequence_tokens'] for x in identities),
                'dataset_rows':len(identities), 'source_identities_sha256':dataset['public_identities_sha256']},
            forecast={'admitted':False, 'training_buffered_usd':training_forecast,
                'reserved_greedy_usd':student_eval, 'forecast_usd':training_forecast+student_eval,
                'subcap_usd':125, 'overall_cap_usd':200,
                'basis':'Exact training-input tokens times published rate times1.5 plus0.10; initial greedy estimate from the adjusted4B pilot; update after baseline and L measurements'})
        templates.append(req)
        training_estimates.append({'arm':arm,'seed':cell['seed'],'training_token_cost_usd':training_raw,
            'training_forecast_usd':training_forecast,'greedy_forecast_usd':student_eval})
    assert len(templates)==14 and len({r['run_id'] for r in templates})==14
    destination=HERE/'request_templates'; destination.mkdir(exist_ok=False)
    for request in templates:
        assert request['accepted_review_commit'] is None and not request['forecast']['admitted']
        write(destination/(request['run_id']+'.json'), request)
    S1=state['successful_attempts_token_cost_usd']+state['failed_attempt_reserve_usd']
    train_eval=sum(x['training_forecast_usd']+x['greedy_forecast_usd'] for x in training_estimates)
    baselines=evaluation['baseline_total_forecast_usd']
    write(HERE/'PROSPECTIVE_BUDGET.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'authority_commit':AUTHORITY,'cap_authority_commit':CAP_AUTHORITY,
        'S1_accounted_and_retained_failed_reserve_usd':S1,'S1_subcap_usd':100,
        'baselines_forecast_usd':baselines,'baselines_subcap_usd':6,
        'training_and_evaluation_forecast_usd':train_eval,'training_and_evaluation_subcap_usd':125,
        'whole_phase_forecast_usd':S1+baselines+train_eval,'overall_hard_cap_usd':200,
        'training_details':training_estimates,'admitted':False,
        'first_L_must_update_forecasts':True,'failed_reserve_release_requires_API_settlement':True,
        'admission_requires_accepted_combined_review_and_live_budget':True,
        'preparation_script_sha256':sha(__file__)})
    print(json.dumps({'request_templates':14,'training_and_evaluation_forecast_usd':train_eval,
        'whole_phase_forecast_usd':S1+baselines+train_eval,'admitted':False}))


if __name__ == '__main__':
    main()
