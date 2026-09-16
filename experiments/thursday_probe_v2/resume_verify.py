"""CPU-only independent verification of an exported post-E030 continuation.

No model is instantiated, no RNG is restored globally, and no GPU API is used.
This checks scientific artifact consistency; transport/export SHA receipts and
the independent tokenizer/math scorer remain separate audits. Missing evidence
is partial, contradictory evidence is failed, and only a closed complete queue
with all expected artifacts can pass as complete.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import re


PROJECT = Path(__file__).resolve().parents[2]
DATA = PROJECT/'experiments/thursday_probe/data_r1'
RELEASE = PROJECT/'experiments/thursday_probe_v2/release_r2'
EXTRA = PROJECT/'experiments/thursday_probe_v2/release_resume_r1'
C0_SHA = 'e93d954e27a0996330492e59b642d6bd50cdb2981d81ccf0622bae3e705796c2'
BASE_SHA = '0fe3fc99f6a3895a6896bf62fdd42853481646a93b45aa167e1084fa116ae142'
PARAMETERS = 18464768
MODULES = ('q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def read(path):return json.loads(Path(path).read_text())
def physical_lines(path):
    # JSON strings may contain literal U+0085/U+2028/U+2029. Those are data,
    # not JSONL record separators; byte-stream readline splits only on LF.
    with Path(path).open('rb') as stream:return stream.readlines()
def jsonl(path):return [json.loads(line) for line in physical_lines(path) if line.strip()]
def require(condition,message):
    if not condition:raise ValueError(message)


def safe_child(folder,name):
    require(isinstance(name,str) and Path(name).name==name and name not in ('.','..'),'Unsafe artifact filename')
    return Path(folder)/name


def released(folder):
    record=read(folder/'manifest.json')
    for name,expected in record['files_sha256'].items():
        require(file_hash(safe_child(folder,name))==expected,'Frozen release file changed: '+name)
    return record


def adapter_digest(state):
    """Recreate Qwen/PEFT named_parameters order from tensors, without a model."""
    import torch
    def order(name):
        m=re.fullmatch(r'base_model.model.model.layers\.(\d+)\.(self_attn|mlp)\.(\w+)\.lora_([AB])\.weight',name)
        require(m is not None and m[3] in MODULES,'Unexpected adapter parameter name: '+name)
        require(m[2]==('self_attn' if MODULES.index(m[3])<4 else 'mlp'),'Adapter module family changed')
        return int(m[1]),MODULES.index(m[3]),m[4]
    names=sorted(state,key=order)
    require([order(n) for n in names]==[(layer,module,side) for layer in range(28)
        for module in range(7) for side in ('A','B')],'Qwen28-layer LoRA tensor coverage changed')
    h=hashlib.sha256();count=0
    for name in names:
        tensor=state[name]
        require(tensor.device.type=='cpu' and tensor.dtype==torch.float32 and tensor.ndim==2
            and torch.isfinite(tensor).all().item(),'Adapter tensor dtype/shape/finite contract changed')
        require(tensor.shape[0 if '.lora_A.' in name else 1]==16,'LoRA rank changed')
        full=name.replace('.lora_A.weight','.lora_A.default.weight').replace('.lora_B.weight','.lora_B.default.weight')
        h.update(full.encode());h.update(str(tuple(tensor.shape)).encode());h.update(str(tensor.dtype).encode())
        h.update(tensor.contiguous().numpy().tobytes());count+=tensor.numel()
    require(count==PARAMETERS,'LoRA parameter count changed')
    return dict(sha256=h.hexdigest(),parameters=count)


def checkpoint(path):
    from safetensors.torch import load_file
    record=read(path/'checkpoint_identity.json')
    require('adapter_model.safetensors' in record['files_sha256'],'Checkpoint has no adapter byte identity')
    total=0
    for name,expected in record['files_sha256'].items():
        file=safe_child(path,name);require(file_hash(file)==expected,'Checkpoint byte SHA differs: '+str(file));total+=file.stat().st_size
    require(total==record['bytes'],'Checkpoint byte total differs')
    config=read(path/'adapter_config.json')
    require(config['r']==16 and config['lora_alpha']==32 and config['lora_dropout']==0
        and config['bias']=='none' and set(config['target_modules'])==set(MODULES),'Frozen LoRA recipe differs')
    actual=adapter_digest(load_file(str(path/'adapter_model.safetensors'),device='cpu'))
    require(actual==record['parameter_digest'],'Checkpoint tensor digest differs from metadata')
    return record


def rng_identity(state,*,generation=False):
    """Validate all four saved RNG domains using isolated CPU generators only."""
    import numpy as np
    import torch
    require(set(state)=={'python','numpy','torch','cuda'},'Incomplete RNG domains')
    py=state['python'];random.Random().setstate((py[0],tuple(py[1]),py[2]))
    n=state['numpy']
    n=(n[0],np.asarray(n[1],dtype=np.uint32),n[2],n[3],n[4]) if generation else (
        n['kind'],np.asarray(n['keys'],dtype=np.uint32),n['position'],n['has_gauss'],n['cached_gaussian'])
    np.random.RandomState().set_state(n)
    def byte_state(value):
        if generation:
            require(isinstance(value,list) and value and all(type(x) is int and 0<=x<=255 for x in value),'Invalid byte RNG list')
            value=torch.tensor(value,dtype=torch.uint8,device='cpu')
        require(isinstance(value,torch.Tensor) and value.device.type=='cpu' and value.dtype==torch.uint8
            and value.ndim==1 and value.numel()>0,'Invalid RNG byte tensor')
        return value
    cpu=byte_state(state['torch']);torch.Generator(device='cpu').set_state(cpu)
    require(isinstance(state['cuda'],list) and len(state['cuda'])==1,'Expected one saved CUDA RNG state')
    cuda=[byte_state(x) for x in state['cuda']]
    # The pinned production CUDA Philox export is seed+offset (16 bytes),
    # confirmed against the actual E031/E032 recovery states. Never accept a
    # merely nonempty truncated CUDA state as complete restoration evidence.
    require(all(x.numel()==16 for x in cuda),'CUDA RNG export byte length differs from pinned run')
    normalized=dict(python=[py[0],list(py[1]),py[2]],numpy=[n[0],n[1].tolist(),n[2],n[3],n[4]],
        torch=cpu.tolist(),cuda=[x.tolist() for x in cuda])
    return dict(sha256=digest(normalized),cuda_devices=len(cuda),torch_bytes=cpu.numel(),cuda_bytes=[x.numel() for x in cuda])


def verify_history(history,schedule,lrs,dose,folder=None):
    require(len(history)<=len(schedule),'Training exceeds registered update dose')
    locations=set();journals={}
    for offset,row in enumerate(history):
        require(row['step']==offset+1 and row['row_indices']==schedule[offset],'Absolute training step/schedule indices differ')
        require(row['learning_rate']==lrs[offset],'Absolute learning-rate vector differs')
        for key in ('supervised_tokens','processed_tokens'):
            require(type(row[key]) is int and row[key]==dose['per_update'][offset][key],'Per-update token dose differs: '+key)
        require(all(math.isfinite(row[k]) and row[k]>=0 for k in ('seconds','gradient_norm'))
            and math.isfinite(row['response_nll']),'Nonfinite or negative training observation')
        location=(row['segment_file'],row['segment_line'])
        require(location not in locations,'Duplicate committed physical training update');locations.add(location)
        if folder is not None:
            name,line=location
            require(type(line) is int and line>=0 and name.startswith('segment_'),'Invalid training journal reference')
            if name not in journals:journals[name]=physical_lines(safe_child(folder/'segments',name))
            require(line<len(journals[name]) and json.loads(journals[name][line])==row,'Recovery/history physical journal differs')
    totals={key:sum(r[key] for r in history) for key in ('supervised_tokens','processed_tokens')}
    if len(history)==len(schedule):
        require(totals['supervised_tokens']==dose['supervised_response_tokens']
            and totals['processed_tokens']==dose['processed_nonpadding_tokens'],'Final training token totals differ')
    return dict(updates=len(history),**totals)


def verify_optimizer(optimizer,adapter,step,lrs):
    import torch
    groups=optimizer['param_groups'];require(len(groups)==1,'AdamW parameter-group count changed')
    group=groups[0];ids=group['params']
    require(ids==list(range(len(adapter))),'Optimizer parameter identities/count changed')
    require(tuple(group['betas'])==(.9,.999) and group['eps']==1e-8 and group['weight_decay']==0
        and group['foreach'] is False and group['amsgrad'] is False and group['maximize'] is False
        and not group.get('fused') and not group.get('capturable') and not group.get('differentiable'),
        'AdamW recipe differs')
    require(group['lr']==lrs[max(0,step-1)],'Optimizer current absolute learning rate differs')
    require(set(optimizer['state'])==(set(ids) if step else set()),'Optimizer moment state count differs')
    for index,tensor in enumerate(adapter.values()):
        if not step:break
        entry=optimizer['state'][index]
        require(set(entry)=={'step','exp_avg','exp_avg_sq'} and entry['step'].numel()==1
            and entry['step'].item()==step,'Optimizer absolute step differs')
        for key in ('exp_avg','exp_avg_sq'):
            value=entry[key]
            require(value.shape==tensor.shape and value.dtype==torch.float32 and value.device.type=='cpu'
                and torch.isfinite(value).all().item(),'Optimizer moment tensor differs')
        require((entry['exp_avg_sq']>=0).all().item(),'Negative AdamW second moment')
    return dict(parameter_states=len(optimizer['state']),absolute_step=step,learning_rate=group['lr'])


class Audit:
    def __init__(self):self.errors=[];self.missing=[]
    def run(self,label,fn):
        try:return fn()
        except FileNotFoundError as exc:self.missing.append(dict(scope=label,path=str(exc.filename)));return None
        except Exception as exc:self.errors.append(dict(scope=label,type=type(exc).__name__,message=str(exc)));return None


def verify_training(folder,reg,release,parent,checkpoints,source_commit):
    import torch
    stage='prep' if reg['updates']==32 else 'main';schedule=release['schedules'][stage];lrs=release['lrs'][stage]
    dose=release['doses'][reg['data']];identity=read(folder/'training_identity.json');protocol=identity['protocol']
    run=read(folder/'run_manifest.json');run_identity=run['identity']
    require(all(run[k]==v for k,v in reg.items()),'Run registration differs')
    require(run_identity['parent']==parent and run['parent_adapter']==parent and identity['initial_adapter']==parent,
        'Run does not fork the exact registered C0/prep parent')
    require(run_identity==protocol['identity'] and protocol['identity_sha256']==digest(run_identity),'Run/optimizer identity differs')
    require(run_identity['data_sha256']==file_hash(DATA/(reg['data']+'.jsonl'))
        and run_identity['run_id']==reg['run_id'] and run_identity['base']['sha256']==BASE_SHA,'Training input/base identity differs')
    if source_commit is not None:require(run_identity['source_commit']==source_commit,'Training source commit differs')
    require(run['optimizer_reset'] is True and run['scheduler_reset'] is True and run['seed']==17,'Child optimizer/reset seed differs')
    require(protocol['schedule_sha256']==digest(schedule) and protocol['lr_vector_sha256']==digest(lrs)
        and protocol['total_updates']==reg['updates'] and protocol['microbatch']==1 and protocol['clip']==1
        and protocol['optimizer']=='AdamW(.9,.999,1e-8,0)' and protocol['training_seed']==17,'Frozen training protocol differs')
    require(protocol['checkpoint_steps']==([0,32] if stage=='prep' else [0,64,128,256]),'Checkpoint schedule differs')
    require(re.fullmatch('[0-9a-f]{64}',protocol['encoded_rows_sha256']) is not None,'Encoded-row identity absent')
    fingerprint=digest(protocol);require(identity['fingerprint']==fingerprint,'Training protocol fingerprint differs')
    pointer=read(folder/'recovery/latest.json');path=safe_child(folder/'recovery',pointer['file'])
    require(file_hash(path)==pointer['sha256'] and path.stat().st_size==pointer['bytes'],'Latest recovery SHA/size differs')
    recovery=torch.load(path,map_location='cpu',weights_only=True)
    step=recovery['step'];require(type(step) is int and 0<=step<=reg['updates'],'Invalid recovery cursor')
    require(recovery['schema']==1 and recovery['protocol']==protocol and recovery['fingerprint']==fingerprint
        and pointer['fingerprint']==fingerprint and pointer['step']==step and recovery['initial_adapter']==parent,'Recovery identity/cursor differs')
    require(len(recovery['history'])==step,'Recovery cursor/history length differs')
    counts=verify_history(recovery['history'],schedule,lrs,dose,folder)
    if 0 not in checkpoints:raise FileNotFoundError(2,'Checkpoint0 not exported',str(folder/'checkpoint_0'))
    require(checkpoints[0]['parameter_digest']==parent,'Checkpoint0 differs from registered parent')
    for absolute,record in recovery['checkpoints'].items():
        if int(absolute) not in checkpoints:raise FileNotFoundError(2,'Committed checkpoint not exported',str(folder/f'checkpoint_{absolute}'))
        require(int(absolute)<=step and int(absolute) in checkpoints and checkpoints[int(absolute)]==record,'Recovery checkpoint identity differs')
    require(set(map(int,recovery['checkpoints']))=={s for s in protocol['checkpoint_steps'] if s<=step},'Missing committed scientific checkpoint')
    actual=adapter_digest(recovery['adapter']);require(actual==recovery['adapter_digest'],'Recovery tensor digest differs')
    if step in checkpoints:require(actual==checkpoints[step]['parameter_digest'],'Recovery adapter differs from matching checkpoint')
    opt=verify_optimizer(recovery['optimizer'],recovery['adapter'],step,lrs);rng=rng_identity(recovery['rng'])
    status='partial';final_path=folder/'run_manifest_final.json'
    if final_path.exists():
        final=read(final_path);require(final['status']=='completed','Unexpected final training status')
        require(step==reg['updates'] and final['identity']==run_identity and final['final_adapter']==actual
            and final['parent_adapter']==parent and final['recoverable_state']==pointer,'Final training manifest differs')
        require(jsonl(folder/'train_history.jsonl')==recovery['history'],'Final history and recoverable history differ')
        status='completed'
    committed={(r['segment_file'],r['segment_line']) for r in recovery['history']};discarded=[]
    for journal in sorted((folder/'segments').glob('segment_*.jsonl')):
        for line,raw in enumerate(physical_lines(journal)):
            if (journal.name,line) in committed:continue
            try:entry=json.loads(raw);discarded.append(dict(file=journal.name,line=line,step=entry.get('step'),seconds=entry.get('seconds')))
            except ValueError:discarded.append(dict(file=journal.name,line=line,step=None,seconds=None))
    return dict(**{**reg,**counts},planned_updates=reg['updates'],status=status,optimizer=opt,rng=rng,
        final_or_current_adapter=actual,parent_adapter=parent,recovery_sha256=pointer['sha256'],
        discarded_physical_updates=discarded)


def expected_evaluation(event,rows,split,model_hash,stored_protocol):
    config=dict(do_sample=event['sampling'],num_beams=1,max_new_tokens=512,eos_token_id=151643,
        pad_token_id=151643,use_cache=True,seed=2026091603,samples=event['samples'],batch_size=8)
    if event['sampling']:config.update(temperature=.7,top_p=.95,top_k=0)
    require(stored_protocol['generation']==config,'Frozen generation recipe differs')
    for name,expected in stored_protocol['scientific_source_sha256'].items():
        require(name in ('src/sft_data.py','analyses/e017_stopping.py','analyses/completion_contract.py',
            'experiments/thursday_probe/arithmetic_eval.py') and file_hash(PROJECT/name)==expected,'Frozen scoring/stopping source differs')
    require(len(stored_protocol['scientific_source_sha256'])==4,'Scientific source identity incomplete')
    identity=dict(model_hash=model_hash,split_hash=file_hash(split),rows_hash=digest(rows),decode_protocol_hash=digest(stored_protocol))
    ids=[digest(dict(**identity,problem_id=r['problem_id'],sample_index=s)) for r in rows for s in range(event['samples'])]
    return dict(schema='fixed_batch_rng_resume_v1',identity=identity,event=event,protocol=stored_protocol,request_ids=ids)


def verify_evaluation(out,event,rows,split,model_hash,ledger_events):
    name=event['name'];path=out/(name+'.jsonl');folder=path.with_suffix('.resume')
    manifest=read(folder/'manifest.json');descriptor=expected_evaluation(event,rows,split,model_hash,manifest['descriptor']['protocol'])
    require(manifest['descriptor']==descriptor,'Model/split/request evaluation identity differs')
    require(read(path.with_suffix('.generation.json'))==descriptor['protocol']['generation'],'Published decode config differs')
    rng_identity(manifest['initial_rng'],generation=True)
    import torch
    initial_cpu=torch.Generator(device='cpu').manual_seed(2026091603).get_state().tolist()
    require(manifest['initial_rng']['torch']==initial_cpu,'Evaluation initial torch seed differs')
    expanded=[(r,s) for r in rows for s in range(event['samples'])]
    require(len(expanded)==event['generations'] and len(rows)==event['questions'],'Registered evaluation denominator differs')
    raw_paths=sorted((folder/'batches').glob('*.raw.json'))
    require([p.name for p in raw_paths]==[f'{i:06d}.raw.json' for i in range(len(raw_paths))],'Raw batch sequence has holes')
    require(len(raw_paths)<=(len(expanded)+7)//8,'Extra raw batches')
    require({p.name for p in (folder/'batches').glob('*.scored.json')}<=
        {p.name.replace('.raw.json','.scored.json') for p in raw_paths},'Scored batch has no durable raw output')
    before=manifest['initial_rng'];records=[];raws=[];requests=[];reservations={};pending=[]
    for i,raw_path in enumerate(raw_paths):
        start=i*8;batch=expanded[start:start+8];ids=descriptor['request_ids'][start:start+len(batch)]
        batch_id=dict(evaluation_hash=digest(descriptor),batch_index=i,request_key='eval_batch_'+digest(ids),request_ids=ids,generations=len(batch))
        stem=raw_path.name.removesuffix('.raw.json');bundle=read(raw_path);raw=bundle['raw']
        require(bundle['identity']==batch_id and bundle['rng_before']==before,'Raw identity/RNG chain differs')
        require(read(folder/'batches'/(stem+'.reserved.json'))==batch_id,'Raw reservation receipt differs')
        intent=read(folder/'batches'/(stem+'.intent.json'))
        require(intent['identity']==batch_id and intent['rng_before']==before,'Intent differs from committed batch')
        require(ledger_events[batch_id['request_key']]['reserved']==len(batch),'Raw generation is not charged exactly once')
        rng_identity(bundle['rng_after'],generation=True);before=bundle['rng_after']
        require(raw['batch_index']==i and raw['start_index']==start and raw['problem_ids']==[r['problem_id'] for r,s in batch]
            and raw['sample_indices']==[s for r,s in batch] and raw['forced_prefixes']==['']*len(batch),'Raw question/sample order differs')
        for key in ('prompt_ids','input_ids','attention_mask','output_ids','stop_events'):
            require(len(raw[key])==len(batch),'Raw tensor/event batch dimension differs')
        width=raw['padded_prompt_width'];require(type(width) is int and 0<width<=512,'Prompt width exceeds context')
        for j in range(len(batch)):
            prompt=raw['prompt_ids'][j];padding=width-len(prompt)
            require(padding>=0 and raw['input_ids'][j]==[151643]*padding+prompt
                and raw['attention_mask'][j]==[0]*padding+[1]*len(prompt)
                and raw['output_ids'][j][:width]==raw['input_ids'][j],'Raw prompt/padding/mask identity differs')
            require(0<len(raw['output_ids'][j])-width<=512,'Generated length exceeds frozen limit')
        raws.append(raw);requests.extend(ids);reservations[batch_id['request_key']]=len(batch)
        scored_path=folder/'batches'/(stem+'.scored.json')
        if not scored_path.exists():pending.append(i);continue
        require(not pending,'Scored batches extend past a pending raw batch')
        scored=read(scored_path)
        require(scored['identity']==batch_id and scored['raw_sha256']==file_hash(raw_path)
            and scored['records_sha256']==digest(scored['records']),'Scored identity or raw/records SHA differs')
        require(len(scored['records'])==len(batch),'Scored sample denominator differs')
        for j,(row,sample) in enumerate(batch):
            record=scored['records'][j];tokens=raw['output_ids'][j][width:];stop=raw['stop_events'][j]
            require(type(stop['retained_tokens']) is int and 0<=stop['retained_tokens']<=len(tokens),'Invalid retained-token count')
            require((record['problem_id'],record['sample_index'],record['task'],record['category'])==(
                row['problem_id'],sample,row['task'],row.get('category')),'Scored problem/sample/task differs')
            require(record['batch_index']==i and record['batch_seconds']==raw['batch_seconds'] and record['stop']==stop
                and record['batch_output_ids']==tokens and record['generated_ids']==tokens[:stop['retained_tokens']]
                and record['prompt_ids']==raw['prompt_ids'][j] and record['forced_prefix']=='','Scored output differs from raw tensor/event')
        records.extend(scored['records'])
    published=jsonl(path) if path.exists() else []
    raw_view=path.with_suffix('.raw_batches.jsonl');published_raw=jsonl(raw_view) if raw_view.exists() else []
    require(published==records[:len(published)] and len(published)<=len(records),'Published predictions differ from immutable scored prefix')
    require(published_raw==raws[:len(published_raw)] and len(published_raw)<=len(raws),'Published raw view differs from immutable raw prefix')
    summary_path=out/(name+'.summary.json');summary=read(summary_path) if summary_path.exists() else None
    complete=False
    if summary is not None:
        require(all(summary[k]==v for k,v in event.items()) and summary['adapter']['sha256']==model_hash
            and type(summary['completed_records']) is int and 0<=summary['completed_records']<=len(records),
            'Evaluation summary identity/count differs')
        require(summary['status'] in ('completed','partial'),'Unknown evaluation completion status')
        if summary['completed_records']==len(published):
            require(path.exists() and summary['predictions_sha256']==file_hash(path),'Evaluation prediction SHA differs')
        elif summary['status']=='partial':
            count=summary['completed_records']
            require(count%8==0,'Partial summary is not a fixed batch prefix')
            prefix=''.join(json.dumps(r,sort_keys=True,allow_nan=False)+'\n' for r in records[:count]).encode()
            require(summary['predictions_sha256']==hashlib.sha256(prefix).hexdigest(),
                'Partial summary SHA differs from its immutable scored prefix')
        if summary['status']=='completed':
            require(len(records)==len(expanded) and published==records and published_raw==raws
                and summary['completed_records']==len(records),'Completed evaluation is not fully published')
            complete=True
    return dict(name=name,status='completed' if complete else 'partial',planned_generations=len(expanded),durable_raw_records=len(requests),
        scored_records=len(records),raw_batches=len(raws),pending_score_batches=pending,request_ids=requests,
        reservations=reservations,model_hash=model_hash,manifest_sha256=file_hash(folder/'manifest.json'),
        published_records=len(published),published_raw_batches=len(published_raw),
        summary_records=summary['completed_records'] if summary else None)


def verify_ledger(record,reservations,*,complete,faults=()):
    require(record['cap']==4864 and record['historical_consumed']==592,'Historical generation charge/cap changed')
    events=record['events'];names=[r['name'] for r in events]
    require(len(names)==len(set(names)),'Duplicate global batch reservation')
    require(all(type(r['reserved']) is int and 1<=r['reserved']<=8 for r in events),'Invalid generation batch charge')
    require(type(record['used']) is int and record['used']==592+sum(r['reserved'] for r in events)
        and 592<=record['used']<=4864,'Generation total does not reconcile or exceeds cap')
    by_name={r['name']:r for r in events};fault_map={}
    for fault in faults:
        key=fault['request_key'];n=fault['generations']
        require(key not in fault_map and key not in reservations and key in by_name and type(n) is int
            and n==by_name[key]['reserved'] and isinstance(fault['reason'],str) and fault['reason'].strip()
            and re.fullmatch('[0-9a-f]{64}',fault['evidence_sha256']) is not None,'Invalid explicit generation fault receipt')
        fault_map[key]=n
    require(all(key in by_name and by_name[key]['reserved']==n for key,n in reservations.items()),'Durable output reservation missing')
    unclassified=set(by_name)-set(reservations)-set(fault_map)
    if complete:
        require(not unclassified and sum(reservations.values())==4192 and record['used']==4784+sum(fault_map.values()),
            'Completed generation ledger needs4192 outputs plus explicit fault charges')
    return dict(historical_actual=592,historical_unique=576,historical_fault=16,
        new_durable_outputs=sum(reservations.values()),new_explicit_fault=sum(fault_map.values()),
        charged_without_exported_raw_or_fault=sum(by_name[k]['reserved'] for k in unclassified),
        unresolved_request_keys=sorted(unclassified),actual_charged=record['used'],cap=4864,
        planned_complete_without_new_fault=4784,remaining=4864-record['used'])


def verify(run_dir,initial_checkpoint):
    out=Path(run_dir);audit=Audit();runs=[];evaluations=[];checkpoints={};counts=Counter()
    releases=audit.run('frozen_releases',lambda:(released(DATA),released(RELEASE),released(EXTRA)))
    if releases is None:return dict(status='failed',errors=audit.errors,missing=audit.missing)
    old,release,extra=releases
    require(release['old_manifest_sha256']==file_hash(DATA/'manifest.json'),'Old release identity changed')
    regs=[r for r in read(RELEASE/'registrations.json')['entries'] if r['state']!='calibration']
    events=[e for e in read(RELEASE/'evaluation_queue.json') if e['state'] not in ('C0','calibration')]+read(EXTRA/'evaluation_queue.json')
    require(len(regs)==6 and sum(r['updates'] for r in regs)==1088 and sum(e['generations'] for e in events)==4192,'Continuation registration changed')
    frozen=dict(schedules=read(RELEASE/'schedules.json'),lrs=read(RELEASE/'learning_rates.json'),doses=read(RELEASE/'doses.json'))
    c0=audit.run('original_C0',lambda:checkpoint(Path(initial_checkpoint)))
    if c0 is not None:audit.run('original_C0_known_identity',lambda:require(c0['parameter_digest']['sha256']==C0_SHA,'Original C0 differs'))
    initial=audit.run('run_manifest',lambda:read(out/'run_manifest.json'))
    final=audit.run('run_manifest_final',lambda:read(out/'run_manifest_final.json'))
    ledger=audit.run('generation_ledger',lambda:read(out/'generation_ledger.json'))
    if initial is not None:
        audit.run('root_identity',lambda:require(initial['initial_adapter_sha256']==C0_SHA and initial['original_model_sha256']==BASE_SHA
            and initial['prior_actual_generations']==592 and initial['release_manifest_sha256']==file_hash(RELEASE/'manifest.json')
            and initial['data_manifest_sha256']==file_hash(DATA/'manifest.json')
            and initial['diagnostic_manifest_sha256']==file_hash(EXTRA/'manifest.json'),'Root frozen identities differ'))
    for reg in regs:
        folder=out/reg['run_id'];steps=[0,32] if reg['updates']==32 else [0,64,128,256];saved={}
        audit.run(reg['state']+'/checkpoint_scope',lambda:require(
            {p.name for p in folder.glob('checkpoint_*') if p.is_dir()}<= {f'checkpoint_{s}' for s in steps},
            'Unregistered scientific checkpoint directory'))
        for step in steps:
            if not (folder/f'checkpoint_{step}').exists():
                audit.missing.append(dict(scope=reg['state'],path=str(folder/f'checkpoint_{step}')));continue
            record=audit.run(reg['state']+'/checkpoint_'+str(step),lambda step=step:checkpoint(folder/f'checkpoint_{step}'))
            if record is not None:saved[step]=record;counts['checkpoints']+=1
        checkpoints[reg['state']]=saved
        parent=c0 if reg['parent']=='C0' else checkpoints.get(reg['parent'],{}).get(32)
        if parent is None:
            audit.missing.append(dict(scope=reg['state'],path='registered parent '+reg['parent']));continue
        if (folder/'recovery/latest.json').exists():counts['latest_pointers']+=1
        result=audit.run(reg['state']+'/training',lambda:verify_training(folder,reg,frozen,parent['parameter_digest'],saved,
            initial['source_commit'] if initial else None))
        if result is not None:runs.append(result)
    reservations={};all_requests=[]
    if ledger is not None:
        ledger_events={r['name']:r for r in ledger['events']}
        for event in events:
            state=event['state'];view=event['view'];step=128 if view=='midpoint' else 32 if state in ('C','B') else 256
            model=checkpoints.get(state,{}).get(step)
            if model is None:continue
            key='discovery_problems' if view.startswith('discovery_') else view
            split=(EXTRA if key=='train_diagnostic' else RELEASE if key in ('midpoint','sentinel') else DATA)/(key+'.jsonl')
            result=audit.run(event['name'],lambda:verify_evaluation(out,event,jsonl(split),split,model['parameter_digest']['sha256'],ledger_events))
            if result is not None:
                all_requests.extend(result.pop('request_ids'));new=result.pop('reservations')
                audit.run(event['name']+'/reservation_uniqueness',lambda:require(not(set(new)&set(reservations)),'Batch charged across multiple evaluation streams'))
                reservations.update(new);evaluations.append(result)
    audit.run('request_uniqueness',lambda:require(len(all_requests)==len(set(all_requests)),'Duplicate scientific generation request ID'))
    content_complete=(len(runs)==6 and all(r['status']=='completed' for r in runs)
        and len(evaluations)==len(events) and all(e['status']=='completed' for e in evaluations)
        and counts['checkpoints']==20 and counts['latest_pointers']==6)
    faults=audit.run('fault_receipts',lambda:read(out/'generation_faults.json')) if (out/'generation_faults.json').exists() else []
    accounting=audit.run('generation_accounting',lambda:verify_ledger(ledger,reservations,complete=content_complete,faults=faults or [])) if ledger else None
    worker_status=final.get('status') if final else None
    if worker_status and worker_status.startswith('failed'):audit.errors.append(dict(scope='worker',message='Worker ended '+worker_status))
    if worker_status=='completed':
        audit.run('complete_claim',lambda:require(content_complete and not audit.missing,'Worker claimed complete but exported required evidence is incomplete'))
        if content_complete:
            def verify_final():
                require(len(final['runs'])==6 and len(final['evaluations'])==len(events)
                    and final['reserved_generations']==ledger['used'],'Final queue manifest completion/accounting differs')
                require({r['run_id'] for r in final['runs']}=={r['run_id'] for r in regs}
                    and {e['name'] for e in final['evaluations']}=={e['name'] for e in events},'Final queue identity coverage differs')
                for record in final['runs']:
                    require(record==read(out/record['run_id']/'run_manifest_final.json'),'Root/final training manifests differ')
                for record in final['evaluations']:
                    require(record==read(out/(record['name']+'.summary.json')),'Root/evaluation summaries differ')
                require(all(final[k]==v for k,v in initial.items()),'Root initial/final frozen provenance differs')
            audit.run('final_manifest',verify_final)
    status='failed' if audit.errors else 'complete' if content_complete and worker_status=='completed' and not audit.missing else 'partial'
    return dict(schema='resume_independent_cpu_verification_v1',verified_at_utc=datetime.now(timezone.utc).isoformat(),
        run_dir=str(out),status=status,worker_status=worker_status,errors=audit.errors,missing=audit.missing,
        training=runs,evaluations=evaluations,accounting=accounting,verified_checkpoint_directories=counts['checkpoints'],
        latest_recovery_pointers=counts['latest_pointers'],expected_checkpoint_directories=20,expected_latest_pointers=6,
        unique_new_request_ids=len(set(all_requests)),completed_training_updates=sum(r['updates'] for r in runs if r['status']=='completed'),
        scope='CPU tensor/hash, ancestry, frozen schedules/dose/LR, AdamW cursor/moments, saved RNG structure/chain, request/raw/scored identities. '
            'Tokenizer/math replay and transport export SHA receipts are separate; no claim of recomputing gradients or CUDA sampling.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--initial-checkpoint',type=Path,default=PROJECT/'.local/v2_export_r2/raw/checkpoint_C0')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=verify(args.run_dir,args.initial_checkpoint)
    if args.output:
        with args.output.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(result,indent=2,sort_keys=True))
    raise SystemExit(1 if result['status']=='failed' else 0)


if __name__=='__main__':main()
