"""CPU-only T-group data/render/request checks. Never creates a Tinker client."""
from pathlib import Path
import collections, copy, datetime, difflib, hashlib, importlib.util, json, subprocess, sys, zipfile
sys.dont_write_bytecode = True
sys.path.insert(0, '.')
from experiments.p012 import training_config as live
from experiments.p012.tinker_lora import load_renderer, rendered_datum, epoch_order, cosine_lr

ROOT = Path('.local/p012_20261111')
OUT = Path('reports/p012_20261111/amendment8_tinker_review_v1')
AUTH = '5e1f9128180f1dcd222fc1e33fe691ec01030f38'
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest = lambda b: hashlib.sha256(b).hexdigest()
write = lambda p, x: Path(p).write_text(json.dumps(x, indent=2) + '\n')
utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
source = Path('experiments/p012/training_config.py')
original = source.read_text()
assert sha(source) == '61163c22d2e3d37c0bf2592cf7d95ea5569cf2acf6c5cb24606a14ab87bb7696'
addition = '\n# A8 conditional Tinker T group; activation requires Claude A-group verdict.\nCELLS.update({"A8_P1024_K2_E4": (1024, 2, 4)})\n'
candidate_text = original.replace('\n\ndef training_config', addition+'\n\ndef training_config', 1)
candidate = OUT/'candidate/training_config.py'; candidate.write_text(candidate_text)
(OUT/'training_config.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), candidate_text.splitlines(True),
    fromfile='a/experiments/p012/training_config.py', tofile='b/experiments/p012/training_config.py', n=0)))
spec = importlib.util.spec_from_file_location('a8_t_candidate', candidate)
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
regression = []
for cell in [None, *live.CELLS]:
    for family in ['qwen', 'llama3']:
        args = ('frozen/model', 'a'*40, family, 'data', 'inputs', 'outputs')
        assert live.training_config(*args, cell=cell) == cfg.training_config(*args, cell=cell)
        if cell: assert live.grid_dose(cell) == cfg.grid_dose(cell)
        regression.append({'cell':cell, 'family':family, 'unchanged':True})
for name in ['P012_PLAN_v1_AMENDMENT_8.md','A8_PREDICTIONS.json']:
    (OUT/name).write_bytes(subprocess.check_output(['git','show',AUTH+':audit/claude/20261114e/'+name]))
pred = read(OUT/'A8_PREDICTIONS.json')['tinker_4b_math']
frozen = ROOT/'c6_frozen_v1/math'
order = read(frozen/'PARENT_ORDER.json')['training4096']
selected = collections.defaultdict(list)
for line in (frozen/'selected8.jsonl').open():
    row=json.loads(line);selected[row['parent_id']].append(row)
assert len(order)==4096 and len(set(order))==4096 and all(len(selected[p])==8 for p in order)
data = lambda p,k:[row for parent in order[:p] for row in selected[parent][:k]]
encode = lambda rows:''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows).encode()
nesting=[]
for cell in ['L','K4','K8','P','R']:
    p,k,_=live.CELLS[cell];assert encode(data(p,k))==(frozen/(cell+'.jsonl')).read_bytes()
    nesting.append({'cell':cell,'sha256':sha(frozen/(cell+'.jsonl')),'byte_identical':True})
base = read(ROOT/'tinker_formal_v1/tinker_lora_qwen3_5_4b_math_p_s17_20261113_v1/request.json')
tokenizer, renderer = load_renderer(base)
counts={};samples=[]
for index,row in enumerate(data(4096,2)):
    datum, ev=rendered_datum(row,tokenizer,renderer)
    key=(row['parent_id'],row['solution_hash']);assert key not in counts
    counts[key]={'parent_id':key[0],'solution_hash':key[1],'input_tokens':datum.model_input.length,
                 'target_tokens':ev['target_tokens'],'full_tokens':len(ev['input_token_ids'])}
    if index<3:samples.append(dict(row,**ev))
    if index%1024==0:print('CPU rendered',index,flush=True)
assert len(counts)==8192
write(OUT/'RENDER_SAMPLES.json',samples)
(OUT/'ROW_TOKEN_COUNTS.jsonl').write_bytes(encode(list(counts.values())))
usage_refs=[]
for cell in ['l','p','r','k8','k4']:
    path=ROOT/f'tinker_formal_v1/tinker_lora_qwen3_5_4b_math_{cell}_s17_greedy_20261113_v1/result/USAGE.json'
    usage=read(path);usage_refs.append({'cell':cell,'usage':usage,'sha256':sha(path)})
greedy=max(x['usage']['upper_token_cost_usd'] for x in usage_refs)*1.5
records=[];dataset_meta=[]
private=ROOT/'amendment8_tinker_candidate_v1';private.mkdir(exist_ok=False)
with zipfile.ZipFile(OUT/'candidate_datasets.zip','x',zipfile.ZIP_DEFLATED) as z:
    for name in ['PARENT_ORDER.json','selected8.jsonl','L.jsonl','K4.jsonl','K8.jsonl','P.jsonl','R.jsonl']:
        z.write(frozen/name,'C6/'+name)
    z.write(ROOT/'c6_frozen_v1/MANIFEST.json','C6/MANIFEST.json')
    z.write(ROOT/'main_eval/inputs_v1/math5000.jsonl','evaluation/math5000.jsonl')
    for i, prediction in enumerate(pred['rows'],1):
        p,k,e=prediction['cell'];cell=f'A8_P{p}_K{k}_E{e}';dose=cfg.grid_dose(cell)
        rows=data(p,k);payload=encode(rows);f=private/f'P{p}_K{k}.jsonl';f.write_bytes(payload)
        member=f'candidate/P{p}_K{k}.jsonl';z.writestr(member,payload)
        assert len(rows)==p*k==dose['distinct_rows'] and len({r['parent_id'] for r in rows})==p
        assert dose['expected_updates']==prediction['steps']==p*k*e//8
        token_rows=[counts[(r['parent_id'],r['solution_hash'])] for r in rows]
        tokens=sum(x['input_tokens'] for x in token_rows)*e
        target=sum(x['target_tokens'] for x in token_rows)*e
        all_order=[j for epoch in range(e) for j in epoch_order(len(rows),17,epoch)]
        assert len(all_order)==p*k*e and set(collections.Counter(all_order).values())=={e}
        assert cosine_lr(base['learning_rate'],0,dose['expected_updates'])==base['learning_rate']
        assert cosine_lr(base['learning_rate'],dose['expected_updates'],dose['expected_updates'])==0
        training=tokens*base['prices_per_million']['train']/1e6*1.25+.1
        request=copy.deepcopy(base)
        request.update(run_id=f'a8_t{i:02d}_tinker_lora_4b_math_p{p}_k{k}_e{e}_s17_v1',cell=cell,dose=dose,
            dataset={'path':str(f),'sha256':digest(payload)},code_commit=head,
            source_sha256=sha('experiments/p012/tinker_lora.py'),accepted_review_commit=None,
            original_track_review_commit='8bbf06a7ef19f56ace1b23dde4607b02bc10b389',
            sampling_review_commit='a56115d6ceee49d0bb5495f9be3579e0cace8daa',
            prediction_commit=AUTH,authority_commit=AUTH,track='tinker_lora',exploratory=True,
            excluded_from_H0_H3=True,A8_group='T',candidate_training_config_sha256=sha(candidate),
            authority='Conditional A8 T group: source review and Claude A-group verdict required; CPU preparation only')
        request['forecast']={'admitted':False,'training_buffered_usd':training,'reserved_greedy_usd':greedy,
            'forecast_usd':training+greedy,'A8_cap_usd':40,'combined_T_cap_usd':485,
            'sampling_rule':'maximum same-model main-grid MATH measured token cost x1.5',
            'storage':'Global USD30 reserve remains counted once; training buffer includes0.10 per arm.'}
        request['cpu_counts']={'training_input_tokens':tokens,'supervised_target_tokens':target,
            'max_sequence_tokens':max(x['full_tokens'] for x in token_rows),'all_rows_mask_and_renderer_verified':True,
            'order_sha256':digest(json.dumps(all_order).encode()),'dataset_rows':len(rows)}
        write(OUT/'requests'/(request['run_id']+'.json'),request)
        records.append({'run_id':request['run_id'],'prediction':prediction,'dose':dose,
                        'dataset_sha256':digest(payload),'archive_member':member,
                        'request_sha256':sha(OUT/'requests'/(request['run_id']+'.json')),
                        **request['cpu_counts'],**request['forecast']})
        dataset_meta.append({'P':p,'K':k,'rows':p*k,'sha256':digest(payload),'archive_member':member})
write(OUT/'CANDIDATE_MANIFEST.json',{'utc':utc,'authority_commit':AUTH,'base_commit':head,
    'base_training_config_sha256':sha(source),'candidate_training_config_sha256':sha(candidate),
    'runner_source_sha256':sha('experiments/p012/tinker_lora.py'),'new_tuple':[1024,2,4],
    'rows':records,'total_forecast_usd':sum(r['forecast_usd'] for r in records),'A8_cap_usd':40,
    'admitted':False,'model_calls':0,'gate':'Source accepted AND Claude A-group verdict >= partially holds AND current budget pass'})
write(OUT/'CPU_CHECKS.json',{'utc':utc,'all_old_config_cases':regression,'original_C6_cells':nesting,
    'new_datasets':dataset_meta,'unique_real_rows_rendered':len(counts),'all_rows_le_4096':True,
    'tokenizer_revision':base['asset']['revision'],'rank':base['rank'],'learning_rate':base['learning_rate'],
    'C6_parent_order_sha256':sha(frozen/'PARENT_ORDER.json'),'C6_selected8_sha256':sha(frozen/'selected8.jsonl'),
    'archive_sha256':sha(OUT/'candidate_datasets.zip'),'live_training_config_unchanged':sha(source)==digest(original.encode())})
write(OUT/'MEASURED_SAMPLING_COSTS.json',{'references':usage_refs,'reserved_per_arm_usd':greedy})
print('prepared',len(records),'arms; forecast',sum(r['forecast_usd'] for r in records),'no model calls',flush=True)
