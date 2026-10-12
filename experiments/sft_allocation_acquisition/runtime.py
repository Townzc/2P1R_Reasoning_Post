"""One fixed 128-by-8 teacher tape; persistent intents, no retries or training."""
from collections import defaultdict
import importlib.metadata
from pathlib import Path
import time
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,verify
from .contract import roster,completion,assess,summarize,SAMPLING,SYSTEM,REVISION,messages

RATE_USD_PER_HOUR = 3.95 + 4*0.0473 + 32*0.008


def run(assets,out,journal):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    expected={'torch':'2.8.0+cu128','transformers':'4.56.2','tokenizers':'0.22.1','numpy':'2.3.2'}
    actual={x:importlib.metadata.version(x) for x in expected}
    if actual!=expected or not torch.cuda.is_available() or torch.cuda.device_count()!=1:
        raise ValueError('Runtime differs from frozen single-GPU contract')
    props=torch.cuda.get_device_properties(0)
    if 'H100' not in props.name or props.total_memory < 75*2**30:
        raise ValueError('Expected one H10080GB')
    dump(out/'environment.json',dict(versions=actual,gpu=props.name,memory_bytes=props.total_memory,
         torch_cuda=torch.version.cuda,parameter_dtype='bfloat16',attention='sdpa'))
    inputs=assets/'inputs';verify(inputs,read(inputs/'manifest.json')['files'])
    parents=[__import__('json').loads(x) for x in (inputs/'parents.jsonl').read_text().splitlines()]
    batches=roster(parents)
    if batches!=read(inputs/'batches.json'):
        raise ValueError('Frozen request roster differs')
    lookup={p['id']:p for p in parents}
    model_dir=assets/'model';started=time.monotonic()
    if read(assets/'result.json')['model_revision']!=REVISION:
        raise ValueError('Teacher revision differs')
    verify(assets,read(assets/'result.json')['files'])
    tok=AutoTokenizer.from_pretrained(model_dir,local_files_only=True,padding_side='left',trust_remote_code=False)
    tok.pad_token_id=SAMPLING['pad_token_id']
    model=AutoModelForCausalLM.from_pretrained(model_dir,local_files_only=True,trust_remote_code=False,
        torch_dtype=torch.bfloat16,attn_implementation='sdpa').to('cuda').eval()
    if model.config.max_position_embeddings!=4096 or next(model.parameters()).dtype!=torch.bfloat16:
        raise ValueError('Teacher context or precision differs')
    prompts={p['id']:tok.apply_chat_template(messages(p),tokenize=False,add_generation_prompt=True) for p in parents}
    lengths={pid:len(tok.encode(prompt,add_special_tokens=False)) for pid,prompt in prompts.items()}
    if any(n+SAMPLING['max_new_tokens']>4096 for n in lengths.values()):
        raise ValueError('Untruncated prompt would exceed context; no outcome-based backfill')
    dump(out/'prompt_manifest.json',{p:dict(sha256=__import__('hashlib').sha256(v.encode()).hexdigest(),
                                          tokens=lengths[p]) for p,v in prompts.items()})
    load_seconds=time.monotonic()-started
    journal.commit()
    seen=defaultdict(dict);usable_seen=defaultdict(dict);records=[];timings=[]
    for batch in batches:
        journal.check()
        name=batch['batch_id'];items=batch['items'];rows=[lookup[i['problem_id']] for i in items]
        packed=tok([prompts[r['id']] for r in rows],return_tensors='pt',padding=True,
                   truncation=False,add_special_tokens=False).to('cuda')
        ids=packed['input_ids'];mask=packed['attention_mask']
        intent=dict(batch=batch,sampling=SAMPLING,prompt_token_ids=ids.cpu().tolist(),
                    attention_mask=mask.cpu().tolist(),started_epoch=time.time())
        journal.begin(name,intent);journal.commit()
        torch.manual_seed(batch['seed']);torch.cuda.synchronize();tick=time.monotonic()
        with torch.inference_mode():returned=model.generate(**packed,**SAMPLING,use_cache=True)
        torch.cuda.synchronize();seconds=time.monotonic()-tick
        returned=returned.cpu().tolist();prefix=ids.cpu().tolist();width=ids.shape[1]
        if len(returned)!=len(items) or any(r[:width]!=p for r,p in zip(returned,prefix)):
            raise ValueError('Backend changed the requested roster or prompt prefix')
        raw=dict(batch_id=name,items=items,batch_output_ids=returned,
                 prompt_width=width,generation_seconds=seconds,returned_epoch=time.time())
        rawfile=out/'raw'/f'{name}.json';dump(rawfile,raw);journal.commit()
        tick=time.monotonic();scored=[]
        for parent,item,tokens in zip(rows,items,returned):
            stop=completion(tokens[width:]);text=tok.decode(stop['text_token_ids'],skip_special_tokens=False)
            judgement=assess(parent,text,stop,seen[parent['id']],usable_seen[parent['id']])
            result=dict(**item,text=text,stop=stop,**judgement,prompt_tokens=lengths[parent['id']],
                batch_id=name,batch_size=len(items),allocated_generation_seconds=seconds/len(items),
                allocation_is_batch_share_not_independent_marginal_cost=True)
            seen[parent['id']].setdefault(judgement['normalized_text_sha256'],item['candidate_id'])
            if judgement['usable']:
                usable_seen[parent['id']].setdefault(judgement['normalized_text_sha256'],item['candidate_id'])
            scored.append(result)
        score_seconds=time.monotonic()-tick
        scorefile=out/'scored'/f'{name}.json';dump(scorefile,scored)
        done=dict(candidate_ids=[r['candidate_id'] for r in scored],count=len(scored),
            raw_sha256=sha(rawfile),scored_sha256=sha(scorefile),generation_seconds=seconds,
            checker_seconds=score_seconds,output_tokens=sum(r['stop']['token_count'] for r in scored),
            usable=sum(r['usable'] for r in scored),duplicates=sum(r['duplicate_of'] is not None for r in scored))
        journal.end(name,done);journal.commit();records.extend(scored);timings.append(done)
        print(__import__('json').dumps(dict(batch=name,outputs=len(records),usable=sum(r['usable'] for r in records),
              generation_seconds=seconds)),flush=True)
    result=summarize(parents,records)
    result.update(status='completed',model_revision=REVISION,student_updates=0,model_load_and_validation_seconds=load_seconds,
        generation_seconds=sum(t['generation_seconds'] for t in timings),
        checker_seconds=sum(t['checker_seconds'] for t in timings),
        nominal_gpu_and_host_rate_usd_per_hour=RATE_USD_PER_HOUR,provider_invoice_usd=None,
        planned_attempts=1024,attempted=1024,unknown_attempts=0)
    if result['recorded_outputs']!=1024:raise ValueError('Incomplete tape')
    return result
