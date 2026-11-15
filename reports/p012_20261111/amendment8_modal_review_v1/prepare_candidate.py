"""CPU-only A8 candidate data/config and measured-cost review preparation."""
from pathlib import Path
import collections, copy, datetime, difflib, hashlib, importlib.util, json, math, re, statistics, subprocess, sys, zipfile
sys.dont_write_bytecode = True
sys.path.insert(0, '.')
ROOT=Path('.local/p012_20261111'); PUBLIC=Path('reports/p012_20261111')
OUT=PUBLIC/'amendment8_modal_review_v1'; OUT.mkdir(exist_ok=False)
(OUT/'candidate').mkdir()
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest=lambda b:hashlib.sha256(b).hexdigest()
write=lambda p,d:Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
AUTHORITY='5e1f9128180f1dcd222fc1e33fe691ec01030f38'
UTC=datetime.datetime.now(datetime.timezone.utc).isoformat()
for f in ['P012_PLAN_v1_AMENDMENT_8.md','A8_PREDICTIONS.json']:
    (OUT/f).write_bytes(subprocess.check_output(['git','show',AUTHORITY+':audit/claude/20261114e/'+f]))
pred=read(OUT/'A8_PREDICTIONS.json')
groups={'A':('llama_base_gsm8k','tier1_llama_v1','llama_base','llama3'),
        'B':('llama_instruct_gsm8k','tier1_llama_v1','llama_instruct','llama3'),
        'C':('qwen_instruct_gsm8k','tier1_gsm_v1','qwen_instruct','qwen')}
triples=sorted({tuple(x['cell']) for key,_,_,_ in groups.values() for x in pred[key]['rows']})
cellname=lambda t:'A8_P%d_K%d_E%d'%tuple(t)
base_path=Path('experiments/p012/training_config.py'); original_source=base_path.read_text()
addition='\n# A8 exploratory Modal parameter tuples; Tinker T group remains gated.\nCELLS.update({\n'+''.join(f'    "{cellname(t)}": {t},\n' for t in triples)+'})\n'
candidate_source=original_source.replace('\n\ndef training_config',addition+'\n\ndef training_config',1)
assert candidate_source.count('"max_samples": 10000')==1
candidate_source=candidate_source.replace('"max_samples": 10000','"max_samples": max(10000, CELLS[cell][0] * CELLS[cell][1]) if cell else 10000')
candidate=OUT/'candidate/training_config.py';candidate.write_text(candidate_source)
(OUT/'training_config.patch').write_text(''.join(difflib.unified_diff(original_source.splitlines(True),candidate_source.splitlines(True),fromfile='a/experiments/p012/training_config.py',tofile='b/experiments/p012/training_config.py',n=0)))
spec=importlib.util.spec_from_file_location('a8_candidate_training_config',candidate)
cfg=importlib.util.module_from_spec(spec);spec.loader.exec_module(cfg)
from experiments.p012 import training_config as old
regression=[]
for c in [None,*old.CELLS]:
    for family in ['llama3','qwen']:
        args=('fixed/model','a'*40,family,'data','inputs','outputs')
        assert old.training_config(*args,cell=c)==cfg.training_config(*args,cell=c)
        if c:assert old.grid_dose(c)==cfg.grid_dose(c)
        regression.append({'cell':c,'family':family,'unchanged':True})

c6=ROOT/'c6_frozen_v1'; folder=c6/'gsm8k'; order=read(folder/'PARENT_ORDER.json')['training4096']
selected=collections.defaultdict(list)
for line in (folder/'selected8.jsonl').open():
    row=json.loads(line);selected[row['parent_id']].append(row)
assert len(order)==4096 and len(set(order))==4096
for parent in order:assert len(selected[parent])==8
data=lambda p,k:[r for parent in order[:p] for r in selected[parent][:k]]
encode=lambda rows:''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows).encode()
nesting=[]
for c in ['L','P','K4','K8','R']:
    p,k,_=old.CELLS[c];payload=encode(data(p,k));assert payload==(folder/(c+'.jsonl')).read_bytes()
    nesting.append({'cell':c,'rows':p*k,'sha256':digest(payload),'byte_identical':True})
datasets={}
with zipfile.ZipFile(OUT/'candidate_datasets.zip','x',zipfile.ZIP_DEFLATED) as z:
    for source in ['PARENT_ORDER.json','selected8.jsonl','P.jsonl','K4.jsonl','K8.jsonl','L.jsonl','R.jsonl']:
        z.write(folder/source,'C6/'+source)
    z.write(c6/'MANIFEST.json','C6/MANIFEST.json')
    for p,k in sorted({t[:2] for t in triples}):
        rows=data(p,k);payload=encode(rows);member=f'candidate/P{p}_K{k}.jsonl';z.writestr(member,payload)
        assert len(rows)==p*k and len({x['parent_id'] for x in rows})==p
        assert all(v==k for v in collections.Counter(x['parent_id'] for x in rows).values())
        assert len({(x['parent_id'],x['solution_hash']) for x in rows})==p*k
        assert max(max(r['training_tokens'].values()) for r in rows)<=4096
        datasets[p,k]={'archive_member':member,'sha256':digest(payload),'rows':p*k,'parents':p,'paths_per_parent':k,
            'full_tokens_per_epoch':{f:sum(r['training_tokens'][f] for r in rows) for f in ['llama3','qwen']},
            'maximum_full_tokens':{f:max(r['training_tokens'][f] for r in rows) for f in ['llama3','qwen']}}
write(OUT/'DATA_CHECKS.json',{'utc':UTC,'candidate_not_launched':True,'C6_parent_order_sha256':sha(folder/'PARENT_ORDER.json'),
    'C6_selected8_sha256':sha(folder/'selected8.jsonl'),'C6_manifest_sha256':sha(c6/'MANIFEST.json'),
    'original_cells_reconstructed_byte_identically':nesting,'new_unique_datasets':list(datasets.values()),
    'row_identity':'Exact frozen selected8 rows in training4096 order; first K solutions; no resampling or new solutions.',
    'all_token_lengths_from_frozen_C6_common_inventory':True,'dataset_archive_sha256':sha(OUT/'candidate_datasets.zip')})

bills={w:read(ROOT/f'amendment8_v1/{w}_report.json') for w in ['tangzhice','townzc']}
measured=[];used_bills=[]
for group,(key,oldgroup,prefix,family) in groups.items():
    for seed in [17,29]:
        root=ROOT/(oldgroup if seed==17 else 'tier2_v1')
        workspace='townzc' if group=='C' and seed==29 else 'tangzhice'
        for c in (['P','K8','K4','R','L'] if seed==17 else ['P','K8','R','L']):
            name=('tier2_' if seed==29 else '')+f'{prefix}_gsm8k_{c.lower()}_s{seed}_20261113_v1'
            if seed == 29:
                canonical = read(PUBLIC / f'tier2_{prefix}_gsm8k_s29_v1/RESULTS.json')
                name = next(row['training_run_id'] for row in canonical['cells'] if row['cell'] == c)
            tr=root/name;ev=root/name.replace(f'_s{seed}_',f'_s{seed}_greedy_')
            request=read(tr/'request.json');parts={}
            for mode,d in [('training',tr),('evaluation',ev)]:
                ids=set(re.findall(r'ap-[A-Za-z0-9]+',(d/'run.log').read_text(errors='replace')));assert len(ids)==1
                app=ids.pop();rr=[r for r in bills[workspace] if r['object_id']==app];assert rr
                status=read(d/'result/STATUS.json');assert status['success']
                amount=sum(float(r['cost']) for r in rr);used_bills.extend(dict(workspace=workspace,**r) for r in rr)
                parts[mode]={'app_id':app,'billed_usd':amount,'function_seconds':status['function_seconds'],'status_sha256':sha(d/'result/STATUS.json')}
            result=read(tr/'result/checkpoint/train_results.json')
            rows=[json.loads(x) for x in request['dataset']['jsonl'].splitlines()]
            updates=request.get('dose',old.grid_dose(c))['expected_updates']
            measured.append({'group':group,'setting':key,'workspace':workspace,'cell':c,'seed':seed,'run_id':name,
                'updates':updates,'train_runtime_seconds':result['train_runtime'],
                'mean_full_tokens':sum(r['training_tokens'][family] for r in rows)/len(rows),
                'total_billed_usd':parts['training']['billed_usd']+parts['evaluation']['billed_usd'],**parts})
write(OUT/'MEASURED_MAIN_GRID_COSTS.json',{'utc':UTC,'basis':'Closed per-app resource billing; compute only, successful training plus full1319 greedy evaluation. Shared volume charges separate.',
    'rows':measured,'billing_rows':used_bills})

train_rate=4.3952;eval_rate=4.1406
forecasts=[];checks=[]
for group,(key,oldgroup,prefix,family) in groups.items():
    refs=[r for r in measured if r['group']==group]
    # Use both-seed measured step throughput; account separately for setup/billing overhead and dataset size.
    unit=max((r['train_runtime_seconds']/r['updates']/r['mean_full_tokens'] for r in refs if r['cell']!='L'))
    overhead=max(r['training']['billed_usd']-r['train_runtime_seconds']*train_rate/3600 for r in refs)
    eval_bill=max(r['evaluation']['billed_usd'] for r in refs)
    baseline=read(ROOT/oldgroup/(prefix+'_gsm8k_p_s17_20261113_v1/request.json'))
    for index,x in enumerate(pred[key]['rows'],1):
        p,k,e=x['cell'];c=cellname((p,k,e));ds=datasets[p,k]
        steps=p*k*e//8;assert steps==x['steps']
        name=f'a8_{group.lower()}{index:02d}_{prefix}_gsm8k_p{p}_k{k}_e{e}_s17_20261114_v1'
        config=cfg.training_config(baseline['model']['repo'],baseline['model']['revision'],family,
            name,'inputs',f'/p012/training/{name}/checkpoint',seed=17,cell=c)
        dose=cfg.grid_dose(c);assert dose['expected_updates']==steps
        assert config['max_samples']>=p*k and config['num_train_epochs']==e
        assert config['per_device_train_batch_size']*config['gradient_accumulation_steps']==8
        assert config['lr_scheduler_type']=='cosine' and config['learning_rate']==1e-5
        mean_tokens=ds['full_tokens_per_epoch'][family]/ds['rows']
        runtime=unit*mean_tokens*steps
        # Fixed setup overhead is conservatively scaled for inventories larger than the original4096 rows.
        train_cost=(runtime*train_rate/3600+overhead*max(1,ds['rows']/4096))*1.25+30*train_rate/3600+.02
        eval_cost=eval_bill*1.25+30*eval_rate/3600
        forecasts.append({'group':group,'index':index,'run_id':name,'cell':c,'P':p,'K':k,'E':e,'steps':steps,
            'workspace':'tangzhice','GPU':'H100!','seed':17,'exploratory':True,'excluded_from_H0_H3':True,
            'authority_commit':AUTHORITY,'prediction':x,'dataset':ds,'model':baseline['model'],
            'config':config,'dose':dose,'source_candidate_sha256':sha(candidate),'admitted':False,
            'training_forecast_usd':train_cost,'evaluation_forecast_usd':eval_cost,'total_forecast_usd':train_cost+eval_cost,
            'forecast_inputs':{'seconds_per_update_per_mean_token':unit,'fixed_billing_overhead_usd':overhead,
                'scaled_training_runtime_seconds':runtime,'largest_observed_evaluation_bill_usd':eval_bill}})
        checks.append({'run_id':name,'rows':p*k,'max_samples':config['max_samples'],'steps':steps,'cosine_total_steps_from_this_dose':True})
assert len(forecasts)==22
write(OUT/'CANDIDATE_MANIFEST.json',{'utc':UTC,'authority_commit':AUTHORITY,'status':'Pending source review; no new Modal training started',
    'base_training_config_sha256':sha(base_path),'candidate_training_config_sha256':sha(candidate),'cells':forecasts})
write(OUT/'CONFIG_CHECKS.json',{'original_cases_unchanged':regression,'new_cases':checks,
    'unmodified_live_source_sha256':sha(base_path),'changed_scientific_files':['training_config.py'],
    'training_evaluation_scoring_launchers_unchanged':True,'new_model_calls':0,'T_group_started':False})
totals={g:sum(x['total_forecast_usd'] for x in forecasts if x['group']==g) for g in groups}
balances={'utc_recorded':UTC,'source':'Authenticated Modal Usage & billing UI observed in this turn',
    'tangzhice':{'balance_usd':29.05,'protected_usd':4,'url':'https://modal.com/settings/tangzhice/usage'},
    'townzc':{'balance_usd':13.74,'protected_usd':2,'url':'https://modal.com/settings/townzc/usage'}}
write(OUT/'MODAL_BALANCES.json',balances)
write(OUT/'FORECAST.json',{'utc':UTC,'authority_commit':AUTHORITY,'group_totals_usd':totals,'all22_usd':sum(totals.values()),
    'workspace':'tangzhice','workspace_basis':'A6 addendum requires same setting and seed in same workspace; all three seed17 main-grid settings ran in tangzhice.',
    'formula':'Both-seed maximum train-runtime/(steps*mean tokens), scaled by new steps and mean tokens; max measured fixed billing overhead scaled by max(1,rows/4096); training25% margin+30seconds+.02storage; evaluation max measured bill*1.25+30seconds.',
    'gpu_cpu_memory_rates_usd_per_hour':{'train':train_rate,'eval':eval_rate},
    'per_cell':[{k:x[k] for k in ['group','index','run_id','P','K','E','steps','training_forecast_usd','evaluation_forecast_usd','total_forecast_usd']} for x in forecasts],
    'prelaunch_admission':'Not yet admitted. Must reconcile workspace unsettled reserves and source review before launch.',
    'C_group_pruning_order':'C05,C04,C03,C02,C01 if needed; no workspace changes'})
print(json.dumps({'out':str(OUT),'groups':totals,'total':sum(totals.values()),'candidate_cells':len(triples),'datasets':len(datasets)}))
