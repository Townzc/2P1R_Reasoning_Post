"""Finite teacher lifetime. Raw bytes persist before CPU selection/scoring."""
from pathlib import Path
import math
import time
from experiments.p010.common import dump,read,sha,digest,manifest,verify,utc,MODELS
from experiments.p010.teacher_contract import SYSTEM,canonical_request,sampling,validate_queue,first_usable
from experiments.p010.teacher_repair_contract import SLOTS,bounded_forecast
from experiments.p010.teacher_transport import completion


def run(model,inputs,assets,out,store,volume,started,deadline,prefix=None):
    import torch
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs,actual_engine
    from experiments.learning_regime_p009.math_scoring import last_box
    from experiments.learning_regime_p009.math_scoring_pool import SymbolicPool
    from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
    inputs=Path(inputs);out=Path(out);slot=SLOTS[model]
    if torch.cuda.device_count()!=slot['gpus'] or any('H100' not in torch.cuda.get_device_name(i) or torch.cuda.get_device_properties(i).total_memory<75*1024**3 for i in range(slot['gpus'])):
        raise ValueError('Actual GPU allocation differs')
    if (assets['model_id'],assets['revision'])!=MODELS[model]:raise ValueError('Pinned teacher identity differs')
    verify(assets['remote_path'],assets['files'])
    tok=AutoTokenizer.from_pretrained(assets['remote_path'],local_files_only=True)
    mapped_ids=set(tok.get_vocab().values())
    model_vocab_size=read(Path(assets['remote_path'])/'config.json')['vocab_size']
    special_ids=set(tok.all_special_ids)
    alltrain=read(inputs/'MATH_SOURCE.json');train={r['problem_id']:r for r in alltrain}
    roster=read(inputs/'MATH_ROSTERS.json');queue=read(inputs/f'{model}_fixed_requests.json')
    validate_queue(queue,model)
    prompts={}
    for row in queue:
        pid=row['problem_id']
        if pid not in prompts:
            prompts[pid]=tok.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':train[pid]['problem']}],tokenize=True,add_generation_prompt=True)
        if prompts[pid]!=row['prompt_token_ids']:
            raise ValueError('Native teacher chat serialization differs from frozen P009')
    kwargs=engine_kwargs();kwargs['tensor_parallel_size']=slot['gpus']
    for row in queue:SamplingParams(**sampling(row))
    llm=LLM(model=assets['remote_path'],tokenizer=assets['remote_path'],**kwargs)
    actual=actual_engine(llm.llm_engine.vllm_config)
    if llm.llm_engine.vllm_config.parallel_config.tensor_parallel_size!=slot['gpus']:
        raise ValueError('Actual TP differs')
    dump(out/'ENGINE.json',dict(actual=actual,requested=kwargs,model=assets,
        source_first_prompt_check=len(prompts),entry_utc=utc(),new_training=0))
    volume.commit()
    records={};done=set();full_times=[];batch_index=0;inherited=0
    if prefix:
        full_times.append(prefix['failed_interval_proxy_seconds'])
    basekey='teacher/'+('t7_remainder_r1' if model=='t7' else model)
    def check():
        if time.time()>=deadline-15:raise TimeoutError('Original worker deadline')
        if store.get(basekey+'/claim') is None:raise RuntimeError('Missing original once-only claim')
    def request(pid,attempt):
        if pid not in prompts:
            prompts[pid]=tok.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':train[pid]['problem']}],tokenize=True,add_generation_prompt=True)
        return canonical_request(pid,attempt,model,prompts[pid])
    with SymbolicPool() as pool:
        def batch(rows,phase,remaining_estimate,reused_raw=None):
            nonlocal batch_index
            check();validate_queue(rows,model)
            if not rows or any(r['candidate_id'] in done for r in rows):raise ValueError('No output may be regenerated')
            name=f'{batch_index:05d}';batch_index+=1
            # First20 smoke and first256 timing batch are bounded paid work from
            # the already authorized roster, not extra scientific requests.
            forecast=None
            if full_times and reused_raw is None:
                forecast=bounded_forecast(model,time.time()-started,full_times,math.ceil(remaining_estimate/256))
            intent=dict(rows=rows,phase=phase,forecast=forecast,epoch=time.time(),
                bounded_measurement_without_prior_full_batch=not full_times,
                inherited_raw_no_generation=reused_raw is not None)
            if not store.put(basekey+'/batch/'+name,intent,skip_if_exists=True):raise RuntimeError('Batch already reserved')
            dump(out/'intents'/f'{name}.json',intent);volume.commit()
            t=time.monotonic();params=[sampling(r) for r in rows]
            if reused_raw is None:
                results=llm.generate([{'prompt_token_ids':r['prompt_token_ids']} for r in rows],
                    [SamplingParams(**p) for p in params],use_tqdm=False)
                raw=returned_records(rows,params,results)
            else:
                raw=reused_raw
            dump(out/'raw'/f'{name}.json',raw);volume.commit()
            if len(raw)!=len(rows):raise ValueError('Raw cardinality differs; preserved')
            scoring=[];unsupported=[];derived=[]
            for r,x in zip(rows,raw):
                if x['output_count']!=1 or x['prompt_token_ids']!=r['prompt_token_ids']:
                    raise ValueError('Transport identity/shape differs; raw preserved')
                logical,transport=completion(x,tok,mapped_ids,model_vocab_size,special_ids)
                text=logical['answer_segment']
                gold=last_box(train[r['problem_id']]['solution'])['answer']
                d=dict(candidate_id=r['candidate_id'],problem_id=r['problem_id'],attempt=r['attempt'],
                    raw_file=f'raw/{name}.json',raw_record_sha256=digest(x),answer_text=text,
                    stop=logical,transport=transport,gold_supported=bool(gold))
                derived.append(d)
                if gold:scoring.append(dict(id=r['candidate_id'],gold=gold,answer_segment=text,stop_reason=logical['stop_reason']))
                else:unsupported.append(r['candidate_id'])
            # Frozen symbolic engine on CPU only; no test/model selection or
            # re-scoring of P009 outputs. Failed/time-out pairs stay cached.
            verdict=pool.score_rows(scoring)
            dump(out/'scores'/f'{name}.json',verdict)
            scoremap={x['id']:x for x in verdict['rows']}
            for r,d in zip(rows,derived):
                sc=scoremap.get(r['candidate_id'])
                d['score']=sc;d['usable']=bool(sc and sc['score']['correct'] and sc['score']['parsed'] and d['stop']['stop_reason']=='native_eos')
                records[r['candidate_id']]=d;done.add(r['candidate_id'])
            dump(out/'derived'/f'{name}.json',derived)
            seconds=time.monotonic()-t
            if len(rows)==256 and reused_raw is None:full_times.append(seconds)
            ack=dict(count=len(rows),seconds=seconds,raw_sha256=sha(out/'raw'/f'{name}.json'),
                scores_sha256=sha(out/'scores'/f'{name}.json'),unsupported_gold=unsupported,
                generated_total=len(done)-inherited,inherited_raw_no_generation=reused_raw is not None)
            dump(out/'acks'/f'{name}.json',ack);volume.commit()
            if not store.put(basekey+'/done/'+name,ack,skip_if_exists=True):raise RuntimeError('Duplicate acknowledgment')
            print({'model':model,'completed':len(done),'batch_seconds':seconds},flush=True)
            check()
        if prefix:
            if model!='t7' or prefix['rows']!=queue[:256] or len(prefix['raw'])!=256:
                raise ValueError('Exact original first256 only')
            inherited=256
            batch(prefix['rows'],'inherited_first256',len(queue),reused_raw=prefix['raw'])
            if sha(out/'raw/00000.json')!=prefix['raw_file_sha256']:
                raise ValueError('Inherited raw bytes must remain identical')
        if model=='t72':
            byid={r['candidate_id']:r for r in queue}
            smoke=[byid[pid+'::attempt01'] for pid in roster['smoke20']]
            batch(smoke,'selfhost_smoke20',len(queue)+4000)
            values=[records[r['candidate_id']] for r in smoke]
            smokeproof=dict(correct=sum(r['usable'] for r in values),n=20,
                contains_box=sum(bool(r['score'] and r['score']['score'].get('box_extracted')) for r in values),
                lengths=[r['stop']['retained_tokens'] for r in values],provider='Modal selfhost',
                dtype='bfloat16',quantization=None,not_Fireworks_API_test=True)
            dump(out/'SMOKE20.json',smokeproof);volume.commit()
            if smokeproof['correct']<14:raise ValueError('Selfhost smoke quality below14/20; no bulk')
        queue=[r for r in queue if r['candidate_id'] not in done]
        # Generate every one of16 authorized attempts for the400 questions;
        # never prune this supply using observed correctness.
        for start in range(0,len(queue),256):
            batch(queue[start:start+256],'fixed_supply',len(queue)-start+(4000 if model=='t72' else 400))
        if model!='t15':
            outside=[p for p in roster['s1']['3200'] if p not in set(roster['s1']['400'])]
            for attempt in range(2,5):
                pending=[request(pid,attempt) for pid in outside if not first_usable(pid,records)]
                for start in range(0,len(pending),256):batch(pending[start:start+256],'K1_conditional_retry',len(pending)-start+(4000 if model=='t72' else 0))
        if model=='t72':
            accepted=[];cursor=0
            while len(accepted)<3200:
                check()
                # At most the still needed count: no extra E1d questions after
                # the sequential3200th acceptance. Previously generated answers
                # are reused by canonical request ID, not resampled.
                part=roster['e1d_order'][cursor:cursor+min(256,3200-len(accepted))]
                if not part:raise ValueError('E1d exhausted train roster before3200')
                cursor+=len(part)
                for attempt in range(1,5):
                    pending=[request(pid,attempt) for pid in part if not first_usable(pid,records) and f'{pid}::attempt{attempt:02d}' not in done]
                    if pending:batch(pending,'E1d_conditional',3200-len(accepted))
                accepted.extend(pid for pid in part if first_usable(pid,records))
            dump(out/'E1D_ACCEPTED.json',dict(problem_ids=accepted,examined_prefix_count=cursor,
                source_order_sha256=digest(roster['e1d_order']),selection='first usable within four; no T1.5 correctness filter'))
        dump(out/'RECORD_INDEX.json',records)
        dump(out/'PAIR_CACHE.json',dict(attempts=pool.attempts,startups=pool.startups))
        result=dict(model=model,completed_unique_new_outputs=len(done)-inherited,inherited_raw_outputs=inherited,counts_by_phase='intents/',
            scientific_training_updates=0,all_raw_saved=True,seconds=time.time()-started,
            full_batch_seconds=full_times,frozen_scorer=sha(Path(__file__).resolve().parents[1]/'learning_regime_p009/math_scoring.py'))
        dump(out/'RESULT.json',result);volume.commit();return result
