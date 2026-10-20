"""Independent child endpoint evidence; original training proof is reused, not loaded."""
from collections import Counter
from pathlib import Path
import math
from analyses.completion_contract import first_stop, completion_score
from experiments.p010.common import read, dump, sha, digest
from experiments.p010.e4_endpoint_contract import sampling, forecast, endpoint_rows
from experiments.learning_regime_p009.high_throughput_v1 import validate_observed_engine

GOLD_SHA256='e8e85dd16771c7f3121b061afdb7d9d90ceadb2580137d108b66abf51cb248b3'


def record_keys(run):
    if run not in ('e4_s17_n400','e4_s17_n3200'):raise ValueError('Original E4 cells only')
    child='e4_endpoint_only/'+run;parent='e4/'+run
    return sorted([child+'/claim',child+'/terminal',parent+'/claim',parent+'/terminal',parent+'/endpoint_only_successor']+
        [prefix+'/'+kind+f'/{i:04d}' for prefix in (parent,child) for kind in ('eval','eval_done') for i in range(0,1319,256)])


def decode(row,item,tokenizer,mapped,special,vocab_size):
    if (item.get('problem_id')!=row['problem_id'] or item.get('candidate_id') is not None
            or item.get('source_row_sha256') is not None or item.get('prompt_token_ids')!=row['input_ids']
            or item.get('sampling')!=sampling() or item.get('output_count')!=1
            or not isinstance(item.get('backend_text'),str)):
        raise ValueError('Original OLMo endpoint identity differs')
    ids=item['token_ids']
    if (not ids or len(ids)>512 or any(type(t) is not int or not 0<=t<vocab_size for t in ids)
            or set(ids)-mapped):raise ValueError('Unknown token is not a scored zero')
    positions=[i for i,t in enumerate(ids) if t==100257]
    if positions:
        if positions!=[len(ids)-1]:raise ValueError('Interior or repeated native EOS')
        if item['finish_reason']=='stop':
            if item['stop_reason'] not in (None,100257):raise ValueError('Foreign stop token')
        elif not (len(ids)==512 and item['finish_reason']=='length' and item['stop_reason'] is None):
            raise ValueError('Only actual native EOS at exact cap permits length metadata')
    elif len(ids)!=512 or item['finish_reason']!='length' or item['stop_reason'] is not None:
        raise ValueError('Unconfirmed short stream cannot be scored')
    return first_stop(ids,lambda x:tokenizer.decode(x,skip_special_tokens=False,
        clean_up_tokenization_spaces=False),100257,512,special)


def verify_endpoint(root,wrapper,ledger,run,prior,tokenizer,gold,vocab_size,out):
    root=Path(root);rows=endpoint_rows(wrapper);prefix='e4_endpoint_only/'+run
    if [x['problem_id'] for x in rows]!=[f'gsm8k/test/{i:05d}' for i in range(1319)] or set(gold)!={x['problem_id'] for x in rows}:
        raise ValueError('Original complete ordered GSM1319 roster required')
    validate_observed_engine(read(root/'ENGINE.json'))
    result=read(root/'RESULT.json');times=result['eval_batch_seconds']
    if (result['run']!=run or result['raw_endpoint_count']!=1319 or result['new_training_updates']!=0
            or result['original_training_updates']!=1024 or result['original_targets']!=2097148
            or result['original_failed_parent_remains_failed'] is not True or len(times)!=6
            or any(not math.isfinite(x) or x<=0 for x in times)):
        raise ValueError('Original child scope or complete measured batches differ')
    expected={f'{i:04d}.json' for i in range(0,1319,256)}
    for name in ('raw','eval_intents','eval_acks','eval_forecasts'):
        if {p.name for p in (root/name).glob('*.json')}!=expected:raise ValueError('Missing/extra original batch')
    before=read(root/'BEFORE_MODEL_FORECAST.json')
    if before!=forecast(before['elapsed_seconds'],0,[],prior):raise ValueError('Original pre-model forecast differs')
    mapped=set(tokenizer.get_vocab().values());special=tuple(tokenizer.all_special_ids)
    decoded=[];stops=Counter();backend=Counter()
    for index,offset in enumerate(range(0,1319,256)):
        unit=f'{offset:04d}';part=rows[offset:offset+256];raw=read(root/'raw'/(unit+'.json'))
        intent=read(root/'eval_intents'/(unit+'.json'));ack=read(root/'eval_acks'/(unit+'.json'))
        f=read(root/'eval_forecasts'/(unit+'.json'))
        if (intent['rows']!=part or intent['sampling']!=[sampling() for _ in part] or len(raw)!=len(part)
                or ledger[prefix+'/eval/'+unit]!=intent or ledger[prefix+'/eval_done/'+unit]!=ack
                or ack!=dict(count=len(part),seconds=times[index],raw_sha256=digest(raw))
                or f!=forecast(f['elapsed_seconds'],index,times[:index],prior)):
            raise ValueError('Original child request/ack/raw/forecast binding differs')
        batch=[];raw_file_sha256=sha(root/'raw'/(unit+'.json'))
        for row,item in zip(part,raw):
            stop=decode(row,item,tokenizer,mapped,special,vocab_size)
            score=completion_score(gold[row['problem_id']],stop)
            entry=dict(problem_id=row['problem_id'],raw_file='raw/'+unit+'.json',raw_file_sha256=raw_file_sha256,
                raw_record_sha256=digest(item),gold_row_sha256=digest(gold[row['problem_id']]),stop=stop,score=score,
                backend_finish_reason=item['finish_reason'],backend_stop_reason=item['stop_reason'])
            batch.append(entry);stops[stop['stop_reason']]+=1;backend[item['finish_reason']]+=1
        dump(Path(out)/'confirmed_batches'/(unit+'.json'),batch);decoded.extend(batch)
    return dict(decoded=decoded,total=1319,correct=sum(x['score']['task_answer_correct'] for x in decoded),
        logical_stops=dict(stops),backend_stops=dict(backend),technical_unknown=0,
        new_training_updates=0,repeated_training_state_loads=0,independent_A3_pending=True)
