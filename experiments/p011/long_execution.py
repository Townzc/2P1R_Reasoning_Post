"""Complete A/D worker body candidate; dispatch/spec/numeric admission is separate.

No import-time model or cloud operation. The full reviewed entry must bind its
source, frozen input/model manifests, exact forecast policy and once-only claim.
This body has no retries, checkpoint resume, partial scoring or arm selection.
"""
from copy import deepcopy
import math
import multiprocessing
import os
from pathlib import Path
import time
import traceback

from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, verify
from experiments.p011 import long_training as training
from experiments.p011.long_evaluation import sampling, MAX_NEW_TOKENS, BENCHMARK_COUNTS


class WholeAnswerJournal:
    """Each update is reserved before any optimizer work; arbitrary exact U.

    Atomic remote intents plus committed local records deliberately retain even
    a failed single update. There is no block-size divisibility requirement and
    no route to resume a partially acknowledged job.
    """
    def __init__(self, out, key, store, commit, check, encoded, plan, rates, forecast):
        self.out, self.key, self.store = Path(out), key, store
        self.commit, self.check, self.forecast = commit, check, forecast
        self.records = [dict(step=i+1, indices=indices, lr=rates[i],
            supervised_tokens=sum(encoded[j]['n_supervised'] for j in indices),
            processed_tokens=sum(encoded[j]['n_processed'] for j in indices))
            for i, indices in enumerate(plan['updates'])]
        self.cursor, self.pending, self.terminal_cursor = 0, None, 0
        self.times, self.failed = [], False
        self.cycles, self.cycle_started = [], None
        self.total_supervised, self.total_processed = 0, 0

    def begin(self, name, record):
        try:
            self.check()
            if self.cycle_started is not None:
                raise ValueError('Previous complete iteration has not closed')
            if name.startswith('update_'):self.cycle_started=time.monotonic()
            if self.failed or self.pending is not None:
                raise RuntimeError('Failed or unfinished unit cannot be reused')
            if name.startswith('update_'):
                if (self.cursor >= len(self.records) or name != f'update_{self.cursor+1:05d}'
                        or record != self.records[self.cursor] or self.terminal_cursor):
                    raise ValueError('Foreign or repeated exact update')
                projection = self.forecast(len(self.records)-self.cursor, list(self.times))
                dump(self.out/'forecasts'/(name+'.json'), projection)
            elif (self.cursor != len(self.records) or self.terminal_cursor >= 2
                  or name != ('terminal_state', 'terminal_model_export')[self.terminal_cursor]):
                raise ValueError('Terminal state/export must follow all complete updates')
            if not self.store.put(self.key+'/unit/'+name, record, skip_if_exists=True):
                raise RuntimeError('Permanent unit marker already exists')
            dump(self.out/'intents'/(name+'.json'), record)
            self.pending = name, deepcopy(record)
        except BaseException:
            self.failed = True
            raise

    def end(self, name, record):
        try:
            self.check()
            if self.failed or self.pending is None or self.pending[0] != name:
                raise ValueError('No matching unfinished unit')
            if name.startswith('update_'):
                expected = self.pending[1]
                next_s = self.total_supervised + expected['supervised_tokens']
                next_p = self.total_processed + expected['processed_tokens']
                if (any(record.get(k) != v for k, v in expected.items())
                        or record.get('cumulative_supervised') != next_s
                        or record.get('cumulative_processed') != next_p
                        or any(type(record.get(k)) not in (int, float)
                               or not math.isfinite(record[k]) for k in ('loss','gradient_norm','seconds'))
                        or record['seconds'] <= 0 or record['gradient_norm'] < 0):
                    raise ValueError('Exact finite complete update proof required')
            dump(self.out/'completed'/(name+'.json'), record)
            if not self.store.put(self.key+'/done/'+name, record, skip_if_exists=True):
                raise RuntimeError('Duplicate unit completion')
            if name.startswith('update_'):
                self.cursor += 1
                self.total_supervised, self.total_processed = next_s, next_p
                self.body_seconds=record['seconds']
            else:
                self.terminal_cursor += 1
            self.pending = None
        except BaseException:
            self.failed = True
            raise

    def finish_update(self):
        if self.cycle_started is None or self.pending is not None or self.failed:
            raise ValueError('Complete acknowledged update and both commits required')
        elapsed=time.monotonic()-self.cycle_started
        if elapsed<self.body_seconds:raise ValueError('Complete cycle shorter than model work')
        self.cycles.append(dict(step=self.cursor,seconds=elapsed,body_seconds=self.body_seconds,
            volume_commits_included=2,remote_unit_and_done_included=True))
        self.times.append(elapsed);self.cycle_started=None

    def complete(self):
        self.check()
        if (self.failed or self.pending is not None or self.cursor != len(self.records)
                or self.terminal_cursor != 2 or self.cycle_started is not None):
            raise ValueError('Full exact training/state/export journal required')


def engine_settings(context):
    if type(context) is not int or not MAX_NEW_TOKENS < context <= 32768:
        raise ValueError('Actual complete-prompt plus original cap context required')
    return dict(dtype='bfloat16', tensor_parallel_size=1, max_model_len=context,
        max_num_seqs=32, max_num_batched_tokens=8192, gpu_memory_utilization=.80,
        enforce_eager=False, enable_prefix_caching=False, enable_chunked_prefill=True,
        seed=17, generation_config='vllm', disable_log_stats=True, trust_remote_code=False,
        compilation_config=dict(level=3, cudagraph_mode='FULL_AND_PIECEWISE',
            cudagraph_capture_sizes=[1,2,4,8,16,32]))


def validate_engine(config, context):
    actual = dict(max_model_len=config.model_config.max_model_len,
        enforce_eager=config.model_config.enforce_eager, dtype=str(config.model_config.dtype),
        max_num_seqs=config.scheduler_config.max_num_seqs,
        max_num_batched_tokens=config.scheduler_config.max_num_batched_tokens,
        enable_chunked_prefill=config.scheduler_config.enable_chunked_prefill,
        enable_prefix_caching=config.cache_config.enable_prefix_caching,
        gpu_memory_utilization=config.cache_config.gpu_memory_utilization,
        compilation_level=config.compilation_config.level,
        cudagraph_mode=config.compilation_config.cudagraph_mode.name,
        cudagraph_capture_sizes=sorted(config.compilation_config.cudagraph_capture_sizes))
    expected = dict(max_model_len=context, enforce_eager=False, dtype='torch.bfloat16',
        max_num_seqs=32, max_num_batched_tokens=8192, enable_chunked_prefill=True,
        enable_prefix_caching=False, gpu_memory_utilization=.80, compilation_level=3,
        cudagraph_mode='FULL_AND_PIECEWISE', cudagraph_capture_sizes=[1,2,4,8,16,32])
    if actual != expected:
        raise ValueError('Actual long-context engine differs; no eager fallback')
    return actual


def software():
    import importlib.metadata
    import torch
    versions={p:importlib.metadata.version(p) for p in
              ('vllm','torch','transformers','tokenizers','peft','numpy','safetensors')}
    expected=dict(vllm='0.11.0',transformers='4.56.2',tokenizers='0.22.1',
                  peft='0.17.1',numpy='2.2.6',safetensors='0.6.2')
    if (any(versions[k]!=v for k,v in expected.items())
            or versions['torch'].split('+')[0]!='2.8.0'
            or torch.version.cuda!='12.8' or not torch.cuda.is_available()
            or torch.cuda.device_count()!=1 or 'H100' not in torch.cuda.get_device_name(0)
            or torch.cuda.get_device_properties(0).total_memory<75*1024**3):
        raise ValueError('Pinned Linux versions and one H10080GB required')
    torch.set_num_threads(4)
    return dict(versions=versions,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0))


def validate_endpoint(rows, context):
    """GPU request file is a gold-free projection of the local source roster."""
    expected = {f'{b}:{i:04d}:{mode}:{seed}'
        for b, count in BENCHMARK_COUNTS.items() for i in range(count)
        for mode, seeds in ([('sample', range(4)), ('greedy', [0])] if b=='math500'
                            else [('sample', range(8))]) for seed in seeds}
    fields = {'id','problem_id','benchmark','source_row','mode','seed','prompt_token_ids',
              'prompt_text_sha256','raw_prompt_text_sha256','native_NFC_changed','required_context','request_sha256'}
    if len(rows) != len(expected) or {r['id'] for r in rows} != expected:
        raise ValueError('Exactly all 3300 original long endpoints required')
    prompts = {}
    for r in rows:
        pid = f"{r['benchmark']}:{r['source_row']:04d}"
        ids = r['prompt_token_ids']
        if (set(r) != fields or r['problem_id'] != pid
                or r['id'] != f"{pid}:{r['mode']}:{r['seed']}"
                or not ids or any(type(i) is not int or not 0 <= i < 151936 for i in ids)
                or type(r['native_NFC_changed']) is not bool
                or r['required_context'] != len(ids)+MAX_NEW_TOKENS
                or r['required_context'] > context
                or any(not isinstance(r[k],str) or len(r[k])!=64
                       for k in ('request_sha256','prompt_text_sha256','raw_prompt_text_sha256'))):
            raise ValueError('Foreign, truncated, gold-bearing or malformed endpoint')
        prompt = (ids, r['prompt_text_sha256'],r['raw_prompt_text_sha256'],r['native_NFC_changed'])
        if pid in prompts and prompts[pid] != prompt:
            raise ValueError('The same question has different native prompt tokens')
        prompts[pid] = prompt
    if context != max(r['required_context'] for r in rows):
        raise ValueError('Context must bind the actual complete prompt maximum')
    engine_settings(context)


def save_raw(part, params, returned):
    """Retain every backend return before deciding whether the batch is complete."""
    records = []
    for i, obj in enumerate(returned):
        row = part[i] if i < len(part) else None
        records.append(dict(id=row['id'] if row else None,
            request_sha256=row['request_sha256'] if row else None,
            prompt_token_ids=list(obj.prompt_token_ids), sampling=params[i] if row else None,
            answers=[dict(token_ids=list(a.token_ids), backend_text=a.text,
                finish_reason=a.finish_reason, stop_reason=a.stop_reason) for a in obj.outputs]))
    return records


def evaluate(llm, constructor, rows, model_eos, out, key, store, commit, check, forecast):
    """One request per original seed; every raw return survives shape failures."""
    out = Path(out)
    times,cycles = [],[]
    for first in range(0, len(rows), 32):
        cycle_start=time.monotonic()
        check()
        part = rows[first:first+32]
        params = [sampling(r, model_eos) for r in part]
        name = f'eval_{first//32:04d}'
        projection = forecast((len(rows)-first+31)//32, list(times))
        dump(out/'forecasts'/(name+'.json'), projection)
        intent = dict(requests=part, sampling=params)
        if not store.put(key+'/unit/'+name, intent, skip_if_exists=True):
            raise RuntimeError('Endpoint batch already attempted')
        dump(out/'intents'/(name+'.json'), intent)
        commit()
        tick = time.monotonic()
        returned = llm.generate([{'prompt_token_ids':r['prompt_token_ids']} for r in part],
                               [constructor(**p) for p in params], use_tqdm=False)
        raw = save_raw(part, params, returned)
        dump(out/'raw'/(name+'.json'), raw)
        commit()
        if (len(raw) != len(part) or any(len(o['answers'])!=1
                or o['id']!=r['id'] or o['prompt_token_ids']!=r['prompt_token_ids']
                for o,r in zip(raw,part))):
            raise ValueError('Partial/invalid backend output retained; no retry')
        check()
        ack = dict(count=len(part), raw_file_sha256=sha(out/'raw'/(name+'.json')),
                   request_ids=[r['id'] for r in part], seconds=time.monotonic()-tick)
        dump(out/'completed'/(name+'.json'), ack)
        if not store.put(key+'/done/'+name, ack, skip_if_exists=True):
            raise RuntimeError('Duplicate endpoint completion')
        commit()
        elapsed=time.monotonic()-cycle_start
        cycles.append(dict(batch=first//32,seconds=elapsed,body_seconds=ack['seconds'],
            volume_commits_included=3,remote_unit_and_done_included=True))
        times.append(elapsed)
    dump(out/'ENDPOINT_COMPLETE_CYCLES.json',cycles)
    return times


def child(conn, model_assets, arm, inputs, out, identity, key, claim, stop, timing):
    """Spawn-only actual training; its process must exit before vLLM allocation."""
    try:
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
            raise ValueError('Required deterministic CUDA environment missing')
        import modal
        from experiments.p011.long_numeric import forecast
        volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        store = modal.Dict.from_name('p011-once-20261020', create_if_missing=False)
        volume.reload()
        def check():
            if time.time() >= stop-30: raise TimeoutError('Original full worker deadline')
            if store.get(key+'/claim') != claim: raise RuntimeError('Original claim changed')
        encoded, plan, rates = [read(Path(inputs)/name) for name in ('encoded.json','plan.json','rates_'+arm+'.json')]
        training.validate_plan(encoded, plan, rates, arm)
        check()
        dump(Path(out)/'TRAINING_ENVIRONMENT.json',software())
        volume.commit()
        model, tokenizer, optimizer = training.load_model(model_assets, arm)
        journal = WholeAnswerJournal(out,key,store,volume.commit,check,encoded,plan,rates,
            lambda left, observed: forecast(timing, left, (3300+31)//32, observed, [], time.time()))
        result = training.train_terminal(model,tokenizer,optimizer,encoded,plan,rates,arm,
                                         out,journal,identity)
        journal.complete()
        dump(Path(out)/'TRAINING_COMPLETE_CYCLES.json',journal.cycles)
        dump(Path(out)/'TRAINING_PROCESS_RESULT.json',dict(result=result,update_seconds=journal.times,
                                                          pid=os.getpid()))
        volume.commit()
        conn.send(('complete', result, journal.times))
    except BaseException:
        conn.send(('error', traceback.format_exc(), []))
        raise
    finally:
        conn.close()


def joined_training(inputs, out, assets, arm, identity, key, claim, stop, timing,
                    commit, reload_volume, context=None):
    """The parent does not import torch or retain training CUDA allocations."""
    ctx = context or multiprocessing.get_context('spawn')
    parent, remote = ctx.Pipe()
    process = ctx.Process(target=child, args=(remote,assets,arm,str(inputs),str(out),
                                             identity,key,claim,stop,timing))
    try:
        process.start()
        remote.close()
        if not parent.poll(max(0,stop-time.time()-30)):
            raise TimeoutError('Training original window expired')
        kind, result, times = parent.recv()
        process.join(timeout=max(0,min(30,stop-time.time()-15)))
        if kind!='complete' or process.is_alive() or process.exitcode!=0:
            raise RuntimeError('Training child failed or did not exit: '+str(result))
        reload_volume()
        export = read(Path(out)/'MODEL_EXPORT.json')
        if (digest(export)!=result['model_export_sha256']
                or export['relative_path']!='model_for_vllm'
                or export['final_state']!=result['terminal_state']
                or export['optimizer_updates_after_terminal_state']!=0):
            raise ValueError('Full terminal model/export binding differs')
        verify(Path(out)/'model_for_vllm', export['files'])
        dump(Path(out)/'TRAINING_EXIT.json',dict(pid=process.pid,exitcode=process.exitcode,
            joined_before_vllm=True,model_export_file_sha256=sha(Path(out)/'MODEL_EXPORT.json')))
        commit()
        return result,times,str(Path(out)/'model_for_vllm')
    finally:
        if process.pid is not None and process.is_alive():
            process.kill()
            process.join(timeout=5)
        parent.close()
        remote.close()


def worker_body(job, inputs, out, identity, key, claim, stop, timing, store, volume):
    """Exact admitted payload through train-exit, vLLM and durable raw completion.

    The outer entry owns source/review/budget/resource checks, atomic dispatch
    and claim, a process-tree hard timer and original failure preservation.
    This function is not a separately callable cloud entry or approval bypass.
    """
    from experiments.p011.long_numeric import forecast
    if (job['kind'] not in ('student','baseline') or job['arm'] not in training.ARMS
            or job['model']['model_id'] != training.ARMS[job['arm']]['model_id']
            or job['model']['revision'] != training.ARMS[job['arm']]['revision']
            or identity['job_sha256'] != digest(job)
            or stop != timing['worker_start_epoch']+timing['worker_hard_seconds']
            or os.environ.get('VLLM_USE_V1') != '1'):
        raise ValueError('Exact admitted long payload, identity and original deadline required')
    inputs,out = Path(inputs),Path(out)
    def check():
        if time.time() >= stop-30:raise TimeoutError('Original long worker deadline')
        if store.get(key+'/claim') != claim:raise RuntimeError('Original claim changed')
    check()
    verify(inputs,job['input_files'])
    rows = read(inputs/'ENDPOINT_GPU.json')
    validate_endpoint(rows,job['context'])
    if job['kind']=='student':
        result,training_times,model_path = joined_training(inputs,out,job['model'],job['arm'],
            identity,key,claim,stop,timing,volume.commit,volume.reload)
    else:
        if job['arm']=='S-F15':raise ValueError('The 1.5B baseline is shared, never duplicated')
        verify(job['model']['remote_path'],job['model']['files'])
        result,training_times,model_path = None,[],job['model']['remote_path']
        dump(out/'BASELINE_PROOF.json',dict(training_updates=0,model=job['model']))
        volume.commit()
    check()
    from transformers import AutoTokenizer
    from vllm import LLM,SamplingParams
    environment=software()
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,
                                             trust_remote_code=False,use_fast=True)
    if tokenizer.eos_token_id!=151645:raise ValueError('Original Instruct tokenizer EOS differs')
    for r in rows:
        text=tokenizer.decode(r['prompt_token_ids'],skip_special_tokens=False,
                              clean_up_tokenization_spaces=False)
        if digest(text)!=r['prompt_text_sha256']:
            raise ValueError('Native prompt tokenization differs from admitted exact text')
        SamplingParams(**sampling(r,job['eos_token_ids']))
    dump(out/'LINUX_CONSTRUCTORS.json',dict(count=len(rows),environment=environment,
        before_vllm_model_allocation=True,all_native_prompt_texts_verified=True))
    volume.commit()
    projection=forecast(timing,0,(len(rows)+31)//32,training_times,[],time.time())
    dump(out/'PRE_ENGINE_FORECAST.json',projection)
    llm=LLM(model=model_path,tokenizer=model_path,**engine_settings(job['context']))
    config=llm.llm_engine.vllm_config
    native=config.model_config.hf_config.eos_token_id
    native=native if isinstance(native,list) else [native]
    if (not native or not set(native)<=set(job['eos_token_ids'])
            or config.model_config.hf_config.architectures!=['Qwen2ForCausalLM']):
        raise ValueError('Pinned Qwen model architecture or automatic EOS differs')
    dump(out/'ENGINE.json',dict(actual=validate_engine(config,job['context']),
        requested=engine_settings(job['context']),model_path=model_path))
    volume.commit()
    endpoint_times=evaluate(llm,SamplingParams,rows,job['eos_token_ids'],out,key,store,
        volume.commit,check,lambda n,t:forecast(timing,0,n,training_times,t,time.time()))
    check()
    value=dict(training=result,raw_endpoint_count=len(rows),unique_questions=600,
        endpoint_batch_seconds=endpoint_times,training_update_seconds=training_times,
        score='NOT_SCORED; full raw oracle and original frozen local scorer required',
        model_export_relative_path='model_for_vllm' if result is not None else None)
    dump(out/'RESULT.json',value)
    volume.commit()
    return value
