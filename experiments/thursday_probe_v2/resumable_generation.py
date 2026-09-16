"""Fixed-batch evaluation with durable RNG/output commits and no automatic replay.

API identity fields: model_hash, split_hash, batch_time_reserve_seconds (>0),
and exit_reserve_seconds (>=0, default30). Resource estimates may change between
calls; they do not change request identities. A pending intent without committed
raw output is ambiguous and requires external ledger reconciliation, never an
automatic repeated generation. Budget.reserve(batch_request_key, n) is called
once immediately before each actual new batch.

Files: <evaluation>.resume/manifest.json and batches/NNNNNN.{intent,reserved,
raw,scored}.json. Raw commits contain outputs AND pre/post Python/NumPy/torch/CUDA
RNG. Prediction and raw JSONL files are replaceable derived prefix views; the
individual committed batch files are immutable. Completed legacy predictions
without this manifest cannot be silently adopted or regenerated.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time

from experiments.thursday_probe.arithmetic_eval import score
from experiments.thursday_probe_v2.generation import _TokenizerMetadataCache
from src.sft_data import prefix


SEED=2026091603
BATCH_SIZE=8
MAX_NEW_TOKENS=512


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _read(path):return json.loads(Path(path).read_text())


def _sync_dir(path):
    fd=os.open(path,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def _atomic(path,value,*,immutable=False,jsonl=False):
    path=Path(path)
    if immutable and path.exists():raise FileExistsError('Never overwrite a committed batch artifact')
    pending=path.with_name(path.name+'.pending')
    with pending.open('w') as stream:
        if jsonl:
            for row in value:stream.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n')
        else:json.dump(value,stream,sort_keys=True,allow_nan=False);stream.write('\n')
        stream.flush();os.fsync(stream.fileno())
    pending.replace(path);_sync_dir(path.parent)


def capture_rng():
    import numpy as np
    import torch
    py=random.getstate();npy=np.random.get_state()
    return dict(python=[py[0],list(py[1]),py[2]],
        numpy=[npy[0],npy[1].tolist(),int(npy[2]),int(npy[3]),float(npy[4])],
        torch=torch.get_rng_state().tolist(),
        cuda=[state.tolist() for state in torch.cuda.get_rng_state_all()] if torch.cuda.is_available() else [])


def restore_rng(state):
    import numpy as np
    import torch
    random.setstate((state['python'][0],tuple(state['python'][1]),state['python'][2]))
    npy=state['numpy'];np.random.set_state((npy[0],np.asarray(npy[1],dtype=np.uint32),npy[2],npy[3],npy[4]))
    torch.set_rng_state(torch.tensor(state['torch'],dtype=torch.uint8,device='cpu'))
    devices=torch.cuda.device_count() if torch.cuda.is_available() else 0
    if len(state['cuda'])!=devices:raise ValueError('CUDA RNG device topology changed')
    if devices:torch.cuda.set_rng_state_all([torch.tensor(s,dtype=torch.uint8,device='cpu') for s in state['cuda']])


@contextmanager
def _caller_state(model):
    state=capture_rng();training=model.training
    try:yield
    finally:
        restore_rng(state);model.train(training)


def _protocol(event,tokenizer):
    samples=event['samples'];sampling=event['sampling']
    if type(samples) is not int or samples<=0 or type(sampling) is not bool:
        raise ValueError('Invalid frozen sampling recipe')
    args=dict(do_sample=sampling,num_beams=1,max_new_tokens=MAX_NEW_TOKENS,
        eos_token_id=tokenizer.eos_token_id,pad_token_id=tokenizer.eos_token_id,use_cache=True)
    if sampling:args.update(temperature=.7,top_p=.95,top_k=0)
    root=Path(__file__).resolve().parents[2]
    sources=('src/sft_data.py','analyses/e017_stopping.py','analyses/completion_contract.py',
             'experiments/thursday_probe/arithmetic_eval.py')
    return dict(generation={**args,'seed':SEED,'samples':samples,'batch_size':BATCH_SIZE},
        scientific_source_sha256={name:_file_hash(root/name) for name in sources}),args


def _descriptor(rows,event,identity,protocol):
    for field in ('model_hash','split_hash'):
        value=identity.get(field)
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('A lowercase SHA256 is required for '+field)
    if event['questions']!=len(rows) or event['generations']!=len(rows)*event['samples']:
        raise ValueError('Evaluation shape differs from the frozen event')
    if len({r['problem_id'] for r in rows})!=len(rows) or not rows:
        raise ValueError('Nonempty distinct question identities required')
    scientific=dict(model_hash=identity['model_hash'],split_hash=identity['split_hash'],
                    rows_hash=_digest(rows),decode_protocol_hash=_digest(protocol))
    requests=[_digest(dict(**scientific,problem_id=r['problem_id'],sample_index=s))
              for r in rows for s in range(event['samples'])]
    return dict(schema='fixed_batch_rng_resume_v1',identity=scientific,event=event,
                protocol=protocol,request_ids=requests)


def _score_raw(raw,batch,tokenizer,vocab_size,special_ids):
    from analyses.completion_contract import first_stop
    ids=[tokenizer.encode(prefix(r['prompt']),add_special_tokens=False) for r,_ in batch]
    width=max(map(len,ids));inputs=[[tokenizer.eos_token_id]*(width-len(x))+x for x in ids]
    masks=[[0]*(width-len(x))+[1]*len(x) for x in ids]
    wanted=dict(padded_prompt_width=width,problem_ids=[r['problem_id'] for r,_ in batch],
        sample_indices=[s for _,s in batch],forced_prefixes=['']*len(batch),prompt_ids=ids,
        input_ids=inputs,attention_mask=masks)
    if any(raw.get(k)!=v for k,v in wanted.items()):raise ValueError('Raw batch input identity changed')
    if len(raw['output_ids'])!=len(batch) or len(raw['stop_events'])!=len(batch):
        raise ValueError('Raw batch output/event count changed')
    records=[]
    decode=lambda ts:tokenizer.decode(ts,skip_special_tokens=True,clean_up_tokenization_spaces=False)
    for (row,sample),prompt,full,event in zip(batch,ids,raw['output_ids'],raw['stop_events']):
        if full[:width]!=inputs[len(records)]:raise ValueError('Prompt prefix changed')
        tokens=full[width:]
        oracle=first_stop(tokens,decode,tokenizer.eos_token_id,MAX_NEW_TOKENS,
                          special_ids|{t for t in tokens if t>=vocab_size})
        if event!=oracle or any(t!=tokenizer.eos_token_id for t in tokens[event['retained_tokens']:]):
            raise ValueError('Independent stop/padding audit failed')
        records.append(dict(problem_id=row['problem_id'],sample_index=sample,task=row['task'],
            category=row.get('category'),forced_prefix='',stop=event,
            generated_ids=tokens[:event['retained_tokens']],batch_output_ids=tokens,prompt_ids=prompt,
            batch_index=raw['batch_index'],batch_seconds=raw['batch_seconds'],score=score(row,event,'')))
    return records


def _generate_raw(model,tokenizer,batch,index,args):
    import torch
    from transformers import GenerationConfig,StoppingCriteriaList
    from analyses.e017_stopping import TaskBoundaryStop
    ids=[tokenizer.encode(prefix(r['prompt']),add_special_tokens=False) for r,_ in batch]
    width=max(map(len,ids))
    if width+MAX_NEW_TOKENS>1024:raise ValueError('Generation context exceeded')
    inputs=torch.tensor([[tokenizer.eos_token_id]*(width-len(x))+x for x in ids],device='cuda')
    masks=torch.tensor([[0]*(width-len(x))+[1]*len(x) for x in ids],device='cuda')
    stopper=TaskBoundaryStop(tokenizer,width,len(batch),MAX_NEW_TOKENS)
    tick=time.monotonic()
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
        output=model.generate(input_ids=inputs,attention_mask=masks,generation_config=GenerationConfig(**args),
                              stopping_criteria=StoppingCriteriaList([stopper]))
    torch.cuda.synchronize();seconds=time.monotonic()-tick
    full_ids=output.tolist()
    retained=(sum(e['retained_tokens'] for e in stopper.events) if all(e is not None for e in stopper.events) else None)
    return dict(batch_index=index,start_index=index*BATCH_SIZE,batch_seconds=seconds,
        padded_prompt_width=width,problem_ids=[r['problem_id'] for r,_ in batch],
        sample_indices=[s for _,s in batch],forced_prefixes=['']*len(batch),prompt_ids=ids,
        input_ids=inputs.tolist(),attention_mask=masks.tolist(),output_ids=full_ids,stop_events=stopper.events,
        input_nonpadding_tokens=sum(map(len,ids)),generated_tokens_with_padding=sum(len(x)-width for x in full_ids),
        retained_generated_tokens=retained,prefill_seconds=None,decode_only_seconds=None,
        generation_seconds_includes_prefill=True)


def _ledger_reservation(budget,key,n):
    if not hasattr(budget,'record'):return None
    matches=[e for e in budget.record()['events'] if e['name']==key]
    if len(matches)>1 or (matches and matches[0]['reserved']!=n):
        raise ValueError('Persistent budget reservation identity differs')
    return bool(matches)


def _publish(path,raws,records,manifest_hash,total_batches,reason):
    _atomic(path,records,jsonl=True)
    _atomic(path.with_suffix('.raw_batches.jsonl'),raws,jsonl=True)
    complete_batches=(len(records)+BATCH_SIZE-1)//BATCH_SIZE
    progress=dict(manifest_sha256=manifest_hash,completed_batches=complete_batches,
        durable_raw_batches=len(raws),total_batches=total_batches,completed_records=len(records),
        status='completed' if complete_batches==total_batches else 'partial',reason=reason)
    _atomic(path.with_suffix('.resume')/'progress.json',progress)
    return progress


def run_batches(model,tokenizer,rows,path,event,identity,remaining_batch_limit,budget,deadline):
    """Run admitted new batches; replay committed raw scores without generation.

    Budget reservations use stable batch keys. A reserve without committed raw
    output is deliberately not retried: its actual cost must first be reconciled.
    Only scheduling estimates may change on resume; identities/rows/event/recipe
    and the sequential evaluation RNG chain must match byte-for-byte.
    """
    import torch
    if type(remaining_batch_limit) is not int or remaining_batch_limit<0:
        raise ValueError('remaining_batch_limit must be a nonnegative integer')
    reserve=identity.get('batch_time_reserve_seconds');exit_reserve=identity.get('exit_reserve_seconds',30.)
    if (not isinstance(reserve,(int,float)) or isinstance(reserve,bool) or not math.isfinite(reserve) or reserve<=0
        or not isinstance(exit_reserve,(int,float)) or isinstance(exit_reserve,bool) or not math.isfinite(exit_reserve) or exit_reserve<0
        or not math.isfinite(deadline)):
        raise ValueError('Explicit finite batch and exit time reserves required')
    path=Path(path);folder=path.with_suffix('.resume');manifest_path=folder/'manifest.json'
    if path.exists() and not manifest_path.exists():raise FileExistsError('Existing evaluation is not an identified resumable stream')
    folder.mkdir(parents=True,exist_ok=True);batch_dir=folder/'batches';batch_dir.mkdir(exist_ok=True)
    with (folder/'lock').open('a') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another worker owns this evaluation') from None
        with _caller_state(model):
            protocol,args=_protocol(event,tokenizer);descriptor=_descriptor(rows,event,identity,protocol)
            vocab=len(tokenizer);special=set(tokenizer.all_special_ids)
            metadata=dict(vocab_size=vocab,special_ids=sorted(special))
            stopping_tokenizer=_TokenizerMetadataCache(tokenizer,vocab,special)
            if manifest_path.exists():
                manifest=_read(manifest_path)
                if manifest['descriptor']!=descriptor or manifest['tokenizer_metadata']!=metadata:
                    raise ValueError('Evaluation identity or decoding contract changed on resume')
            else:
                torch.manual_seed(SEED)
                manifest=dict(descriptor=descriptor,tokenizer_metadata=metadata,initial_rng=capture_rng(),
                    created_at_utc=datetime.now(timezone.utc).isoformat())
                _atomic(manifest_path,manifest,immutable=True)
            config_path=path.with_suffix('.generation.json')
            if config_path.exists():
                if _read(config_path)!=protocol['generation']:raise ValueError('Generation config changed')
            else:_atomic(config_path,protocol['generation'],immutable=True)
            manifest_hash=_file_hash(manifest_path);evaluation_hash=_digest(descriptor)
            expanded=[(r,s) for r in rows for s in range(event['samples'])]
            total_batches=(len(expanded)+BATCH_SIZE-1)//BATCH_SIZE
            raw_indices=sorted(int(p.name.split('.')[0]) for p in batch_dir.glob('*.raw.json'))
            if raw_indices!=list(range(len(raw_indices))) or len(raw_indices)>total_batches:
                raise ValueError('Raw batches are not a contiguous prefix of the frozen evaluation')
            eval_rng=manifest['initial_rng'];raws=[];records=[];timings=[];new_batches=0;replayed=0;reason=None
            model.eval()
            for index,start in enumerate(range(0,len(expanded),BATCH_SIZE)):
                batch=expanded[start:start+BATCH_SIZE];stem=batch_dir/f'{index:06d}'
                intent_path=Path(str(stem)+'.intent.json');reserved_path=Path(str(stem)+'.reserved.json')
                raw_path=Path(str(stem)+'.raw.json');scored_path=Path(str(stem)+'.scored.json')
                raw_timing_path=Path(str(stem)+'.raw_save.json');timing_path=Path(str(stem)+'.timing.json')
                requests=descriptor['request_ids'][start:start+len(batch)]
                request_key='eval_batch_'+_digest(requests)
                batch_identity=dict(evaluation_hash=evaluation_hash,batch_index=index,
                    request_key=request_key,request_ids=requests,generations=len(batch))
                generated_now=False;scored_now=False;score_save_seconds=None
                if intent_path.exists():
                    intent=_read(intent_path)
                    if intent['identity']!=batch_identity or intent['rng_before']!=eval_rng:
                        raise ValueError('Pending intent identity/RNG chain changed')
                    charged=_ledger_reservation(budget,request_key,len(batch))
                    if not reserved_path.exists() and charged:
                        # The global ledger committed before the local marker.
                        _atomic(reserved_path,batch_identity,immutable=True)
                    if reserved_path.exists() and charged is False:
                        raise ValueError('Local reservation is missing from persistent budget')
                if raw_path.exists():
                    bundle=_read(raw_path)
                    if not reserved_path.exists() or _read(reserved_path)!=batch_identity:
                        raise ValueError('Committed output has no matching reservation receipt')
                    if bundle['identity']!=batch_identity or bundle['rng_before']!=eval_rng:
                        raise ValueError('Committed raw identity/RNG chain changed')
                    raw=bundle['raw'];eval_rng=bundle['rng_after']
                else:
                    if reserved_path.exists() or scored_path.exists() or (intent_path.exists() and not hasattr(budget,'record')):
                        raise RuntimeError('Ambiguous interrupted batch '+request_key+': reconcile the ledger/fault charge; do not regenerate automatically')
                    if new_batches>=remaining_batch_limit:
                        reason='new_batch_limit';break
                    now=time.time()
                    if now+reserve+exit_reserve>deadline:
                        reason='insufficient_time_for_next_batch_and_exit';break
                    restore_rng(eval_rng)
                    intent=dict(identity=batch_identity,rng_before=eval_rng,admission=dict(
                        checked_at_unix=now,deadline_unix=deadline,batch_time_reserve_seconds=reserve,
                        exit_reserve_seconds=exit_reserve))
                    if not intent_path.exists():_atomic(intent_path,intent,immutable=True)
                    budget.reserve(request_key,len(batch))
                    _atomic(reserved_path,batch_identity,immutable=True)
                    # Logging/accounting is outside the sampler's RNG stream.
                    restore_rng(eval_rng)
                    raw=_generate_raw(model,stopping_tokenizer,batch,index,args)
                    after_rng=capture_rng()
                    bundle=dict(identity=batch_identity,rng_before=eval_rng,rng_after=after_rng,raw=raw)
                    save_tick=time.perf_counter()
                    _atomic(raw_path,bundle,immutable=True)
                    raw_save_seconds=time.perf_counter()-save_tick
                    _atomic(raw_timing_path,dict(raw_save_seconds=raw_save_seconds),immutable=True)
                    eval_rng=after_rng;new_batches+=1;generated_now=True
                if raw['batch_index']!=index or raw['start_index']!=start:
                    raise ValueError('Raw batch index changed')
                raws.append(raw)
                # Commit the compatible raw view before any scoring of this batch.
                _publish(path,raws,records,manifest_hash,total_batches,'raw_committed_pending_score')
                if scored_path.exists():
                    scored=_read(scored_path)
                    if (scored['identity']!=batch_identity or scored['raw_sha256']!=_file_hash(raw_path)
                        or scored['records_sha256']!=_digest(scored['records'])):
                        raise ValueError('Committed score identity/hash changed')
                    batch_records=scored['records']
                else:
                    if time.time()+exit_reserve>deadline:
                        reason='raw_committed_score_pending_at_deadline';break
                    score_tick=time.perf_counter()
                    batch_records=_score_raw(raw,batch,tokenizer,vocab,special)
                    cpu_score_seconds=time.perf_counter()-score_tick
                    scored=dict(identity=batch_identity,raw_sha256=_file_hash(raw_path),
                        records_sha256=_digest(batch_records),records=batch_records,cpu_score_seconds=cpu_score_seconds)
                    score_save_tick=time.perf_counter()
                    _atomic(scored_path,scored,immutable=True)
                    score_save_seconds=time.perf_counter()-score_save_tick
                    scored_now=True
                    if not generated_now:replayed+=1
                if [(r['problem_id'],r['sample_index']) for r in batch_records]!=[(r['problem_id'],s) for r,s in batch]:
                    raise ValueError('Scored batch question/sample identities changed')
                records.extend(batch_records)
                if scored_now:
                    print(json.dumps(dict(event='evaluation_batch_committed',name=event['name'],
                        completed_records=len(records),total_records=len(expanded),batch_index=index,
                        budget_used=budget.record().get('used') if hasattr(budget,'record') else None),
                        sort_keys=True),flush=True)
                if timing_path.exists():timing=_read(timing_path)
                else:
                    timing=dict(batch_index=index,input_nonpadding_tokens=raw['input_nonpadding_tokens'],
                        generated_tokens_with_padding=raw['generated_tokens_with_padding'],
                        retained_generated_tokens=raw['retained_generated_tokens'],
                        generation_seconds=raw['batch_seconds'],generation_seconds_includes_prefill=True,
                        prefill_seconds=None,decode_only_seconds=None,
                        raw_save_seconds=_read(raw_timing_path)['raw_save_seconds'] if raw_timing_path.exists() else None,
                        cpu_score_seconds=scored.get('cpu_score_seconds'),
                        score_save_seconds=score_save_seconds)
                    _atomic(timing_path,timing,immutable=True)
                timings.append(timing)
            progress=_publish(path,raws,records,manifest_hash,total_batches,reason)
            return dict(**progress,records=records,new_batches=new_batches,replayed_scoring_batches=replayed,
                request_ids=descriptor['request_ids'],journal_directory=str(folder),batch_timings=timings)
