"""A10 S1 only: private inputs, immutable batches, no training or account changes.

Generation is exempt from prereview under f42dcd15 section1.4. Training data
and the separate candidate training path require review before any training.
"""
import argparse
import collections
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import sys
import subprocess
import traceback
import zipfile

sys.path.insert(0, '.')
sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import publish, lock
from experiments.p012.tinker_lora import load_renderer, rendered_datum

ROOT = Path('.local/p012_20261111')
LOCAL = ROOT/'amendment10_v1'
PUBLIC = Path('reports/p012_20261111/amendment10_s1_v1')
PILOT = Path('reports/p012_20261111/amendment9_logiqa_v1')
AUTHORITY = 'f42dcd1595807406f67ff694e5235447c6814ebc'
PILOT_SOURCE_SHA = '0611b495fbc796f0bd316ca9ee2f854b60971b3889238a098828d62dea7644dc'
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest = lambda b: hashlib.sha256(b).hexdigest()
spec = importlib.util.spec_from_file_location('a9_logiqa', PILOT/'logiqa_pilot.py')
pilot = importlib.util.module_from_spec(spec); spec.loader.exec_module(pilot)


def write(path, value, private=False, exclusive=True):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x' if exclusive else 'w') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')
    if private: path.chmod(0o600)


def safe(row):
    return {k:v for k,v in row.items() if k!='prompt'}


def solution_text(text):
    # Remove only the terminal stop marker; preserve all other original text.
    return text.removesuffix('<|im_end|>')


def unique_correct(records, labels):
    chosen=[]; seen=set()
    for r,y in zip(records,labels,strict=True):
        assert (r['id'],r['draw'])==(y['id'],y['draw'])
        if not y['correct']: continue
        text=solution_text(r['text']); normalized=' '.join(text.split())
        if normalized in seen: continue
        seen.add(normalized);chosen.append((r,text))
        if len(chosen)==4:break
    return chosen


def checks():
    assert pilot.check_scorer()['scoring_cases_passed']==10
    rr=[{'id':'x','draw':i,'text':s} for i,s in enumerate(['a  b<|im_end|>','a b<|im_end|>','c','d','e'])]
    yy=[{'id':'x','draw':i,'correct':True} for i in range(5)]
    assert [r['draw'] for r,_ in unique_correct(rr,yy)]==[0,2,3,4]
    assert solution_text(' x \n<|im_end|>')==' x \n'
    assert 20000+600*8==24800
    return {'pilot_scoring_checks':10,'whitespace_duplicate_skip':True,'terminal_marker_only_removal':True,'global_seed_batch_boundary':True}


def prepare():
    assert sha(PILOT/'logiqa_pilot.py')==PILOT_SOURCE_SHA
    src=read(PILOT/'DATA_MANIFEST.json');path=ROOT/'amendment9_v1/logiqa/source/train.txt'
    assert sha(path)==next(x['sha256'] for x in src['files'] if x['split']=='train')
    rows=[]
    for i,line in enumerate(path.read_text().splitlines()):
        r=json.loads(line);r.update(record_id=f'logiqa/train/{i:05d}',source_line_zero_based=i);rows.append(r)
    overlap=read(PILOT/'OVERLAP.json')['primary']
    removed={x for r in overlap['matches'] for k in ['exact_train_ids','13gram_train_ids'] for x in r[k]}
    clean=[r for r in rows if r['record_id'] not in removed];seen=set();unique=[];duplicates=[]
    for r in clean:
        if r['text'] in seen:duplicates.append(r['record_id']);continue
        seen.add(r['text']);unique.append(r)
    assert (len(rows),len(removed),len(clean),len(unique))==(12567,461,12106,11169),'A10 count mismatch: stop'
    old={r['id'] for r in read(PILOT/'inputs/a9_t0_logiqa_9b_train_n8_v1.json')}
    pilot_removed=[r['record_id'] for r in unique if r['record_id'] in old]
    available=sorted((r for r in unique if r['record_id'] not in old),key=lambda r:r['record_id'])
    random.Random(20261121).shuffle(available)
    teacher=read(PILOT/'requests/a9_t0_logiqa_9b_train_n8_v1.json')
    student=read(PILOT/'requests/a9_t0_logiqa_4b_test_n1_v1.json')
    token_files=['tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','chat_template.jinja']
    assert {x['path']:x['sha256'] for x in teacher['asset']['files'] if x['path'] in token_files}=={x['path']:x['sha256'] for x in student['asset']['files'] if x['path'] in token_files}
    tokenizer,renderer=load_renderer(teacher);template=pilot.template();inputs=[]
    for i,row in enumerate(available):
        prompt=pilot.render_text(row,template);messages=[{'role':'user','content':prompt}]
        tokens=renderer.build_generation_prompt(messages).to_ints()
        assert tokens==tokenizer.apply_chat_template(messages,add_generation_prompt=True,enable_thinking=False,return_dict=False)
        assert len(tokens)+4096<=8192
        inputs.append({'id':row['record_id'],'source_id':row['id'],'source_line_zero_based':row['source_line_zero_based'],'row_index':i,'gold':'ABCD'[row['answer']],'prompt':prompt,'prompt_sha256':digest(prompt.encode()),'prompt_tokens':len(tokens),'prompt_tokens_sha256':digest(json.dumps(tokens).encode())})
    write(LOCAL/'ALL_INPUTS_PRIVATE.json',inputs,True)
    write(PUBLIC/'AVAILABLE_ROWS.json',[safe(x) for x in inputs])
    write(PUBLIC/'FILTERS.json',{'source_rows':12567,'overlap_removed_ids':sorted(removed),'after_overlap':12106,'duplicate_passage_removed_ids':duplicates,'after_passage_dedup':11169,'pilot_removed_ids':pilot_removed,'available_rows':len(inputs),'shuffle':'sort record_id then Random(20261121).shuffle','original_text_public':False})
    write(PUBLIC/'MANIFEST.json',{'utc':utc(),'authority_commit':AUTHORITY,'authority_file_sha256':sha(Path('audit/claude/20261120e/P012_PLAN_v1_AMENDMENT_10.md')),'source_sha256':sha(Path(__file__)),'pilot_source_sha256':PILOT_SOURCE_SHA,'pilot_audit_commit':'04b1049f7238f2d1b330b8d6bd826fafeba23530','source_data_manifest_sha256':sha(PILOT/'DATA_MANIFEST.json'),'overlap_sha256':sha(PILOT/'OVERLAP.json'),'template_sha256':digest(template.encode()),'private_input_sha256':sha(LOCAL/'ALL_INPUTS_PRIVATE.json'),'public_input_identities_sha256':sha(PUBLIC/'AVAILABLE_ROWS.json'),'teacher':teacher,'student':student,'batch_rows':600,'draws':8,'max_tokens':4096,'seed_formula':'20000 + global_shuffled_row_index*8 + draw','stop_after_qualified_rows':4300,'S1_cap_usd':75,'A10_independent_cap_usd':200,'training_authorized_by_this_program':False,'checks':checks()})
    write(PUBLIC/'DEPENDENCIES.json',{str(p):sha(p) for p in [Path('experiments/p012/tinker_lora.py'),PILOT/'logiqa_pilot.py',PILOT/'DATA_MANIFEST.json',PILOT/'OVERLAP.json']})
    print(json.dumps({'available':len(inputs),'removed_pilot':len(pilot_removed),'checks':checks()}))


def generate(rows, request, output):
    import tinker
    tokenizer,renderer=load_renderer(request['teacher'])
    service=tinker.ServiceClient(display_name=request['run_id'])
    usage={'completed_calls':0,'prefill_tokens_uncached_upper':0,'completion_tokens':0,'prompt_cache_hit_tokens':0}
    output.mkdir(exist_ok=False)
    try:
        client=service.create_sampling_client(base_model='Qwen/Qwen3.5-9B').result()
        def one(job):
            row,j=job;prompt=renderer.build_generation_prompt([{'role':'user','content':row['prompt']}])
            assert digest(json.dumps(prompt.to_ints()).encode())==row['prompt_tokens_sha256']
            seed=20000+row['row_index']*8+j
            response=client.sample(prompt,num_samples=1,sampling_params=tinker.SamplingParams(max_tokens=4096,temperature=.7,top_p=1,top_k=-1,seed=seed,stop=renderer.get_stop_sequences())).result()
            assert len(response.sequences)==1
            seq=response.sequences[0];assert seq.stop_reason in ('stop','length')
            return {'id':row['id'],'row_index':row['row_index'],'draw':j,'text':tokenizer.decode(seq.tokens,skip_special_tokens=False),'token_ids':seq.tokens,'finish_reason':seq.stop_reason,'sequence_id':seq.sequence_id,'sampling_seed':seed,'prompt_sha256':row['prompt_sha256'],'prompt_tokens_sha256':row['prompt_tokens_sha256'],'prompt_tokens':prompt.length,'prompt_cache_hit_tokens':response.prompt_cache_hit_tokens}
        with (output/'raw.jsonl').open('x') as f,ThreadPoolExecutor(max_workers=32) as pool:
            for r in pool.map(one,((row,j) for row in rows for j in range(8))):
                f.write(json.dumps(r,ensure_ascii=False)+'\n');f.flush()
                usage['completed_calls']+=1;usage['prefill_tokens_uncached_upper']+=r['prompt_tokens'];usage['completion_tokens']+=len(r['token_ids']);usage['prompt_cache_hit_tokens']+=r['prompt_cache_hit_tokens']
                if usage['completed_calls']%100==0:print(json.dumps({'utc':utc(),**usage}),flush=True)
        price=request['prices_per_million'];usage['upper_token_cost_usd']=(usage['prefill_tokens_uncached_upper']*price['prefill']+usage['completion_tokens']*price['sample'])/1e6
        write(output/'USAGE.json',usage);write(output/'COMPLETE.json',{'utc':utc(),'success':True,'raw_sha256':sha(output/'raw.jsonl')})
        service.close(status='success').result()
    except BaseException:
        write(output/'PARTIAL_USAGE.json',usage);service.close(status='errored').result();raise


def qualify(rows, directory, student):
    raw=[json.loads(x) for x in (directory/'result/raw.jsonl').read_text().splitlines()]
    assert len(raw)==len(rows)*8 and len({r['sequence_id'] for r in raw})==len(raw)
    assert len({r['sampling_seed'] for r in raw})==len(raw)
    labels=[];qualified=[];selected=[];hist=collections.Counter();violations=[];same=0
    tokenizer,renderer=load_renderer(student)
    for i,row in enumerate(rows):
        rr=raw[i*8:(i+1)*8];assert [(r['id'],r['draw'],r['sampling_seed']) for r in rr]==[(row['id'],j,20000+row['row_index']*8+j) for j in range(8)]
        yy=[pilot.label(r,row['gold']) for r in rr];labels.extend(yy);hist[sum(y['correct'] for y in yy)]+=1
        same+=len({tuple(r['token_ids']) for r in rr})==1
        chosen=unique_correct(rr,yy)
        if len(chosen)!=4:continue
        q={'id':row['id'],'row_index':row['row_index'],'correct_of8':sum(y['correct'] for y in yy),'selected':[]}
        for r,text in chosen:
            train={'parent_id':row['id'],'problem':row['prompt'],'solution':text,'solution_hash':digest(text.encode()),'draw':r['draw']}
            try:
                datum,rendered=rendered_datum(train,tokenizer,renderer)
                counts={'training_input_tokens':datum.model_input.length,'supervised_target_tokens':rendered['target_tokens'],'full_sequence_tokens':len(rendered['input_token_ids'])}
            except ValueError as exc:
                if str(exc)!='Overlength training row; never truncate':raise
                from tinker_cookbook import renderers
                mi,w=renderer.build_supervised_example([{'role':'user','content':row['prompt']},{'role':'assistant','content':text}],train_on_what=renderers.TrainOnWhat.LAST_ASSISTANT_MESSAGE)
                counts={'full_sequence_tokens':mi.length};violations.append({'id':row['id'],'draw':r['draw'],**counts})
            selected.append(train);q['selected'].append({'draw':r['draw'],'solution_sha256':train['solution_hash'],**counts})
        qualified.append(q)
    with (directory/'labels.jsonl').open('x') as f:
        for x in labels:f.write(json.dumps(x)+'\n')
    write(directory/'QUALIFIED.json',qualified);write(directory/'SELECTED_PRIVATE.json',selected,True)
    result={'utc':utc(),'rows':len(rows),'outputs':len(raw),'correct_of8_distribution':{str(k):hist[k] for k in range(9)},'qualified_rows':len(qualified),'eight_identical_questions':same,'seeds_and_sequence_ids_distinct':True,'overlength_training_samples':violations,'labels_sha256':sha(directory/'labels.jsonl'),'raw_sha256':sha(directory/'result/raw.jsonl'),'independent_audit':'pending'}
    write(directory/'RESULTS.json',result)
    return result,qualified


def archive_batch(directory, public):
    with zipfile.ZipFile(public/'evidence.zip','x',zipfile.ZIP_DEFLATED) as z:
        for p in [*sorted((directory/'result').iterdir()),directory/'labels.jsonl',directory/'QUALIFIED.json',directory/'RESULTS.json']:
            if p.is_file():
                b=p.read_bytes();assert b'/Users/' not in b
                z.writestr(('result/' if p.parent.name=='result' else '')+p.name,b)
    write(public/'RESULTS.json',read(directory/'RESULTS.json'))


def run():
    manifest=read(PUBLIC/'MANIFEST.json');assert manifest['source_sha256']==sha(Path(__file__)) and sha(PILOT/'logiqa_pilot.py')==PILOT_SOURCE_SHA
    assert sha(LOCAL/'ALL_INPUTS_PRIVATE.json')==manifest['private_input_sha256']
    assert read(PUBLIC/'OWNER_BUDGET_DECISION.json')['A10_independent_cap_usd']==200
    for name,h in read(PUBLIC/'DEPENDENCIES.json').items():assert sha(name)==h
    for p in [Path(__file__),PUBLIC/'MANIFEST.json',PUBLIC/'OWNER_BUDGET_DECISION.json',PUBLIC/'DEPENDENCIES.json']:
        p=p.resolve().relative_to(Path.cwd());assert p.read_bytes()==subprocess.check_output(['git','show','HEAD:'+str(p)])
    rows=read(LOCAL/'ALL_INPUTS_PRIVATE.json');state={'utc':utc(),'authority_commit':AUTHORITY,'status':'running','completed_batches':[],'S1_actual_token_upper_usd':0,'qualified_rows':0,'automatic_retries':False}
    write(LOCAL/'QUEUE.json',state,True);os.environ['TINKER_API_KEY']=(ROOT/'credentials/tinker_api_key').read_text().strip()
    try:
        for start in range(0,len(rows),600):
            if state['qualified_rows']>=4300:break
            batch=rows[start:start+600];num=len(state['completed_batches'])+1;name=f'a10_s1_batch{num:02d}_v1'
            d=LOCAL/'batches'/name;d.mkdir(parents=True,exist_ok=False);pub=PUBLIC/'batches'/name;pub.mkdir(parents=True,exist_ok=False)
            price=manifest['teacher']['prices_per_million']
            if not state['completed_batches']:
                expected=(sum(r['prompt_tokens'] for r in batch)*8*price['prefill']+len(batch)*8*4096*price['sample'])/1e6
                basis='Exact prompts; every first-batch sample at4096 cap'
            else:
                expected=max(x['token_cost_usd']/x['rows'] for x in state['completed_batches'])*len(batch)
                basis='Maximum observed completed-batch token cost per row'
            forecast=expected*1.5;used=state['S1_actual_token_upper_usd']
            with lock('BUDGET_ADMISSION.lock'):
                assert used+forecast<=75 and used+forecast<=200,'S1 budget admission failed; stop'
                request={'utc':utc(),'run_id':name,'authority_commit':AUTHORITY,'source_sha256':sha(Path(__file__)),'teacher':manifest['teacher'],'global_start':start,'rows':len(batch),'n':8,'max_tokens':4096,'temperature':.7,'top_p':1,'seed_formula':manifest['seed_formula'],'prices_per_million':price,'safe_inputs_sha256':digest(json.dumps([safe(r) for r in batch],ensure_ascii=False,indent=2).encode()+b'\n'),'forecast_usd':forecast,'forecast_basis':basis,'prior_S1_token_upper_usd':used,'S1_cap_usd':75,'A10_independent_cap_usd':200,'no_other_A10_jobs_started':True}
                write(pub/'INPUT_IDENTITIES.json',[safe(r) for r in batch]);assert sha(pub/'INPUT_IDENTITIES.json')==request['safe_inputs_sha256']
                write(pub/'REQUEST.json',request);write(d/'REQUEST.json',request,True)
                state['active_batch']={'run_id':name,'forecast_usd':forecast,'request_sha256':sha(pub/'REQUEST.json')}
                write(LOCAL/'QUEUE.json',state,True,False);write(PUBLIC/'CURRENT_STATUS.json',state,exclusive=False)
                publish([pub,PUBLIC/'CURRENT_STATUS.json'],'P012 A10 S1: admit frozen '+name+' before generation')
            generate(batch,request,d/'result')
            freeze={'utc':utc(),'authority_commit':AUTHORITY,'source_sha256':sha(Path(__file__)),'raw_sha256':sha(d/'result/raw.jsonl'),'selection_rule':'at least4correct, first4whitespace-distinct correct solutions by draw; fixed4300pool stopping'}
            write(pub/'PREDICTION_BEFORE_SCORE.json',freeze);publish([pub/'PREDICTION_BEFORE_SCORE.json'],'P012 A10 S1: freeze scoring and selection binding '+name)
            result,q=qualify(batch,d,manifest['student']);archive_batch(d,pub)
            cost=read(d/'result/USAGE.json')['upper_token_cost_usd'];state['S1_actual_token_upper_usd']+=cost
            state['completed_batches'].append({'run_id':name,'rows':len(batch),'qualified':len(q),'token_cost_usd':cost,'raw_sha256':result['raw_sha256']});state['qualified_rows']+=len(q)
            state['active_batch']=None
            state['utc']=utc();write(LOCAL/'QUEUE.json',state,True,False);write(PUBLIC/'CURRENT_STATUS.json',state,exclusive=False)
            publish([pub,PUBLIC/'CURRENT_STATUS.json'],'P012 A10 S1: preserve complete '+name+' outputs and qualification evidence')
            assert result['eight_identical_questions']<=len(batch)/2,'Majority eight-identical: stop'
            assert not result['overlength_training_samples'],'Selected training sample exceeds4096: stop and report'
            assert state['S1_actual_token_upper_usd']<=75,'S1 actual usage exceeded cap: stop'
        assert state['qualified_rows']>=4096,'Exhausted available rows below4096: stop'
        state.update(utc=utc(),status='generation_complete_data_and_training_review_required')
        write(LOCAL/'QUEUE.json',state,True,False);write(PUBLIC/'CURRENT_STATUS.json',state,exclusive=False)
        publish([PUBLIC/'CURRENT_STATUS.json'],'P012 A10 S1: close authorized generation; await data and training-path review')
    except BaseException as exc:
        state.update(utc=utc(),status='stopped_for_inspection',error=str(exc))
        write(LOCAL/'QUEUE.json',state,True,False);write(PUBLIC/'STOPPED.json',state)
        publish([PUBLIC/'STOPPED.json'],'P012 A10 S1: preserve stopped condition without replay')
        traceback.print_exc();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','run','test']);args=parser.parse_args()
    if args.mode=='prepare':prepare()
    elif args.mode=='run':run()
    else:print(json.dumps(checks()))
