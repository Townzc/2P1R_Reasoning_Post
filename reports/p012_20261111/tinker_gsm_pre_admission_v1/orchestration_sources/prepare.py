"""Prepare unchanged reviewed Tinker paths on frozen GSM8K inputs; CPU only."""
from pathlib import Path
import copy, datetime, hashlib, json, shutil, subprocess
from experiments.p012.tinker_lora import load_renderer, rendered_datum, generation_messages
from experiments.p012.training_config import grid_dose

ROOT=Path('.local/p012_20261111'); OUT=Path('reports/p012_20261111/tinker_gsm_preparation_v1')
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')

assert not OUT.exists();OUT.mkdir()
runner=sha('experiments/p012/tinker_lora.py')
assert runner=='050a9f43d81c7a610dfc9ca30c901103e145fff28384d2efd1f13247fc60f5ee'
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
c6=read(ROOT/'c6_frozen_v1/MANIFEST.json');c7=read(ROOT/'c7_prepared_v1/MANIFEST.json')
assert sha(ROOT/'c6_frozen_v1/MANIFEST.json')==c7['sources']['frozen_manifest_sha256']
c7_hashes={g['file']:g['input_sha256'] for m in c7['models'] for g in m['generation']}
for name in ['nll1000','L','P','R','K8','K4']:
    f=ROOT/'c6_frozen_v1/gsm8k'/(name+'.jsonl')
    assert sha(f)==c6['tasks']['gsm8k']['files'][name+'.jsonl']['sha256']
    (OUT/'inputs').mkdir(exist_ok=True);shutil.copyfile(f,OUT/'inputs'/f.name)
for name in ['gsm8k_baseline0','gsm8k_baseline4','gsm8k_holdout0','gsm8k_holdout4']:
    f=ROOT/'c7_prepared_v1'/(name+'.jsonl');assert sha(f)==c7_hashes[f.name]
    shutil.copyfile(f,OUT/'inputs'/f.name)
test=ROOT/'main_eval/inputs_v1/gsm8k1319.jsonl'
shutil.copyfile(test,OUT/'inputs/gsm8k1319.jsonl')
pre=[];train=[]
for key in ['4b','9b','9b_base']:
    stem=f'tinker_lora_qwen3_5_{key}_math_pre_'
    ref=ROOT/'tinker_formal_v1'/(stem+'nll_20261113_v1')
    template=read(ref/'request.json');tok,rend=load_renderer(template)
    for endpoint in ['nll','baseline4']+([] if key=='9b_base' else ['baseline0'])+['holdout8']:
        version='v2' if endpoint=='holdout8' else 'v1'
        old=ROOT/'tinker_formal_v1'/(stem+endpoint+'_20261113_'+version)
        req=read(old/'request.json');req['run_id']=f'tinker_lora_qwen3_5_{key}_gsm8k_pre_{endpoint}_20261114_v1'
        req['code_commit']=head;req['authority']='Original A4 T-GSM, reaffirmed by owner accepting e9f0ebdd; unchanged reviewed scientific path'
        req['source_sha256']=runner;req.pop('replaces_invalid_independent_sampling_endpoint',None)
        if endpoint=='nll':
            inp=OUT/'inputs/nll1000.jsonl';rows=[json.loads(x) for x in inp.open()]
            ds=[rendered_datum(row,tok,rend) for row in rows]
            tokens=sum(d.model_input.length for d,e in ds)
            detail={'rows':len(rows),'parents':len({r['parent_id'] for r in rows}),'training_input_tokens':tokens,'maximum_sequence_tokens':max(d.model_input.length for d,e in ds),'all_rows_renderer_and_mask_verified':True}
            assert detail['rows']==1000 and detail['parents']==500
            req['dataset']={'path':str(inp),'sha256':sha(inp)}
            estimate=tokens*req['prices_per_million']['train']/1e6;buffer=estimate*1.25+.05
        else:
            kind='holdout4' if endpoint=='holdout8' and key=='9b_base' else 'holdout0' if endpoint=='holdout8' else endpoint
            inp=OUT/'inputs'/('gsm8k_'+kind+'.jsonl');rows=[json.loads(x) for x in inp.open()];lengths=[]
            for row in rows:
                assert row.get('messages');messages=generation_messages(row);ids=rend.build_generation_prompt(messages).to_ints()
                assert ids==tok.apply_chat_template(messages,add_generation_prompt=True,enable_thinking=False,return_dict=False)
                assert len(ids)+4096<=8192;lengths.append(len(ids))
            n=req['n'];assert len(rows)==(500 if n==8 else 1319)
            req['evaluation']={'path':str(inp),'sha256':sha(inp),'task':'gsm8k'}
            measured=read(old/'result/USAGE.json')['sampling'];old_rows=len(list(Path(read(old/'request.json')['evaluation']['path']).open()))
            predicted_completion=measured['completion_tokens']*len(rows)/old_rows
            estimate=(sum(lengths)*n*req['prices_per_million']['prefill']+predicted_completion*req['prices_per_million']['sample'])/1e6
            buffer=estimate*1.5
            detail={'rows':len(rows),'draws':len(rows)*n,'maximum_prompt_tokens':max(lengths),'exact_prefill_tokens':sum(lengths)*n,'predicted_completion_tokens':predicted_completion,'basis':'Same-model same-format MATH measured completion tokens scaled by GSM question count; exact GSM prompt tokens; entire sampling cost times1.5. Cross-task forecast, not measured GSM outputs.','reference_usage_sha256':sha(old/'result/USAGE.json'),'HF_template_parity_all_rows':True}
        req['forecast']={'admitted':False,'estimated_token_usd':estimate,'buffered_upper_usd':buffer,'T_GSM_cap':105,'T_total_hard_cap':340,'combined_cap':485,'basis':detail}
        req['awaiting_sampling_review']=False
        write(OUT/'pre_requests'/(req['run_id']+'.json'),req)
        pre.append({'run_id':req['run_id'],'key':key,'endpoint':endpoint,'request':str(OUT/'pre_requests'/(req['run_id']+'.json')),'forecast_usd':buffer,'input_checks':detail})
        print(key,endpoint,round(buffer,6),flush=True)
    for cell in ['L','P','R','K8','K4']:
        inp=OUT/'inputs'/(cell+'.jsonl');rows=[json.loads(x) for x in inp.open()];ds=[rendered_datum(row,tok,rend) for row in rows];dose=grid_dose(cell)
        assert len(rows)==dose['distinct_rows'];tokens=sum(d.model_input.length for d,e in ds)*dose['epochs'];cost=tokens*template['prices_per_million']['train']/1e6
        record={'key':key,'model':template['model'],'asset':template['asset'],'cell':cell,'dataset':{'path':str(inp),'sha256':sha(inp)},'dose':dose,'maximum_sequence_tokens':max(d.model_input.length for d,e in ds),'full_training_input_tokens':tokens,'training_token_cost_upper_usd':cost,'buffered_training_and_storage_usd':cost*1.25+.1,'all_rows_renderer_and_mask_verified':True,'seed17':True,'seed29':cell!='K4'}
        assert record['maximum_sequence_tokens']+1<=4096
        train.append(record);print(key,cell,'train_tokens',tokens,flush=True)
write(OUT/'PRETRAINING_PREFLIGHT.json',pre);write(OUT/'TRAINING_COUNTS.json',train)
write(OUT/'MANIFEST.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':'prepared_not_admitted','model_calls':0,'runner_sha256':runner,'C6_manifest_sha256':sha(ROOT/'c6_frozen_v1/MANIFEST.json'),'C7_manifest_sha256':sha(ROOT/'c7_prepared_v1/MANIFEST.json'),'pretraining_endpoints':len(pre),'pretraining_buffered_usd':sum(x['forecast_usd'] for x in pre),'training_cells':27,'all_training_buffered_usd':sum(x['buffered_training_and_storage_usd']*(2 if x['seed29'] else 1) for x in train),'evaluation_forecast':'To be admitted by model and batch after pretraining measurements; full GSM1319 greedy; unchanged4096/8192','inputs':{str(p):sha(p) for p in (OUT/'inputs').iterdir()}})
print('PREPARED',OUT,flush=True)
