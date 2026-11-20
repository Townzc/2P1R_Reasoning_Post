"""A9 section 4: private LogiQA preparation, evaluation and sampling; no training.

Explicitly exempt from prereview by ecda0914; all outputs require full postaudit.
Public artifacts must never contain original inputs or reversible prompt tokens.
"""
import argparse
import collections
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import re
import statistics
import subprocess
import sys

sys.path.insert(0, '.')
from experiments.p012.evaluation import last_boxed, sha256_file
from experiments.p012.tinker_lora import load_renderer, RENDERER

AUTHORITY = 'ecda09143c135a64512fec346fe13d38002c7951'
LOCAL = Path('.local/p012_20261111/amendment9_v1/logiqa')
PUBLIC = Path('reports/p012_20261111/amendment9_logiqa_v1')
TEMPLATE_SOURCE = Path('audit/claude/20261120a/P012_PLAN_v1_AMENDMENT_9.md')
NOW = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
digest = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(Path(p).read_text())


def write(path, obj, private=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')
    if private:
        path.chmod(0o600)


def template():
    return re.search(r'```\n(Read the passage.*?)\n```', TEMPLATE_SOURCE.read_text(), re.S).group(1)


def render_text(row, text):
    replacements = {'text': row['text'], 'question': row['question'],
                    **{f'option_{i}': row['options'][i] for i in range(4)}}
    # One literal substitution pass: input strings containing a marker stay literal.
    return re.sub(r'\{(text|question|option_[0-3])\}', lambda m: replacements[m.group(1)], text)


def normalize_letter(box):
    if box is None:
        return None
    while re.search(r'\\text\{([^{}]*)\}', box):
        box = re.sub(r'\\text\{([^{}]*)\}', r'\1', box)
    box = re.sub(r'[()\[\]{}（）.\s]', '', box)
    return box if box in ('A', 'B', 'C', 'D') else None


def label(record, gold):
    text = record['text']
    boxes = list(re.finditer(r'\\boxed\s*\{', text))
    answer = normalize_letter(last_boxed(text))
    normal = record['finish_reason'] == 'stop'
    # Same final-box boundary as scoring; outputs without a box are separate.
    words = len(text[:boxes[-1].start()].split()) if boxes else None
    return {'id': record['id'], 'draw': record['draw'], 'gold': gold,
            'prediction': answer, 'correct': normal and answer == gold,
            'missing_box': not boxes, 'invalid_or_incomplete_box': bool(boxes) and answer is None,
            'unfinished': not normal, 'words_before_last_box': words,
            'answer_only': words is not None and words < 20}


def check_scorer():
    cases = [
        (r'\boxed{A}', 'stop', 'A', True), (r'\boxed{\text{(B).}}', 'stop', 'B', True),
        (r'\boxed{A} reasoning \boxed{C}', 'stop', 'A', False),
        (r'\boxed{a}', 'stop', 'A', False), (r'\boxed{A or B}', 'stop', 'A', False),
        (r'\boxed{A}', 'length', 'A', False), ('A', 'stop', 'A', False),
        (r'\boxed{A} \boxed{B', 'stop', 'A', False),
        (r'\boxed{ D. }', 'stop', 'D', True), (r'\boxed{A,B}', 'stop', 'A', False),
    ]
    for text, finish, gold, expected in cases:
        assert label({'text': text, 'finish_reason': finish, 'id': 'synthetic', 'draw': 0}, gold)['correct'] == expected
    toy = {'text': '{question}', 'question': 'q', 'options': ['a', 'b', 'c', 'd']}
    assert render_text(toy, '{text} {question}') == '{question} q'
    assert label({'text':' '.join(['word']*19)+r' \boxed{A}','finish_reason':'stop','id':'x','draw':0},'A')['answer_only']
    assert not label({'text':' '.join(['word']*20)+r' \boxed{A}','finish_reason':'stop','id':'x','draw':0},'A')['answer_only']
    return {'scoring_cases_passed':len(cases), 'literal_substitution_check':True, 'answer_only_boundary_checks':2}


def grams(text):
    words = re.findall(r'\w+', text.casefold(), flags=re.UNICODE)
    return {tuple(words[i:i+13]) for i in range(len(words)-12)}


def overlaps(train, test, with_question):
    def text(r):
        return r['text'] + ('\n'+r['question'] if with_question else '')
    exact = collections.defaultdict(set)
    index = collections.defaultdict(set)
    for row in train:
        value = text(row)
        exact[value].add(row['record_id'])
        for gram in grams(value):
            index[gram].add(row['record_id'])
    hits=[];exact_train=set();gram_train=set()
    for row in test:
        e=exact.get(text(row),set());g=set()
        for gram in grams(text(row)):
            g.update(index.get(gram,()))
        exact_train.update(e);gram_train.update(g)
        if e or g:
            hits.append({'test_id':row['record_id'],'exact_train_ids':sorted(e),'13gram_train_ids':sorted(g)})
    return {'text_scope':'passage plus question' if with_question else 'passage only',
            'exact_test_rows':sum(bool(r['exact_train_ids']) for r in hits),
            'exact_train_rows':len(exact_train),'13gram_test_rows':sum(bool(r['13gram_train_ids']) for r in hits),
            '13gram_train_rows':len(gram_train),'matches':hits,
            'exact_normalization':'none','13gram_normalization':'Unicode word regex, casefold; contiguous 13 words',
            'filtered_rows':0}


def prepare():
    checks=check_scorer();manifest=read(LOCAL/'source/MANIFEST.json');splits={}
    for spec in manifest['files']:
        path=LOCAL/'source'/(spec['split']+'.txt')
        assert sha256_file(path)==spec['sha256']
        rows=[]
        for i,line in enumerate(path.read_text().splitlines()):
            r=json.loads(line)
            assert len(r['options'])==4 and type(r['id']) is int and r['answer'] in range(4)
            r.update(record_id=f'logiqa/{spec["split"]}/{i:05d}',source_line_zero_based=i)
            rows.append(r)
        assert len(rows)==spec['rows'];splits[spec['split']]=rows
    assert len(splits['train'])==12567 and len(splits['test'])==1572
    sampled=random.Random(20261120).sample(sorted(splits['train'],key=lambda r:r['id']),300)
    tmpl=template();write(LOCAL/'TEMPLATE_PRIVATE.json',{'template':tmpl},True)
    write(PUBLIC/'DATA_MANIFEST.json',dict(manifest,template_sha256=digest(tmpl.encode()),
        duplicate_source_id_counts={s:len(r)-len({x['id'] for x in r}) for s,r in splits.items()},
        record_identity='split + original zero-based source line; source id is retained, not assumed unique',
        sampling='stable ascending numeric source id, source order retained within ties; random.Random(20261120).sample(300)',
        training_authorized=False,source_text_public=False))
    write(PUBLIC/'OVERLAP.json',{'utc':NOW(),'primary':overlaps(splits['train'],splits['test'],False),
        'supplemental':overlaps(splits['train'],splits['test'],True)})
    # Official JSON was read through the web tool; urllib is blocked by its CDN.
    prices=read(PUBLIC/'PRICES_SOURCE.json')['models']
    picked=[p for p in prices if p['tinker_id'] in ('Qwen/Qwen3.5-4B','Qwen/Qwen3.5-9B')]
    write(PUBLIC/'PRICES.json',{'utc':NOW(),'url':'https://tinker-docs.thinkingmachines.ai/tinker/models.json','models':picked})
    requests=[]
    for model,split,n in [('4B','test',1),('9B','test',1),('9B','train',8)]:
        # Reuse the exact audited asset identity from previous T requests.
        ref=None
        # Fixed previously reviewed public request paths, selected by model only.
        if model=='4B':
            ref=read('reports/p012_20261111/amendment9_admission_v1/requests/a9_r04_tinker_lora_4b_math_p4096_k1_e1_s29_20261120_v1.json')
        else:
            for p in Path('.local/p012_20261111').glob('tinker*/*/request.json'):
                r=read(p)
                if r.get('model')=='Qwen/Qwen3.5-9B' and 'asset' in r:
                    ref=r;break
        assert ref is not None
        tokenizer,renderer=load_renderer(ref)
        selected=splits['test'] if split=='test' else sampled
        records=[];safe=[]
        for i,row in enumerate(selected):
            prompt=render_text(row,tmpl);messages=[{'role':'user','content':prompt}]
            tokens=renderer.build_generation_prompt(messages).to_ints()
            assert tokens==tokenizer.apply_chat_template(messages,add_generation_prompt=True,enable_thinking=False,return_dict=False)
            assert len(tokens)+2048<=8192
            record={'id':row['record_id'],'source_id':row['id'],'source_line_zero_based':row['source_line_zero_based'],
                    'row_index':i,'prompt':prompt,'gold':'ABCD'[row['answer']],
                    'prompt_sha256':digest(prompt.encode()),'prompt_tokens_sha256':digest(json.dumps(tokens).encode()),'prompt_tokens':len(tokens)}
            records.append(record);safe.append({k:v for k,v in record.items() if k!='prompt'})
        name=f'a9_t0_logiqa_{model.lower()}_{split}_n{n}_v1'
        inputs=LOCAL/'inputs'/(name+'.json');write(inputs,records,True)
        price=next(p for p in picked if p['tinker_id']=='Qwen/Qwen3.5-'+model)
        rates={k:float(price[k].removeprefix('$')) for k in ('prefill','sample','train')}
        worst=(sum(x['prompt_tokens'] for x in records)*n*rates['prefill']+len(records)*n*2048*rates['sample'])/1e6
        req={'run_id':name,'model':'Qwen/Qwen3.5-'+model,'split':split,'n':n,
             'asset':ref['asset'],'learning_rate':ref['learning_rate'],'renderer':RENDERER,
             'input_path':str(inputs),'input_sha256':sha256_file(inputs),'template_sha256':digest(tmpl.encode()),
             'max_tokens':2048,'temperature':0.7 if n==8 else 0,'top_p':1,'top_k':-1,
             'seed_base':9000 if n==8 else 17,'seed_formula':'seed_base + row_index*n + draw',
             'prices_per_million':rates,'source_sha256':sha256_file(Path(__file__)),
             'authority_commit':AUTHORITY,'pre_review_exemption':'Amendment9 section4; full post-audit',
             'worst_case_token_cost_usd':worst,'buffered_forecast_usd':worst*1.5,
             'forecast_basis':'Exact private prompt counts plus every output at2048token cap, multiplied by1.5',
             'exploratory':True,'excluded_from_H0_H3':True,'training_authorized':False}
        write(LOCAL/'runs'/name/'request.json',req,True)
        write(PUBLIC/'requests'/(name+'.json'),req);write(PUBLIC/'inputs'/(name+'.json'),safe)
        requests.append(req)
    total=sum(r['buffered_forecast_usd'] for r in requests)
    assert total<=20,total
    write(PUBLIC/'ADMISSION.json',{'utc':NOW(),'authority_commit':AUTHORITY,'forecast_usd':total,'cap_usd':20,
        'already_reserved_in':'reports/p012_20261111/amendment9_admission_v1/TINKER_ADMISSION.json',
        'requests':[r['run_id'] for r in requests],'no_additional_combined_reservation':True,
        'admitted':True,'all_original_inputs_private':True,'checks':checks})
    print(json.dumps({'prepared':len(requests),'buffered_forecast_usd':total,'scorer_checks':checks}))


def generate(directory):
    import tinker
    r=read(directory/'request.json')
    assert r['authority_commit']==AUTHORITY and r['source_sha256']==sha256_file(Path(__file__))
    assert not r['training_authorized'] and r['max_tokens']==2048
    assert sha256_file(Path(r['input_path']))==r['input_sha256']
    assert read(PUBLIC/'ADMISSION.json')['admitted']
    tokenizer,renderer=load_renderer(r);rows=read(r['input_path']);n=r['n']
    assert (r['split'],n,len(rows)) in [('test',1,1572),('train',8,300)]
    output=directory/'result';output.mkdir(exist_ok=False)
    write(output/'REQUEST.json',r,True)
    write(output/'VERSIONS.json',{p:importlib.metadata.version(p) for p in ['tinker','tinker-cookbook','torch','transformers']})
    usage={'prefill_tokens_uncached_upper':0,'completion_tokens':0,'prompt_cache_hit_tokens':0,'completed_calls':0}
    service=tinker.ServiceClient(display_name=r['run_id'])
    try:
        client=service.create_sampling_client(base_model=r['model']).result()
        def one(job):
            i,j=job;row=rows[i];prompt=renderer.build_generation_prompt([{'role':'user','content':row['prompt']}])
            assert digest(json.dumps(prompt.to_ints()).encode())==row['prompt_tokens_sha256']
            seed=r['seed_base']+i*n+j
            response=client.sample(prompt,num_samples=1,sampling_params=tinker.SamplingParams(max_tokens=2048,
                temperature=r['temperature'],top_p=1,top_k=-1,seed=seed,stop=renderer.get_stop_sequences())).result()
            assert len(response.sequences)==1
            seq=response.sequences[0];assert seq.stop_reason in ('length','stop')
            rec={'id':row['id'],'source_id':row['source_id'],'row_index':i,'draw':j,
                'text':tokenizer.decode(seq.tokens,skip_special_tokens=False),'token_ids':seq.tokens,
                'finish_reason':seq.stop_reason,'sequence_id':seq.sequence_id,'sampling_seed':seed,
                'prompt_sha256':row['prompt_sha256'],'prompt_tokens_sha256':row['prompt_tokens_sha256'],
                'prompt_tokens':prompt.length,'prompt_cache_hit_tokens':response.prompt_cache_hit_tokens}
            return rec
        with (output/'raw.jsonl').open('x') as f,ThreadPoolExecutor(max_workers=32) as pool:
            for rec in pool.map(one,((i,j) for i in range(len(rows)) for j in range(n))):
                f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush()
                usage['completed_calls']+=1;usage['prefill_tokens_uncached_upper']+=rec['prompt_tokens']
                usage['completion_tokens']+=len(rec['token_ids']);usage['prompt_cache_hit_tokens']+=rec['prompt_cache_hit_tokens']
                if usage['completed_calls']%100==0:print(json.dumps({'utc':NOW(),**usage}),flush=True)
        usage['upper_token_cost_usd']=(usage['prefill_tokens_uncached_upper']*r['prices_per_million']['prefill']+
            usage['completion_tokens']*r['prices_per_million']['sample'])/1e6
        assert usage['upper_token_cost_usd']<=r['worst_case_token_cost_usd']+1e-6
        write(output/'USAGE.json',usage)
        write(output/'COMPLETE.json',{'utc':NOW(),'success':True,'raw_sha256':sha256_file(output/'raw.jsonl'),'calls':usage['completed_calls']})
        service.close(status='success').result()
    except BaseException:
        write(output/'PARTIAL_USAGE.json',usage)
        service.close(status='errored').result()
        raise


def score(directory):
    r=read(directory/'request.json');output=directory/'result';raw=output/'raw.jsonl'
    freeze=read(directory/'PREDICTION_BEFORE_SCORE.json')
    assert freeze['authority_commit']==AUTHORITY and freeze['raw_sha256']==sha256_file(raw)
    assert freeze['scorer_source_sha256']==sha256_file(Path(__file__))
    assert read(output/'COMPLETE.json')['success']
    inputs=read(r['input_path']);gold={x['id']:x['gold'] for x in inputs}
    records=[json.loads(x) for x in raw.read_text().splitlines()];n=r['n']
    assert {(x['id'],x['draw']) for x in records}=={(x['id'],j) for x in inputs for j in range(n)}
    assert len(records)==len(inputs)*n and len({x['sequence_id'] for x in records})==len(records)
    assert len({x['sampling_seed'] for x in records})==len(records)
    labels=[label(x,gold[x['id']]) for x in records]
    dest=directory/'score';dest.mkdir(exist_ok=False)
    with (dest/'labels.jsonl').open('x') as f:
        for row in labels:f.write(json.dumps(row)+'\n')
    lengths=[len(x['token_ids']) for x,y in zip(records,labels) if y['correct']]
    def quantiles(xs):
        if not xs:return None
        s=sorted(xs)
        return {'n':len(s),'min':s[0],'p25':s[int((len(s)-1)*.25)],'median':statistics.median(s),
                'p75':s[int((len(s)-1)*.75)],'p90':s[int((len(s)-1)*.9)],'p95':s[int((len(s)-1)*.95)],'max':s[-1],'mean':statistics.mean(s)}
    result={'utc':NOW(),'run_id':r['run_id'],'model':r['model'],'source_sha256':r['source_sha256'],
        'authority_commit':AUTHORITY,'raw_sha256':sha256_file(raw),'labels_sha256':sha256_file(dest/'labels.jsonl'),
        'outputs':len(records),'correct':sum(x['correct'] for x in labels),'accuracy':sum(x['correct'] for x in labels)/len(labels),
        'answer_only_count':sum(x['answer_only'] for x in labels),'unfinished_count':sum(x['unfinished'] for x in labels),
        'missing_box_count':sum(x['missing_box'] for x in labels),'invalid_box_count':sum(x['invalid_or_incomplete_box'] for x in labels),
        'correct_solution_token_lengths':quantiles(lengths),'usage':read(output/'USAGE.json'),
        'independent_result_audit':'pending','training_authorized':False,'exploratory':True,'excluded_from_H0_H3':True}
    if n==8:
        counts=collections.Counter();all_same=0
        for i,row in enumerate(inputs):
            rr=records[i*8:(i+1)*8];ll=labels[i*8:(i+1)*8]
            assert all(x['id']==row['id'] for x in rr)
            counts[sum(x['correct'] for x in ll)]+=1
            all_same+=len({tuple(x['token_ids']) for x in rr})==1
        result.update(correct_of8_distribution={str(k):counts[k] for k in range(9)},
            at_least4_fraction=sum(v for k,v in counts.items() if k>=4)/300,
            eight_identical_questions=all_same,seeds_and_sequence_ids_all_distinct=True)
        assert all_same<=150,'Majority eight identical: stop and report under46e98da5'
        result['projected_train_rows_at_least4']=result['at_least4_fraction']*12567
        result['projected_full_train8_usd']=result['usage']['upper_token_cost_usd']*12567/300
    write(dest/'RESULTS.json',result)
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','generate','score','test']);parser.add_argument('--directory',type=Path)
    args=parser.parse_args()
    if args.mode=='prepare':prepare()
    elif args.mode=='generate':generate(args.directory)
    elif args.mode=='score':score(args.directory)
    else:print(json.dumps(check_scorer()))
