"""Prepared native T1.5 missing-attempt loader and saved-verdict C2 adapter.

Full C2 source/input/numeric review and concrete finite queue remain mandatory.
Only new outputs are transported/scored; original T72/T15 verdicts stay frozen.
"""
from experiments.p011.c2_generation_evidence import checked_plan
from experiments.p011.b_generation_loader import checked_assets,transport_reader
from experiments.p011.c2_generation_window import after_window
from experiments.p010.teacher_contract import SYSTEM
from experiments.p010.dataset_selection import usable
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs,actual_engine
from experiments.sft_allocation_midpoint.common import digest


def check_native_prompts(tokenizer,pack):
    rows=checked_plan(pack['plan']);parents=pack['plan']['window_parents']
    if set(pack)!= {'plan','source','prompts'} or set(pack['source'])!=set(parents) or set(pack['prompts'])!=set(parents):
        raise ValueError('Exact gold-free admitted window pack required')
    for pid in parents:
        if set(pack['source'][pid])!={'problem'}:raise ValueError('Only question text may enter GPU pack')
        native=tokenizer.apply_chat_template([{'role':'system','content':SYSTEM},
            {'role':'user','content':pack['source'][pid]['problem']}],tokenize=True,add_generation_prompt=True)
        if native!=pack['prompts'][pid]:raise ValueError('Original native prompt mismatch; no replacement')
    if any(r['request']['prompt_token_ids']!=pack['prompts'][r['request']['problem_id']] for r in rows):
        raise ValueError('Saved request prompt differs')


def load(pack,assets):
    import torch
    from transformers import AutoTokenizer
    from vllm import LLM,SamplingParams
    if (torch.cuda.device_count()!=1 or 'H100' not in torch.cuda.get_device_name(0)
            or torch.cuda.get_device_properties(0).total_memory<75*1024**3):
        raise ValueError('Original single H10080GB required')
    cfg=checked_assets(assets)
    tok=AutoTokenizer.from_pretrained(assets['remote_path'],local_files_only=True)
    check_native_prompts(tok,pack)
    for row in pack['plan']['new_requests']:SamplingParams(**row['sampling'])
    kwargs=engine_kwargs();llm=LLM(model=assets['remote_path'],tokenizer=assets['remote_path'],**kwargs)
    actual=actual_engine(llm.llm_engine.vllm_config)
    if llm.llm_engine.vllm_config.parallel_config.tensor_parallel_size!=1:
        raise ValueError('Original single-GPU engine required')
    return llm,SamplingParams,transport_reader(tok,cfg['vocab_size']),{
        'model':assets,'engine':actual,'requested':kwargs,
        'native_prompts_checked':len(pack['plan']['window_parents']),
        'new_training':0,'old_outputs_generated_or_scored':0}


def score_rows(plan,gold,raw,transports):
    rows=checked_plan(plan)
    if len(raw)!=len(rows) or len(transports)!=len(rows):raise ValueError('All new window raw outputs required')
    lookup={g['problem_id']:g for g in gold}
    if len(lookup)!=len(gold) or set(lookup)!=set(plan['window_parents']):
        raise ValueError('Exact supported original gold projection required')
    output=[]
    for row,x,t in zip(rows,raw,transports):
        req=row['request'];pid=req['problem_id'];g=lookup[pid]
        if (x['candidate_id']!=req['candidate_id'] or x['problem_id']!=pid
                or x['prompt_token_ids']!=req['prompt_token_ids'] or x['sampling']!=row['sampling']
                or t['raw_record_sha256']!=digest(x) or t['answer_text']!=t['stop']['answer_segment']
                or not isinstance(g['gold'],str) or not g['gold']):
            raise ValueError('New raw/transport/original-gold binding differs')
        output.append({'id':'p011_c2_t08/'+req['candidate_id'],'candidate_id':req['candidate_id'],
            'problem_id':pid,'attempt':req['attempt'],'gold':g['gold'],
            'answer_segment':t['answer_text'],'stop_reason':t['stop']['stop_reason'],
            'original_gold_row_sha256':g['original_source_row_sha256'],
            'raw_record_sha256':digest(x),'decoded_record_sha256':digest(t)})
    return output


def selected_records(plan,gold,raw,transports,scored,ordered_e1d,t72,old_t15,s1):
    rows=score_rows(plan,gold,raw,transports)
    if ([x['id'] for x in scored]!=[r['id'] for r in rows]
            or any(type(x.get('score',{}).get('correct')) is not bool for x in scored)):
        raise ValueError('Exact complete new Boolean scores required; unknown is not failure')
    records={}
    for row,t,s in zip(rows,transports,scored):
        item={'candidate_id':row['candidate_id'],'problem_id':row['problem_id'],
            'attempt':row['attempt'],'answer_text':row['answer_segment'],'stop':t['stop'],
            'transport':t['transport'],'score':s,'gold_supported':True,
            'raw_record_sha256':row['raw_record_sha256'],'decoded_record_sha256':row['decoded_record_sha256']}
        item['usable']=usable(item);records[item['candidate_id']]=item
    return records,after_window(plan,ordered_e1d,t72,old_t15,records,s1)
