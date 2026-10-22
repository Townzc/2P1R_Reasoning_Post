"""Owner options2+3: fixed MATH-first roster and complete-endpoint-only oracle.

AIME/AMC are deliberately omitted for this budgeted extension. Original3300
inputs remain bound; the original native decoder/scoring-row functions are
called only on complete500-question MATH endpoints. Missing is never false.
"""
from collections import Counter
import math
from pathlib import Path
from experiments.p011 import long_owner_evidence as original
from experiments.sft_allocation_midpoint.common import read,sha,digest

ORDER=(('greedy',0),('sample',0),('sample',1),('sample',2),('sample',3))
BATCHES=5


def ids_for(mode,seed):
    return {f'math500:{i:04d}:{mode}:{seed}' for i in range(500)}


def math_requests(requests):
    if len(requests)!=3300 or len({r['id'] for r in requests})!=3300:
        raise ValueError('Exact original3300 unique input roster required')
    table={r['id']:r for r in requests if r['id'].startswith('math500:')}
    expected=set().union(*(ids_for(*k) for k in ORDER))
    if set(table)!=expected:raise ValueError('Original complete five MATH endpoints required')
    return [table[f'math500:{i:04d}:{mode}:{seed}'] for mode,seed in ORDER for i in range(500)]


def complete_endpoint_ids(available_ids):
    available=set(available_ids);all_ids=set().union(*(ids_for(*k) for k in ORDER))
    if not available<=all_ids:raise ValueError('Non-MATH or foreign IDs in scoped availability')
    complete=[key for key in ORDER if ids_for(*key)<=available]
    selected=set().union(*(ids_for(*key) for key in complete)) if complete else set()
    return complete,selected


def expected_units(updates):
    return [u for u in original.expected_units('student',updates) if not u.startswith('eval_')]+[f'eval_{i:04d}' for i in range(BATCHES)]


def expected_record_keys(key,updates):
    return [key+'/claim',key+'/terminal']+[key+'/'+stage+'/'+unit for unit in expected_units(updates) for stage in ('unit','done')]


def journals(payload,key,updates,ledger):
    """Require complete training, allow missing evaluation, authenticate each ack."""
    payload=Path(payload);units=set(expected_units(updates))
    if set(ledger)!=set(expected_record_keys(key,updates)):raise ValueError('Exact scoped named-key roster required')
    required={u for u in units if not u.startswith('eval_')};result=[]
    for folder,remote in [('intents','unit'),('completed','done')]:
        names={p.stem for p in (payload/folder).glob('*.json')}
        if not required<=names or not names<=units:raise ValueError('Incomplete training or foreign endpoint journal')
        values={u:read(payload/folder/(u+'.json')) for u in names}
        for u in units:
            if values.get(u)!=ledger[key+'/'+remote+'/'+u]:raise ValueError('Original local/cloud scoped journal differs')
        result.append(values)
    attempted,done=result
    completed=[i for i in range(BATCHES) if f'eval_{i:04d}' in done]
    if completed!=list(range(len(completed))) or not set(done)<=set(attempted):
        raise ValueError('Complete endpoint batches must be an acknowledged prefix')
    return attempted,done


def endpoint(payload,requests,context,eos,tokenizer,config,attempts,done,timing,train_times):
    payload=Path(payload);ordered=math_requests(requests)
    expected_scope={'original_bound_inputs':3300,'generated_scope':2500,
        'order':'greedy500 then sample seeds0,1,2,3 each500','batch_size':512,
        'AIME24_AIME25_AMC23':'NOT_RUN_BY_OWNER_OPTION2','partial_complete_endpoints_authorized':True}
    if read(payload/'MATH_SCOPE.json')!=expected_scope:raise ValueError('Exact owner MATH scope metadata required')
    if not {p.stem for p in (payload/'raw').glob('*.json')}<={f'eval_{i:04d}' for i in range(BATCHES)}:
        raise ValueError('Unexpected raw batch outside new MATH scope')
    gpu=[{**{k:v for k,v in r.items() if k!='gold'},'request_sha256':digest(r)} for r in requests]
    original.validate_endpoint(gpu,context);gpu_order=math_requests(gpu)
    available={};raw_bindings={};complete_cycles=[];cycle_replay_complete=True
    for index in range(BATCHES):
        name=f'eval_{index:04d}';first=index*512;part=ordered[first:first+512];gpu_part=gpu_order[first:first+512]
        expected=dict(requests=gpu_part,sampling=[original.sampling(r,eos) for r in part])
        if name in attempts and attempts[name]!=expected:raise ValueError('Exact fixed MATH batch intent differs')
        if name not in done:continue
        rawfile=payload/'raw'/(name+'.json');raw=read(rawfile);rawsha=sha(rawfile);ack=done[name];seconds=ack.get('seconds')
        if (not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds<=0
                or ack!=dict(count=len(part),raw_file_sha256=rawsha,request_ids=[r['id'] for r in part],seconds=seconds)
                or len(raw)!=len(part) or [r['id'] for r in raw]!=[r['id'] for r in part]):
            raise ValueError('Complete original MATH batch acknowledgment/raw differs')
        raw_bindings[name]=rawsha
        for row,item in zip(part,raw):available[row['id']]=(row,item,name,rawsha)
        cycle_path=payload/'endpoint_cycles'/(name+'.json')
        if cycle_path.exists():
            cycle=read(cycle_path)
            if (cycle.get('batch')!=index or cycle.get('body_seconds')!=seconds
                    or not isinstance(cycle.get('seconds'),(int,float)) or not math.isfinite(cycle['seconds'])
                    or cycle['seconds']<seconds or cycle.get('volume_commits_included')!=3
                    or cycle.get('remote_unit_and_done_included') is not True):raise ValueError('Saved whole endpoint cycle differs')
            if cycle_replay_complete:
                original.replay_forecast(read(payload/'forecasts'/(name+'.json')),timing,0,BATCHES-index,train_times,complete_cycles)
                complete_cycles.append(cycle['seconds'])
        else:cycle_replay_complete=False
    complete,selected=complete_endpoint_ids(available)
    decoded={};stops=Counter()
    for request in ordered:
        if request['id'] not in selected:continue
        row,item,name,rawsha=available[request['id']]
        value=original.decode_record(row,item,eos,tokenizer,config['vocab_size'])
        value.update(raw_file='raw/'+name+'.json',raw_file_sha256=rawsha)
        decoded[row['id']]=value;stops[value['stop_reason']]+=1
    if available:
        original.replay_forecast(read(payload/'PRE_ENGINE_FORECAST.json'),timing,0,BATCHES,train_times,[])
        engine=read(payload/'ENGINE.json');constructor=read(payload/'LINUX_CONSTRUCTORS.json')
        actual=dict(max_model_len=context,enforce_eager=False,dtype='torch.bfloat16',max_num_seqs=original.ENGINE_MAX_SEQS,
            max_num_batched_tokens=8192,enable_chunked_prefill=True,enable_prefix_caching=False,gpu_memory_utilization=.8,
            compilation_level=3,cudagraph_mode='FULL_AND_PIECEWISE',cudagraph_capture_sizes=original.GRAPH_CAPTURE_SIZES.copy())
        if (engine['requested']!=original.engine_settings(context) or engine['actual']!=actual
                or constructor['count']!=3300 or constructor['before_vllm_model_allocation'] is not True
                or constructor['all_native_prompt_texts_verified'] is not True):raise ValueError('Original native model/engine constructors changed')
    scoped=[r for r in ordered if r['id'] in selected]
    return {'decoded':list(decoded.values()),'scoring_rows':original.scoring_rows(scoped,decoded),
        'outputs_decoded':len(scoped),'logical_stops':dict(stops),'technical_unknown_in_scored_scope':0,
        'complete_math_endpoints':[[m,s] for m,s in complete],
        'primary_sample4_complete':all(('sample',s) in complete for s in range(4)),
        'greedy_complete':('greedy',0) in complete,'acknowledged_raw_rows':len(available),
        'partial_endpoint_raw_rows_not_decoded_or_scored':len(available)-len(scoped),
        'raw_batch_bindings':raw_bindings,'unacknowledged_raw_files_not_decoded':[p.name for p in sorted((payload/'raw').glob('*.json')) if p.stem not in done],'endpoint_cycle_replay_complete_for_acknowledged_batches':cycle_replay_complete,
        'missing_cycle_not_replaced_by_body_time':True,'AIME24_AIME25_AMC23':'NOT_RUN_BY_OWNER_OPTION2_SCOPE; no accuracy/zero/contrast',
        'original_native_decoder_and_scoring_rows_unchanged':True,'scoped_completion_not_worker_success':True,
        'selection_only_by_complete_fixed_endpoint_not_score':True,'symbolic_scoring_performed':False}
