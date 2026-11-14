from pathlib import Path
import hashlib, importlib.util, json

ROOT=Path('.local/p012_20261111'); PUBLIC=Path('reports/p012_20261111')
AUTHORITY='2289056089f9ff3467d490efe93a92a07effb063'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
spec=importlib.util.spec_from_file_location('p012_a6_prior_accounting',ROOT/'amendment6_v1/a6_followup_accounting.py')
prior_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior_module)


def accounting():
    prior=prior_module.accounting();components=[]
    for d in sorted((ROOT/'a7_runs_v1').glob('*')):
        if not (d/'request.json').exists():continue
        r=read(d/'request.json')
        if r['mode']!='train':continue
        assert r['authority_commit']==AUTHORITY and r['forecast']['admitted']
        ev=d.with_name(d.name.replace(f'_s{r["seed"]}_',f'_s{r["seed"]}_greedy_'))
        for out,kind in [(d,'training'),(ev,'evaluation')]:
            done=(out/'result/COMPLETE.json').exists()
            if done:
                assert read(out/'result/COMPLETE.json')['success']
                value=read(out/'result/USAGE.json')['upper_token_cost_usd']+(.1 if kind=='training' else 0)
            else:value=r['forecast']['training_buffered_usd' if kind=='training' else 'reserved_greedy_usd']
            components.append({'run_id':out.name,'group':r['A7_group'],'kind':kind,'complete':done,'usd':value,
                'usage_sha256':sha(out/'result/USAGE.json') if done else None})
    for d in sorted((ROOT/'a7_concise_v1').glob('*')):
        if not (d/'request.json').exists():continue
        r=read(d/'request.json');assert r['authority_commit']==AUTHORITY and r['forecast']['admitted']
        done=(d/'result/COMPLETE.json').exists()
        value=read(d/'result/USAGE.json')['upper_token_cost_usd'] if done else r['forecast']['generation_cap_usd']
        components.append({'run_id':d.name,'group':'A7-1','kind':'construction','complete':done,'usd':value,
            'usage_sha256':sha(d/'result/USAGE.json') if done else None})
    failure_pointer=ROOT/'amendment7_v1/INTERRUPTION_LEDGER.json'
    if failure_pointer.exists():
        pointer=read(failure_pointer);assert sha(pointer['path'])==pointer['sha256']
        components.extend(x for x in read(pointer['path'])['components'] if x['group']=='A7')
    total=sum(x['usd'] for x in components)
    return {'prior_components':prior['components'],'A7_components':components,
        'original_T_accounted_and_reserved_usd':prior['original_T_reserved_usd'],
        'A6_2_accounted_and_reserved_usd':prior['A6_2_accounted_and_reserved_usd'],
        'A6_3_accounted_and_reserved_usd':prior['A6_3_accounted_and_reserved_usd'],
        'pre_A7_accounted_and_reserved_usd':prior['combined_reserved_usd'],
        'A7_accounted_and_reserved_usd':total,'combined_reserved_usd':prior['combined_reserved_usd']+total,
        'original_T_ledger_source':prior['original_T_ledger_source'],
        'caps_usd':{'original_T':340,'A6-2':50,'A6-3':35,'A7':60,'combined':485},
        'legacy_queue_bound':'Existing queues retain pre-A7 cap425; their cap425 plus separateA7 cap60 guarantees combined485.'}


def ensure_budget(snapshot, amount):
    assert snapshot['A7_accounted_and_reserved_usd']+amount<=60, ('A7 cap',snapshot['A7_accounted_and_reserved_usd'],amount)
    assert snapshot['combined_reserved_usd']+amount<=485, ('Combined cap',snapshot['combined_reserved_usd'],amount)
