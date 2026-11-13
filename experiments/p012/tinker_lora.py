"""A4 Tinker LoRA track: pinned cookbook renderer and standard SDK operations.

Smoke is explicitly authorized before review. Formal jobs require the accepted
review commit in their request. This module never scores post-training outputs;
the prediction freeze must precede use of the existing scoring.py separately.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import time

from .evaluation import PROMPTS, prompt_text, sha256_file
from .training_config import CELLS, grid_dose

MODELS = ('Qwen/Qwen3.5-4B', 'Qwen/Qwen3.5-9B', 'Qwen/Qwen3.5-9B-Base')
COOKBOOK_COMMIT = '8486b8df2fc32e9713cf96dd5f75d43c7ef70a17'
RENDERER = 'qwen3_5_disable_thinking'


def write_json(path, obj):
    with Path(path).open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2); f.write('\n')


def read_rows(spec):
    path = Path(spec['path'])
    if path.is_absolute():
        raise ValueError('T-2: use repository-relative input paths')
    if sha256_file(path) != spec['sha256']:
        raise ValueError('Input bytes differ from frozen manifest')
    return [json.loads(x) for x in path.open() if x.strip()]


def epoch_order(n, seed, epoch):
    # Accelerate SeedableRandomSampler: generator.manual_seed(initial_seed+epoch).
    import torch
    return torch.randperm(n, generator=torch.Generator().manual_seed(seed+epoch)).tolist()


def cosine_lr(initial, update, total):
    # HF LambdaLR starts update0 at initial LR; reaches zero after final step.
    return initial * (1 + math.cos(math.pi * update / total)) / 2


def load_renderer(request):
    from transformers import AutoTokenizer
    from tinker_cookbook import renderers, hyperparam_utils
    asset = request['asset']; root = Path(asset['path'])
    if root.is_absolute():
        raise ValueError('T-2: use a repository-relative tokenizer asset path')
    for f in asset['files']:
        if sha256_file(root/f['path']) != f['sha256']:
            raise ValueError('Tokenizer/config asset changed')
    tokenizer = AutoTokenizer.from_pretrained(root, local_files_only=True)
    renderer = renderers.get_renderer(RENDERER, tokenizer)
    lr = hyperparam_utils.get_lr(request['model'], is_lora=True)
    if lr != request['learning_rate']:
        raise ValueError('Cookbook learning rate changed')
    for token in ('<|im_start|>', '<|im_end|>', '<think>', '</think>'):
        ids = tokenizer.encode(token, add_special_tokens=False)
        if len(ids) != 1 or tokenizer.decode(ids) != token:
            raise ValueError('Missing special token: '+token)
    return tokenizer, renderer


def rendered_datum(row, tokenizer, renderer):
    from tinker_cookbook import renderers
    from tinker_cookbook.supervised.common import datum_from_model_input_weights
    messages = [{'role':'user', 'content':row['problem']},
                {'role':'assistant', 'content':row['solution']}]
    prompt = renderer.build_generation_prompt(messages[:1]).to_ints()
    hf_prompt = tokenizer.apply_chat_template(messages[:1], add_generation_prompt=True,
                    enable_thinking=False, return_dict=False)
    if prompt != hf_prompt:
        raise ValueError('Generation tokens differ from HF disable-thinking template')
    mi, weights = renderer.build_supervised_example(messages,
                        train_on_what=renderers.TrainOnWhat.LAST_ASSISTANT_MESSAGE)
    ids = mi.to_ints(); w = weights.tolist()
    # HF adds a newline after im_end; training and generation end at im_end.
    hf_text = tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False)
    if tokenizer.decode(ids) != hf_text.removesuffix('\n'):
        raise ValueError('Training rendering differs before final EOS')
    if ids[:len(prompt)] != prompt or any(w[:len(prompt)]) or not all(x == 1 for x in w[len(prompt):]):
        raise ValueError('Prompt mask or assistant response boundary changed')
    if ids[-1] != tokenizer.convert_tokens_to_ids('<|im_end|>') or w[-1] != 1:
        raise ValueError('Assistant end token must be scored')
    if len(ids) > 4096:
        raise ValueError('Overlength training row; never truncate')
    datum = datum_from_model_input_weights(mi, weights, max_length=None, reduction='none')
    return datum, {'input_token_ids':ids, 'loss_weights':w, 'prompt_tokens':len(prompt),
                   'target_tokens':int(sum(w)), 'rendered_text':tokenizer.decode(ids),
                   'generation_parity':True, 'supervised_parity_through_im_end':True}


def normalize_batch(datums):
    import tinker
    count = sum(sum(d.loss_fn_inputs['weights'].data) for d in datums)
    if count <= 0: raise ValueError('Empty response mask')
    result=[]
    for d in datums:
        inputs=dict(d.loss_fn_inputs); w=inputs['weights']
        inputs['weights']=tinker.TensorData(data=[x/count for x in w.data],dtype='float32',shape=w.shape)
        result.append(tinker.Datum(model_input=d.model_input,loss_fn_inputs=inputs))
    return result, count


def generation_messages(row):
    if row.get('messages'):
        return row['messages']
    # Reject an already wrapped problem by its instruction prefix;
    # frozen conversation messages are used directly above.
    if row['problem'].startswith(PROMPTS['omi2'].split('\\', 1)[0]):
        raise ValueError('T-1: already wrapped problem; use the frozen C7 conversation file')
    return [{'role':'user','content':prompt_text(row['problem'],'omi2')}]


def generate(client, tokenizer, renderer, rows, input_spec, output, n=1, temperature=0.0, seed=17,
             concurrency=32):
    import tinker
    if not isinstance(concurrency, int) or not 1 <= concurrency <= 64:
        raise ValueError('Sampling concurrency must be between1and64')
    output.mkdir(exist_ok=False)
    cfg={'model':client.model_path if getattr(client,'model_path',None) else 'tinker_lora',
         'protocol':'omi2','task':input_spec['task'],'n':n,'temperature':temperature,
         'top_p':1.0,'top_k':-1,'max_tokens':4096,'max_model_len':8192,'seed':seed}
    write_json(output/'MANIFEST.json',{'config':cfg,'input_sha256':input_spec['sha256'],
        'track':'tinker_lora','renderer':RENDERER,'stop_sequences':renderer.get_stop_sequences(),
        'sampling_policy':'One SDK sample per call; seed=seed+question_index*n+draw_index'})
    usage={'prefill_tokens_uncached_upper':0,'completion_tokens':0,'prompt_cache_hit_tokens':0}
    def one(item):
        i,row,j=item
        messages=generation_messages(row)
        prompt=renderer.build_generation_prompt(messages)
        hf=tokenizer.apply_chat_template(messages,add_generation_prompt=True,enable_thinking=False,return_dict=False)
        if prompt.to_ints()!=hf or prompt.length+4096>8192:raise ValueError('Generation prefix/context mismatch')
        draw_seed=seed+i*n+j
        response=client.sample(prompt,num_samples=1,sampling_params=tinker.SamplingParams(
            max_tokens=4096,temperature=temperature,top_p=1,top_k=-1,seed=draw_seed,
            stop=renderer.get_stop_sequences())).result()
        if len(response.sequences)!=1:raise ValueError('Missing samples')
        records=[]
        for seq in response.sequences:
            if seq.stop_reason not in ('length','stop'):raise ValueError('Unknown termination')
            tokens=seq.tokens
            records.append({'id':row['id'],'draw':j,'text':tokenizer.decode(tokens,skip_special_tokens=False),
                'token_ids':tokens,'prompt_token_ids':prompt.to_ints(),'finish_reason':seq.stop_reason,
                'stop_reason':tokens[-1] if tokens and tokens[-1] in renderer.get_stop_sequences() else None,
                'tinker_stop_reason':seq.stop_reason,'stopped_on_terminator':seq.stop_reason=='stop',
                'length_capped':seq.stop_reason=='length','string_stop':False,
                'sequence_id':seq.sequence_id,'sampling_seed':draw_seed})
        return records, prompt.length, response.prompt_cache_hit_tokens
    with (output/'raw.jsonl').open('x') as f, ThreadPoolExecutor(max_workers=concurrency) as pool:
        jobs=((i,row,j) for i,row in enumerate(rows) for j in range(n))
        for records,pre,cached in pool.map(one,jobs):
            usage['prefill_tokens_uncached_upper']+=pre;usage['prompt_cache_hit_tokens']+=cached
            for record in records:
                usage['completion_tokens']+=len(record['token_ids']);f.write(json.dumps(record,ensure_ascii=False)+'\n')
            f.flush()
    write_json(output/'GENERATION_COMPLETE.json',{'requests':len(rows),'draws':len(rows)*n,
               'sdk_sample_calls':len(rows)*n,
               'raw_sha256':sha256_file(output/'raw.jsonl')})
    write_json(output/'USAGE.json',usage)
    return usage


def run(request, output):
    import tinker
    from tinker_cookbook.supervised.common import compute_mean_nll
    mode=request['mode'];smoke=mode=='smoke'
    if request['model'] not in MODELS or request['seed'] not in (17,29):raise ValueError('Unregistered model/seed')
    if not request['forecast']['admitted'] or (smoke and request['forecast']['all_three_models_upper_usd']>5):
        raise ValueError('Prospective budget admission is required')
    if not smoke and not re.fullmatch('[a-f0-9]{40}',request.get('accepted_review_commit','')):
        raise ValueError('Formal Tinker jobs await the combined Claude review')
    if sha256_file(Path(__file__))!=request['source_sha256']:raise ValueError('Runner source changed')
    tokenizer,renderer=load_renderer(request)
    output.mkdir(parents=True,exist_ok=False);write_json(output/'REQUEST.json',request)
    write_json(output/'VERSIONS.json',{p:importlib.metadata.version(p) for p in ['tinker','tinker-cookbook','torch','transformers']})
    usage={'training_input_tokens':0,'sampling':None};start=time.monotonic()
    service=tinker.ServiceClient(display_name=request['run_id'])
    try:
        if mode in ('smoke','train','nll'):
            rows=read_rows(request['dataset']);datums=[];rendered=[]
            for row in rows:
                d,e=rendered_datum(row,tokenizer,renderer);datums.append(d);rendered.append(e)
            write_json(output/'RENDER_SAMPLES.json',[dict(rows[i],**rendered[i]) for i in range(min(3,len(rows)))])
            client=service.create_lora_training_client(base_model=request['model'],rank=32,seed=request['seed'],
                train_mlp=True,train_attn=True,train_unembed=True).result()
            write_json(output/'SERVER_MODEL_INFO.json',client.get_info().model_dump(mode='json'))
            if mode=='nll':
                if len(rows)!=1000 or len({r['parent_id'] for r in rows})!=500:raise ValueError('C7 dose mismatch')
                records=[]
                for begin in range(0,1000,8):
                    batch=datums[begin:begin+8];res=client.forward(batch,loss_fn='cross_entropy').result()
                    for j,(d,out) in enumerate(zip(batch,res.loss_fn_outputs,strict=True)):
                        weights=d.loss_fn_inputs['weights'].data;lp=out['logprobs'].data;row=rows[begin+j]
                        records.append({'parent_id':row['parent_id'],'solution_hash':row['solution_hash'],
                            'solution_chars':len(row['solution']),'target_tokens':int(sum(weights)),
                            'nll_sum':-sum(a*b for a,b in zip(weights,lp,strict=True))})
                    usage['training_input_tokens']+=sum(d.model_input.length for d in batch)
                from .capability_nll import aggregate_nll
                write_json(output/'NLL_RECORDS.json',records);write_json(output/'NLL_SUMMARY.json',aggregate_nll(records))
            else:
                cell=request['cell'];dose=grid_dose(cell)
                if len(rows)!=dose['distinct_rows'] or (smoke and cell!='L'):raise ValueError('Grid dose mismatch')
                total=dose['expected_updates'];steps=20 if smoke else total
                order=[i for epoch in range(CELLS[cell][2]) for i in epoch_order(len(rows),request['seed'],epoch)]
                write_json(output/'ROW_ORDER.json',order)
                with (output/'train_loss.jsonl').open('x') as f:
                    for step in range(steps):
                        indices=order[step*8:(step+1)*8];original=[datums[i] for i in indices]
                        batch,count=normalize_batch(original)
                        lr=cosine_lr(request['learning_rate'],step,total)
                        fw=client.forward_backward(batch,loss_fn='cross_entropy')
                        opt=client.optim_step(tinker.AdamParams(learning_rate=lr,beta1=.9,beta2=.999,
                             eps=1e-8,weight_decay=0,grad_clip_norm=1.0))
                        result=fw.result();optim=opt.result()
                        nll=compute_mean_nll([x['logprobs'] for x in result.loss_fn_outputs],
                                             [d.loss_fn_inputs['weights'] for d in batch])
                        usage['training_input_tokens']+=sum(d.model_input.length for d in batch)
                        rec={'step':step+1,'learning_rate':lr,'loss':nll,'target_tokens':count,
                             'row_indices':indices,'forward_metrics':result.metrics,'optim_metrics':optim.metrics}
                        f.write(json.dumps(rec)+'\n');f.flush();print(json.dumps({'step':step+1,'loss':nll}),flush=True)
                if not smoke:
                    state=client.save_state('final',ttl_seconds=60*86400).result()
                    write_json(output/'STATE.json',state.model_dump(mode='json'))
                saved=client.save_weights_for_sampler('smoke20' if smoke else 'final',ttl_seconds=(7 if smoke else 60)*86400).result()
                write_json(output/'SAMPLER.json',saved.model_dump(mode='json'))
                if smoke:
                    tests=read_rows(request['evaluation'])
                    if len(tests)!=20:raise ValueError('T-smoke requires exactly20 questions')
                    sampler=service.create_sampling_client(model_path=saved.path).result()
                    usage['sampling']=generate(sampler,tokenizer,renderer,tests,request['evaluation'],output/'generation',
                                               concurrency=request.get('sampling_concurrency',32))
        elif mode=='generate':
            tests=read_rows(request['evaluation']);n=request['n'];temperature=.7 if n==8 else 0.0
            if n not in (1,8) or (n==8 and len(tests)!=500):raise ValueError('Unregistered evaluation dose')
            kwargs={'model_path':request['sampler_path']} if request.get('sampler_path') else {'base_model':request['model']}
            sampler=service.create_sampling_client(**kwargs).result()
            usage['sampling']=generate(sampler,tokenizer,renderer,tests,request['evaluation'],output/'generation',n,temperature,request['seed'],
                                       request.get('sampling_concurrency',32))
        else:raise ValueError('Unknown mode')
        prices=request['prices_per_million'];cost=usage['training_input_tokens']*prices['train']/1e6
        if usage['sampling']:
            cost+=(usage['sampling']['prefill_tokens_uncached_upper']*prices['prefill']+usage['sampling']['completion_tokens']*prices['sample'])/1e6
        write_json(output/'USAGE.json',dict(usage,upper_token_cost_usd=cost,includes_cache_discount=False,storage_not_in_token_cost=True))
        write_json(output/'COMPLETE.json',{'success':True,'seconds':time.monotonic()-start,'smoke_is_not_scientific_result':smoke})
        service.close(status='success').result()
    except BaseException:
        write_json(output/'PARTIAL_USAGE.json',usage)
        service.close(status='errored').result();raise


def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not os.environ.get('TINKER_API_KEY'):raise ValueError('Load private API key into environment without printing')
    run(json.loads(a.request.read_text()),a.output)


if __name__=='__main__':main()
