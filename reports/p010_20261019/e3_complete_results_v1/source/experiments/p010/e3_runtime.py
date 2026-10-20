"""All original3200 E3 outputs once; no in-worker symbolic scoring or selection."""
from pathlib import Path
import time
from experiments.p010.common import read, dump, sha, digest, verify, MODELS, utc
from experiments.p010.teacher_contract import SYSTEM
from experiments.p010.e3_contract import KEY, HARD_SECONDS, TEMPERATURES, check_rosters, forecast


def generate(inputs, out, model, claim, started, deadline, timing, charged_G, store, volume):
    import torch
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine
    from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
    from experiments.p010.teacher_transport import completion
    inputs, out = Path(inputs), Path(out)
    if (torch.cuda.device_count() != 4 or any('H100' not in torch.cuda.get_device_name(i)
            or torch.cuda.get_device_properties(i).total_memory < 75*1024**3 for i in range(4))
            or (model['model_id'],model['revision']) != MODELS['t72']
            or abs(deadline-started-HARD_SECONDS) > .001 or store.get(KEY+'/claim') != claim):
        raise ValueError('Exact original T72 TP4/H100 and once-only claim required')
    groups={label:read(inputs/(label+'_requests.json')) for label,_ in TEMPERATURES}
    check_rosters(read(inputs/'ROSTER.json'),groups)
    observed=timing['original_full_batch_seconds'];setup=timing['observed_pre_first_batch_seconds']
    dump(out/'BEFORE_MODEL_FORECAST.json',forecast(time.time()-started,0,[],observed,setup,model_loaded=False,charged_G=charged_G))
    volume.commit()
    verify(model['remote_path'],model['files'])
    tok=AutoTokenizer.from_pretrained(model['remote_path'],local_files_only=True)
    mapped=set(tok.get_vocab().values());special=set(tok.all_special_ids)
    model_vocab=read(Path(model['remote_path'])/'config.json')['vocab_size']
    texts=read(inputs/'PROMPT_TEXTS.json')
    prompts={x['problem_id']:x for x in texts}
    if len(texts)!=200 or len(prompts)!=200:
        raise ValueError('Original200 prompt text records required')
    for pid in read(inputs/'ROSTER.json')['problem_ids']:
        item=prompts[pid]
        expected=tok.apply_chat_template([{'role':'system','content':SYSTEM},
            {'role':'user','content':item['problem']}],tokenize=True,add_generation_prompt=True)
        if expected!=item['prompt_token_ids']:
            raise ValueError('Actual teacher native chat does not match saved prompt')
    constructed={label:[SamplingParams(**r['sampling']) for r in rows] for label,rows in groups.items()}
    for rows in groups.values():
        if any(r['prompt_token_ids']!=prompts[r['problem_id']]['prompt_token_ids'] for r in rows):
            raise ValueError('Generation roster differs from actual verified prompt')
    kwargs=engine_kwargs();kwargs['tensor_parallel_size']=4
    llm=LLM(model=model['remote_path'],tokenizer=model['remote_path'],**kwargs)
    actual=actual_engine(llm.llm_engine.vllm_config)
    if llm.llm_engine.vllm_config.parallel_config.tensor_parallel_size!=4:
        raise ValueError('Actual tensor parallel setting differs')
    dump(out/'ENGINE.json',dict(actual=actual,requested=kwargs,model=model,
        prompt_texts_verified=200,new_training_updates=0));volume.commit()
    times=[];counts={};total=0
    for label,_ in TEMPERATURES:
        rows=groups[label];counts[label]=0
        for first in range(0,len(rows),256):
            if store.get(KEY+'/claim')!=claim:raise ValueError('Original claim changed')
            unit=label+'/'+f'{first:04d}';part=rows[first:first+256]
            f=forecast(time.time()-started,len(times),times,observed,setup,model_loaded=True,charged_G=charged_G)
            dump(out/'forecasts'/(unit+'.json'),f)
            intent=dict(rows=part,sampling=[x['sampling'] for x in part],epoch=time.time(),temperature_label=label)
            if not store.put(KEY+'/batch/'+unit,intent,skip_if_exists=True):
                raise RuntimeError('An original temperature batch was already attempted')
            dump(out/'intents'/(unit+'.json'),intent);volume.commit();tick=time.monotonic()
            results=llm.generate([{'prompt_token_ids':x['prompt_token_ids']} for x in part],
                constructed[label][first:first+256],use_tqdm=False)
            raw=returned_records(part,intent['sampling'],results)
            dump(out/'raw'/(unit+'.json'),raw);volume.commit()
            if (len(raw)!=len(part) or any(x['candidate_id']!=r['candidate_id']
                    or x['prompt_token_ids']!=r['prompt_token_ids'] or x['output_count']!=1
                    or x['sampling']!=r['sampling'] for r,x in zip(part,raw))):
                raise ValueError('Original complete raw identity differs; bytes preserved')
            stops=[]
            for x in raw:
                logical,transport=completion(x,tok,mapped,model_vocab,special)
                stops.append(dict(candidate_id=x['candidate_id'],logical=logical,transport=transport,
                    raw_record_sha256=digest(x)))
            dump(out/'transport'/(unit+'.json'),stops)
            seconds=time.monotonic()-tick;times.append(seconds);counts[label]+=len(part);total+=len(part)
            ack=dict(count=len(part),seconds=seconds,raw_sha256=sha(out/'raw'/(unit+'.json')),
                transport_sha256=sha(out/'transport'/(unit+'.json')),generated_total=total)
            dump(out/'acks'/(unit+'.json'),ack);volume.commit()
            if not store.put(KEY+'/done/'+unit,ack,skip_if_exists=True):
                raise RuntimeError('Original batch acknowledgment exists')
    if total!=3200 or counts!={'t06':1600,'t10':1600} or len(times)!=14 or time.time()>=deadline-15:
        raise ValueError('Incomplete original scope or insufficient pack time')
    result=dict(counts=counts,new_outputs=total,new_training_updates=0,new_symbolic_scores=0,
        saved_T08_regenerated=0,batch_seconds=times,seconds_before_pack=time.time()-started,utc=utc())
    dump(out/'RESULT.json',result);volume.commit();return result
