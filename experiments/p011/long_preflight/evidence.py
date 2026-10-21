"""Read-only full original engineering state/raw/identity verification, no score."""
from pathlib import Path
import math
from experiments.p011 import long_evidence as original,long_execution
from experiments.p011.long_preflight import subset,path
from experiments.p011.long_evaluation import sampling
from experiments.sft_allocation_midpoint.common import read,sha,digest,verify

UNITS=['update_00001','update_00002','terminal_state','terminal_model_export','eval_0000']


def engine_proof(value,job):
    requested=long_execution.engine_settings(job['context'])
    expected={'max_model_len':job['context'],'enforce_eager':False,'dtype':'torch.bfloat16',
        'max_num_seqs':256,'max_num_batched_tokens':8192,'enable_chunked_prefill':True,
        'enable_prefix_caching':False,'gpu_memory_utilization':.80,'compilation_level':3,
        'cudagraph_mode':'FULL_AND_PIECEWISE','cudagraph_capture_sizes':[1,2,4,8,16,32,64,128,256]}
    if (value.get('requested')!=requested or value.get('actual')!=expected
            or value.get('model_path')!=str(Path(path.BASE)/path.logical(job)/'model_for_vllm')):
        raise ValueError('Complete original engine geometry or exported-model path differs')
    return expected


def keys(job):
    k=path.key(job)
    return [k+'/'+x for x in ('dispatch','claim','terminal')]+[k+'/'+stage+'/'+unit for unit in UNITS for stage in ('unit','done')]


def check(root,inputs,job,identity,records,timing):
    root,inputs=Path(root),Path(inputs);k=path.key(job)
    if identity.get('engineering_preflight') is not True or identity.get('scientific_cell_result') is not False:raise ValueError('Engineering-only identity required')
    if set(records)!=set(keys(job)):raise ValueError('Exact original engineering named records required')
    values={}
    for directory,remote in [('intents','unit'),('completed','done')]:
        if {p.stem for p in (root/directory).glob('*.json')}!=set(UNITS):raise ValueError('All original engineering units required')
        values[directory]={n:read(root/directory/(n+'.json')) for n in UNITS}
        if any(v!=records[k+'/'+remote+'/'+n] for n,v in values[directory].items()):raise ValueError('Original acknowledgements differ')
    attempts,done=values['intents'],values['completed']
    encoded,plan,rates=[read(inputs/n) for n in ('encoded.json','plan.json','rates_'+job['arm']+'.json')]
    proof=subset.validate(encoded,plan,rates,job['arm'])
    child=read(root/'TRAINING_PROCESS_RESULT.json');cycles=read(root/'TRAINING_COMPLETE_CYCLES.json')
    times=original.positive(child['update_seconds'],2)
    if len(cycles)!=2:raise ValueError('Two complete original update cycles required')
    targets=processed=0
    for step,indices in enumerate(plan['updates'],1):
        name=f'update_{step:05d}';expected={'step':step,'indices':indices,'lr':rates[step-1],
            'supervised_tokens':sum(encoded[i]['n_supervised'] for i in indices),
            'processed_tokens':sum(encoded[i]['n_processed'] for i in indices)}
        targets+=expected['supervised_tokens'];processed+=expected['processed_tokens'];actual=done[name]
        if (attempts[name]!=expected or any(actual.get(x)!=v for x,v in expected.items())
                or actual['cumulative_supervised']!=targets or actual['cumulative_processed']!=processed
                or cycles[step-1]!={'step':step,'seconds':times[step-1],'body_seconds':actual['seconds'],
                    'volume_commits_included':2,'remote_unit_and_done_included':True}
                or times[step-1]<actual['seconds'] or any(type(actual[x]) not in (int,float) or not math.isfinite(actual[x]) for x in ('loss','gradient_norm','max_allocated_bytes'))
                or actual['gradient_norm']<0 or actual['max_allocated_bytes']<=0):raise ValueError('Exact measured engineering update proof differs')
    config=read(Path(job['model']['local_path'])/'config.json')
    state=original.load_state_once(root,identity,encoded,plan,rates,job['arm'],config)
    exported=read(root/'MODEL_EXPORT.json');joined=read(root/'TRAINING_EXIT.json')
    trained={**proof,'actual_supervised_tokens':targets,'actual_processed_tokens':processed,
             'terminal_state':state['record'],'model_export_sha256':digest(exported)}
    result=read(root/'RESULT.json')
    if (child['result']!=trained or result['training']!=trained or attempts['terminal_state']!=proof
            or done['terminal_state']!=state['record']
            or attempts['terminal_model_export']!={'mode':subset.full.ARMS[job['arm']]['mode'],'final_state':state['record']}
            or done['terminal_model_export']!={'proof_sha256':digest(exported)}
            or exported['relative_path']!='model_for_vllm' or exported['final_state']!=state['record']
            or exported['optimizer_updates_after_terminal_state']!=0 or exported['evaluation_performed'] is not False
            or joined!={'pid':child['pid'],'exitcode':0,'joined_before_vllm':True,'model_export_file_sha256':sha(root/'MODEL_EXPORT.json')}):raise ValueError('Complete original state/export/child-exit chain differs')
    verify(root/'model_for_vllm',exported['files'])
    rows=read(inputs/'ENDPOINT_LOCAL.json');gpu=read(inputs/'ENDPOINT_GPU.json');subset.validate_requests(gpu,job['context'])
    if any(x['request_sha256']!=digest(r) for x,r in zip(gpu,rows)) or len(rows)!=32:raise ValueError('Original local/gpu request binding differs')
    raw=read(root/'raw/eval_0000.json');ack=done['eval_0000'];cycle=read(root/'ENDPOINT_COMPLETE_CYCLES.json')
    if (attempts['eval_0000']!={'requests':gpu,'sampling':[sampling(r,job['eos_token_ids']) for r in gpu]}
            or len(raw)!=32 or ack['count']!=32 or ack['request_ids']!=[r['id'] for r in gpu]
            or ack['raw_file_sha256']!=sha(root/'raw/eval_0000.json') or len(cycle)!=1
            or cycle[0]!={'batch':0,'seconds':result['endpoint_batch_seconds'][0],'body_seconds':ack['seconds'],
                'volume_commits_included':3,'remote_unit_and_done_included':True}):raise ValueError('Original raw/cycle engineering evidence differs')
    original.positive(result['endpoint_batch_seconds'],1)
    if result['endpoint_batch_seconds'][0]<ack['seconds']:raise ValueError('Whole cycle shorter than body')
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(job['model']['local_path'],local_files_only=True,trust_remote_code=False,use_fast=True)
    for req,item in zip(rows,raw):original.decode_record(req,item,job['eos_token_ids'],tok,config['vocab_size'])
    engine_proof(read(root/'ENGINE.json'),job)
    phases=read(root/'TERMINAL_PHASE_TIMINGS.json')
    if [x['phase'] for x in phases]!=['terminal_state','terminal_model_export'] or any(x.get('final_volume_commit_included') is not True for x in phases):raise ValueError('Full terminal timing scope required')
    original.positive([x['seconds'] for x in phases],2)
    for name in ['MODEL_LOAD_TIMING.json','TRAINING_PARENT_INTERVAL.json','ENGINE_START_TIMING.json']:
        original.positive([read(root/name)['seconds']],1)
    tokens=sum(len(x['answers'][0]['token_ids']) for x in raw)
    if (result.get('engineering_preflight') is not True or result.get('scientific_cell_result') is not False
            or result.get('no_correctness_scoring') is not True or result['generated_tokens']!=tokens
            or result['tokens_per_whole_batch_second']!=tokens/result['endpoint_batch_seconds'][0]
            or result['actual_engine_request_count']!=32 or result['formal_engine_batch_count']!=512
            or result['formal_batch_throughput_is_not_measured'] is not True or result['not_a_timing_upper_bound'] is not True):raise ValueError('Engineering result scope differs')
    return {'complete':True,'engineering_only':True,'scientific_cell_result':False,'no_score_computed':True,
            'full_state':state,'original_result_sha256':sha(root/'RESULT.json'),
            'formal_timing_admission_still_requires_independent_numeric_review':True}
