"""A9 evidence adapter accepted at f1ee77b7 with R-1 and R-2 applied.

Imports the accepted bootstrap core unchanged. No model calls or rescoring.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, '.')
from analysis.p012_registered import bound_file, bootstrap_delta, differences, outcomes, two_seed_contrast, POLICY

AUTHORITY = 'ecda09143c135a64512fec346fe13d38002c7951'
ACCEPTED_REVIEW = 'f1ee77b77b8a29d9a6dd47efadf46eb1987e7b8d'
CATALOG_SHA = '623bb25809b133a1fc1f5dea591d622b22545d10b57164bba66cf1af1743f9ca'
PRED_SHA = 'fa3d186069b672c683f6300c174597124af8f970201aacf8bf050b9e57cac3b2'
CORE_SHA = 'b6973ad67c8eff3cec08806a553754911113944a044c9248bdb45aa1ac8d0b06'
CATALOG_PATH = Path('reports/p012_20261111/amendment9_analysis_review_v1/CATALOG.json')
PRED_PATH = Path('audit/claude/20261120a/A9_PREDICTIONS.json')
RUNS_DIR = Path('reports/p012_20261111/amendment9_analysis_runs_v1')
MODEL_KEYS = ('llama_base_gsm8k', 'llama_instruct_gsm8k', 'qwen_instruct_gsm8k', 'qwen_base_gsm8k')
INPUT_SHA = {'gsm8k':'5a9a4e2cae969a72cf7a71f6ce66059039c0f9e694ef689ab7d5fc86080f3176',
             'math':'19019b07cca9bedc519149cef9fad8765cc40cb0fc1129b28485dab0d750848d'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_training(training, expected):
    e = expected
    tinker = e['platform'] == 'tinker'
    model = training['model'] if tinker else training['model']['repo']
    revision = training['asset']['revision'] if tinker else training['model']['revision']
    seed = training['seed'] if tinker else training['config']['seed']
    require((training['run_id'], model, revision, training['cell'], seed) ==
            (e['training_run_id'], e['model'], e['revision'], e['cell'], e['seed']),
            'Training run, model, initialization, cell or seed changed')
    dose = training['dose']
    require((dose['parents'], dose['paths_per_parent'], dose['epochs'], dose['expected_updates'],
             dose['distinct_rows'], dose['effective_batch']) ==
            (e['P'], e['K'], e['E'], e['updates'], e['P']*e['K'], 8), 'Training dose changed')
    require(e['updates'] == e['P']*e['K']*e['E']//8, 'Catalog update dose invalid')
    require(dose['presentations']==e['P']*e['K']*e['E'], 'Training presentations changed')
    require(training['dataset']['sha256'] == e['dataset_sha256'], 'Frozen training data changed')
    if not tinker:
        cfg = training['config']
        require(cfg['data_seed'] == e['seed'] and cfg['num_train_epochs'] == e['E'] and
                cfg['per_device_train_batch_size']*cfg['gradient_accumulation_steps'] == 8 and
                cfg['lr_scheduler_type'] == 'cosine' and cfg['learning_rate'] == 1e-5 and
                cfg['finetuning_type'] == 'full', 'Training recipe changed')
    else:
        require(training['mode'] == 'train' and training['rank'] == 32 and
                training['learning_rate'] == 0.0004905250962784578 and
                training['source_sha256']=='050a9f43d81c7a610dfc9ca30c901103e145fff28384d2efd1f13247fc60f5ee',
                'Tinker LoRA recipe changed')


def read_endpoint(spec, expected):
    # Every used file is hash-bound; declared expected identity comes from the
    # separately frozen44-entry catalog, not mutable labels or caller metadata.
    paths = {k: bound_file(v) for k, v in spec['files'].items()}
    get = lambda k: json.loads(paths[k].read_text())
    training = get('training_manifest')
    validate_training(training, expected)
    generation = get('generation_manifest'); cfg = generation['config']
    require((cfg['protocol'], cfg['task'], cfg['n'], cfg['temperature'], cfg['max_tokens'], cfg['max_model_len']) ==
            ('omi2', expected['task'], 1, 0, 4096, 8192), 'Evaluation protocol changed')
    if expected['platform'] == 'modal':
        require(cfg['template_family'] == ('llama3' if expected['model'].startswith('meta-llama/') else 'qwen'),
                'Evaluation template family changed')
        verify = generation['checkpoint_verification']; checkpoint = spec['files']['checkpoint_manifest']['sha256']
        require(cfg['training_run_id'] == verify['training_run_id'] == expected['training_run_id'] and
                cfg['model'] == '/p012/training/'+expected['training_run_id']+'/checkpoint' and
                cfg['revision'] == expected['revision'] and
                cfg['checkpoint_manifest_sha256'] == verify['checkpoint_manifest_sha256'] == checkpoint and
                verify['training_manifest_sha256'] == spec['files']['training_manifest']['sha256'] and
                verify['initialization_repo'] == expected['model'], 'Checkpoint or training manifest cross-wired')
        require(get('trainer_state')['global_step'] == expected['updates'], 'Incomplete training updates')
        examples = [int(n.replace(',', '')) for n in re.findall(r'Num examples\s*=\s*([\d,]+)', paths['training_log'].read_text())]
        require(bool(examples) and set(examples) == {expected['P']*expected['K']}, 'Training sample dose changed')
        require(get('training_status')['success'] and get('evaluation_status')['success'], 'Incomplete Modal endpoint')
    else:
        ev = get('evaluation_request'); binding = ev['training_evidence']
        require(ev['model'] == expected['model'] and ev['seed'] == expected['seed'] == cfg['seed'] and
                ev['asset']['revision'] == expected['revision'] and
                generation['renderer'] == 'qwen3_5_disable_thinking', 'Tinker model, seed or renderer changed')
        require((binding['run_id'],binding['cell'],binding['seed'],binding['model'],binding['dataset_sha256'],binding['updates']) ==
                (expected['training_run_id'],expected['cell'],expected['seed'],expected['model'],expected['dataset_sha256'],expected['updates']),
                'Tinker evaluation training identity changed')
        for field, member in [('request_sha256','training_manifest'),('train_loss_sha256','train_loss'),
                              ('row_order_sha256','row_order'),('sampler_manifest_sha256','sampler'),('state_manifest_sha256','state')]:
            require(binding[field] == spec['files'][member]['sha256'], 'Tinker evidence cross-wired: '+field)
        require(ev['sampler_path'] == get('sampler')['path'], 'Tinker sampler changed')
        losses=[json.loads(x) for x in paths['train_loss'].read_text().splitlines()]
        order=get('row_order');n=expected['P']*expected['K']
        require([x['step'] for x in losses] == list(range(1,expected['updates']+1)), 'Incomplete Tinker updates')
        require([i for x in losses for i in x['row_indices']] == order and
                all(sorted(order[j*n:(j+1)*n])==list(range(n)) for j in range(expected['E'])), 'Tinker row order changed')
        require(get('training_status')['success'] and get('evaluation_status')['success'], 'Incomplete Tinker endpoint')
    inputs=[json.loads(x) for x in paths['inputs'].read_text().splitlines()]
    require(len(inputs)==expected['count'] and generation['input_sha256']==spec['files']['inputs']['sha256']==
            INPUT_SHA[expected['task']], 'Question set changed')
    labels=[json.loads(x) for x in paths['labels'].read_text().splitlines()]
    values=outcomes(labels,[x['id'] for x in inputs])
    term=get('termination');stats=term['all']
    require((term['raw_sha256'],term['labels_sha256']) ==
            (spec['files']['raw']['sha256'],spec['files']['labels']['sha256']), 'Raw or label binding changed')
    require(stats['responses']==expected['count'] and stats['correct']==sum(values.values()) and
            stats['accuracy']==sum(values.values())/expected['count'], 'Published accuracy disagrees with labels')
    if stats['length_cap_rate']>.2:
        diag=get('first_boxed_diagnostic')
        require(diag['raw_sha256']==spec['files']['raw']['sha256'] and diag['diagnostic_only'], 'Missing first-box diagnostic')
    return values


def replication(seed17_accuracy, seed29_accuracy, frozen):
    a = seed17_accuracy-frozen['a8_prediction']; b = seed29_accuracy-frozen['a8_prediction']
    same = b*frozen['seed17_residual']>0
    outside = abs(b)>frozen['band_pp']
    return {'seed17_accuracy_pct':seed17_accuracy,'seed29_accuracy_pct':seed29_accuracy,
            'a8_prediction_pct':frozen['a8_prediction'],'seed17_residual_pp':a,'seed29_residual_pp':b,
            'mean_residual_pp':(a+b)/2,'same_sign':same,'outside_band':outside,
            'miss_replicates':same and outside,
            'interpretation':'repeated_miss' if same and outside else 'same_direction_within_band' if same else 'seed_variation'}


def unit_keys(catalog):
    units = {f'R{i:02d}': {f'R{i:02d}:{seed}' for seed in (17, 29)} for i in range(1, 7)}
    units.update({'M:'+setting: {f'M:{setting}:{arm}:{seed}'
                  for arm in ('P', 'PK2', 'K4', 'K8') for seed in (17, 29)} for setting in MODEL_KEYS})
    require(set().union(*units.values()) == set(catalog), 'Unit catalog does not cover exactly44 endpoints')
    return units


def select_units(manifest, catalog, consumed):
    units = manifest.get('units')
    require(isinstance(units, list) and bool(units), 'Require nonempty analysis units')
    require(len(units) == len(set(units)), 'Duplicate unit in this run')
    mapping = unit_keys(catalog)
    require(set(units) <= set(mapping), 'Unknown analysis unit')
    require(not set(units) & set(consumed), 'Unit already analyzed in a formal run')
    expected = set().union(*(mapping[u] for u in units))
    require(set(manifest['endpoints']) == expected, 'Endpoints must exactly match complete selected units')
    return units


def prior_results(manifest):
    specs = manifest.get('prior_results', [])
    paths = [Path(x['path']) for x in specs]
    require(len(paths) == len(set(paths)), 'Duplicate prior result')
    require(set(paths) == set(RUNS_DIR.glob('*/RESULTS.json')), 'Missing or unregistered prior result')
    R, M, consumed = {}, {}, set()
    for spec in specs:
        prior = json.loads(bound_file(spec).read_text())
        require((prior['authority_commit'], prior['accepted_analysis_review_commit'], prior['catalog_sha256'],
                 prior['prediction_sha256'], prior['bootstrap_core_sha256']) ==
                (AUTHORITY, ACCEPTED_REVIEW, CATALOG_SHA, PRED_SHA, CORE_SHA), 'Prior analysis identity changed')
        units = prior['units']
        require(len(units) == len(set(units)) and not set(units) & consumed, 'Duplicate previously analyzed unit')
        require(set(units) == set(prior['R']) | {'M:'+x for x in prior['M']}, 'Prior unit/output mismatch')
        consumed.update(units); R.update(prior['R']); M.update(prior['M'])
    return R, M, consumed


def aggregate(R, M):
    missing = {}
    def decide(name, required, available, fn):
        absent = sorted(set(required)-set(available)); missing[name] = absent
        return None if absent else bool(fn())
    all_m = {'M:'+s for s in MODEL_KEYS}; available_m = {'M:'+s for s in M}
    single = ['R01', 'R02', 'R03', 'R04']
    result = {
        'single_epoch_all_same_sign': decide('single_epoch_all_same_sign', single, R,
            lambda: all(R[x]['same_sign'] for x in single)),
        'single_epoch_at_least3_misses_repeat': decide('single_epoch_at_least3_misses_repeat', single, R,
            lambda: sum(R[x]['miss_replicates'] for x in single)>=3),
        'interaction_failure_trigger': decide('interaction_failure_trigger', ['R05', 'R06'], R,
            lambda: all(R[x]['same_sign'] and R[x]['mean_residual_pp']>=3 for x in ['R05', 'R06'])),
        'M_predictions': {
            'M-1': decide('M-1', all_m, available_m, lambda: all(not x['PK2_minus_P']['noticeable'] for x in M.values())),
            'M-2': decide('M-2', all_m, available_m, lambda: all(-4.5<=x['K4_minus_P']['seed_mean']['delta_pp']<=.5 for x in M.values())),
            'M-3': decide('M-3', ['M:qwen_base_gsm8k'], available_m,
                lambda: all(67.2<=v<=72.2 for v in M['qwen_base_gsm8k']['accuracy_pct_by_seed']['PK2'].values())),
            'M-4': decide('M-4', all_m, available_m, lambda: sum(x['PK2_gt_K4_gt_K8'] for x in M.values())>=3)}}
    return dict(result, missing_units=missing)


def analyze(manifest):
    require(ACCEPTED_REVIEW is not None and re.fullmatch('[a-f0-9]{40}',ACCEPTED_REVIEW) is not None and
            manifest.get('accepted_analysis_review_commit')==ACCEPTED_REVIEW, 'A9 analysis awaits accepted review')
    require(sha('analysis/p012_registered.py')==CORE_SHA, 'Bootstrap core changed')
    require(sha(CATALOG_PATH)==CATALOG_SHA and manifest['catalog_sha256']==CATALOG_SHA, 'Frozen catalog changed')
    require(manifest['authority_commit']==AUTHORITY and manifest['prediction_sha256']==sha(PRED_PATH)==PRED_SHA, 'Prediction binding changed')
    catalog=json.loads(CATALOG_PATH.read_text());pred=json.loads(PRED_PATH.read_text())
    previous_R, previous_M, consumed = prior_results(manifest)
    units = select_units(manifest, catalog, consumed)
    data={key:read_endpoint(spec,catalog[key]) for key,spec in manifest['endpoints'].items()}
    accuracy=lambda values:100*sum(values.values())/len(values)
    R={}
    for frozen in pred['part_R_seed29_of_missed_cells']:
        if frozen['id'] not in units:
            continue
        ident=frozen['id'];low=data[ident+':17'];high=data[ident+':29']
        require(abs(round(accuracy(low),2)-frozen['seed17_measured'])<.005,'A8 reference accuracy changed')
        R[ident]={**replication(accuracy(low),accuracy(high),frozen),
                  'seed29_minus_seed17':bootstrap_delta(differences(high,low))}
    M={}
    for setting in MODEL_KEYS:
        if 'M:'+setting not in units:
            continue
        arms={arm:{str(seed):data[f'M:{setting}:{arm}:{seed}'] for seed in [17,29]} for arm in ['P','PK2','K4','K8']}
        means={arm:sum(accuracy(v) for v in seeds.values())/2 for arm,seeds in arms.items()}
        M[setting]={'accuracy_pct_by_seed':{arm:{s:accuracy(v) for s,v in seeds.items()} for arm,seeds in arms.items()},
            'two_seed_mean_accuracy_pct':means,'PK2_minus_P':two_seed_contrast(arms['PK2'],arms['P']),
            'K4_minus_P':two_seed_contrast(arms['K4'],arms['P']),
            'K8_minus_P':two_seed_contrast(arms['K8'],arms['P']),
            'PK2_gt_K4_gt_K8':means['PK2']>means['K4']>means['K8']}
    return {'authority_commit':AUTHORITY,'accepted_analysis_review_commit':ACCEPTED_REVIEW,
            'input_manifest_sha256':manifest['_file_sha256'],'catalog_sha256':CATALOG_SHA,'bootstrap_core_sha256':CORE_SHA,
            'prediction_sha256':PRED_SHA,'units':units,'prior_results':manifest.get('prior_results',[]),
            'available_units':sorted(consumed | set(units)), 'policy':POLICY,'R':R,'M':M,
            **aggregate({**previous_R, **R}, {**previous_M, **M}),
            'predictor_refit_performed':False,'exploratory':True,'excluded_from_H0_H3':True,
            'independent_numeric_audit':'pending',
            'M1_limitation':'No noticeable difference does not establish equivalence; intervals condition on observed training seeds.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    require(not args.output.is_absolute() and args.output.parent.parent==RUNS_DIR and
            args.output.name=='RESULTS.json', 'Formal output must use the fixed A9 run registry')
    RUNS_DIR.mkdir(exist_ok=True)
    with Path('.local/p012_20261111/amendment9_v1/ANALYSIS_RUN.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        require(not args.output.exists(), 'Formal output already exists')
        manifest=json.loads(args.manifest.read_text());manifest['_file_sha256']=sha(args.manifest)
        result=analyze(manifest)
        with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
