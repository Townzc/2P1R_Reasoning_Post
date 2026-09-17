"""Two fixed E031 children and a finite, outcome-independent new evaluation."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import time

from experiments.thursday_probe.common import digest, dump, stamp, verify_manifest
from experiments.thursday_probe.lora import attach, parameter_digest
from experiments.thursday_probe_v2.config import REVISION, learning_rates
from experiments.thursday_probe_v2.training import restore_adapter, atomic_json
from scripts.audit_family_matching import verified_tokenizer
from src.sft_data import encode_row, sha256_file
from .generation import run_event, _caller_state, _read, target_seed
from .operator_forward import run_operator
from .training import train_segment

ROOT=Path('experiments/post_e037_goal_training')
RELEASE=ROOT/'release_v1'
OUT=Path(os.environ.get('GOAL_TRAINING_OUTPUT','runs/post_e037_goal_training_v1'))
STATES=('E031','G-single','G-paired')
BASE_SHA='0fe3fc99f6a3895a6896bf62fdd42853481646a93b45aa167e1084fa116ae142'
PARENT_SHA='0936c1682d6df767fbc91a54deba6de1ff558dfd5e8182ae8b3c0d32a892074e'


class SegmentPause(Exception):
    pass


def event(state,interface,decoding='greedy',view='eval'):
    questions={'eval':96,'train16':32,'midpoint12':24}[view]
    samples=4 if decoding=='sampled' else 1
    component=interface if view=='eval' else ('train_' if view=='train16' else 'midpoint_')+interface
    return dict(name=f'{state}_{component}_{decoding}',state=state,interface=interface,
        decoding=decoding,view=view,questions=questions,samples=samples,sampling=samples==4,
        generations=questions*samples,expected_records=questions*samples,
        checkpoint_step=32 if state=='E031' else 128 if view=='midpoint12' else 256)


def evaluation_queue():
    result=[event('E031',i) for i in 'FHC']+[event('E031',i,'sampled') for i in 'FH']
    result += [event(s,'H',view='midpoint12') for s in STATES[1:]]
    for s in STATES[1:]:
        result += [event(s,i) for i in 'FHC']+[event(s,i,view='train16') for i in 'FH']
    result += [event(s,i,'sampled') for s in STATES[1:] for i in 'FH']
    return result


def frozen_inputs():
    from .data import load_inputs
    manifest=verify_manifest(RELEASE);inputs=load_inputs()
    regs=_read(ROOT/'registration.json')['entries']
    if [(r['state'],r['data'],r['parent'],r['updates']) for r in regs] != [
            ('G-single','single','E031',256),('G-paired','paired','E031',256)]:
        raise ValueError('Two registered E031 children required')
    if len({r['run_id'] for r in regs})!=2:raise ValueError('Distinct training identities required')
    for key,count in dict(single=1024,paired=1024,F=96,H=96,C=96,midpoint_H=24,train_F=32,train_H=32).items():
        if len(inputs[key])!=count:raise ValueError('Frozen input shape changed: '+key)
    schedules=inputs['schedules'];lrs=inputs['learning_rates']
    if lrs!=learning_rates(256) or schedules['single']!=schedules['paired']:
        raise ValueError('Released LR/schedule differs from shared frozen256 update recipe')
    for arm in ('single','paired'):
        schedule=schedules[arm]
        if len(schedule)!=256:raise ValueError('Exactly256 updates required')
        for batch in schedule:
            if len(batch)!=16 or sum(i<512 for i in batch)!=8 or len(set(batch))!=16:
                raise ValueError('Each update must use8 H and8 F distinct slots')
        for start in range(0,256,64):
            if sorted(i for b in schedule[start:start+64] for i in b)!=list(range(1024)):
                raise ValueError('Every H/F source slot must occur once per epoch')
    if inputs['single'][512:]!=inputs['paired'][512:]:raise ValueError('Shared F replay differs')
    events=evaluation_queue()
    if len(events)!=21 or sum(e['generations'] for e in events)!=3344:
        raise ValueError('Frozen evaluation count changed')
    return inputs,regs,manifest


def dry_run():
    inputs,regs,_=frozen_inputs()
    return dict(status='prepared_not_run',runs=regs,updates=512,training_updates=512,
        planned_generations=3344,generation_cap=3600,operator_contexts=288,candidate_scores=1152,
        release_manifest_sha256=sha256_file(RELEASE/'manifest.json'),evaluations=evaluation_queue(),
        parent='E031',parent_adapter_sha256=PARENT_SHA,seed=2026091707,
        target_seeds={str(i):target_seed(i) for i in (0,1)},
        reference_nll=dict(views=8,records_per_view=512,microbatch=1,planned_forward_calls=4096,
            planned_input_tokens=sum(inputs['dose'][arm]['processed_nonpadding_tokens']//2 for arm in ('single','paired')),
            scope='Each arm own H/F training references before/after; not common heldout generalization'),
        outcomes_affect_queue=False,admission='Next saveable16-update unit or fixed generation batch only')


def ensure_parent_reference(out,parent):
    """Step0 is a checked reference to the already preserved E031 adapter."""
    out=Path(out);parent=Path(parent).resolve();out.mkdir(parents=True,exist_ok=True)
    link=out/'checkpoint_0'
    if link.is_symlink():
        if link.resolve()!=parent:raise ValueError('Step0 parent reference changed')
    elif link.exists():raise ValueError('Step0 must reference shared E031, never a new copied adapter')
    else:link.symlink_to(parent,target_is_directory=True)
    return link


def validate_encoded(encoded,inputs):
    """Bind runtime serialization and effective token-normalized dose."""
    actual={}
    for arm in ('single','paired'):
        rows=encoded[arm]
        for row in rows:
            labels=row['labels'];ids=row['input_ids']
            if len(labels)!=len(ids) or sum(x!=-100 for x in labels)!=row['n_supervised'] or len(ids)!=row['n_processed']:
                raise ValueError('Encoded mask/token counts changed')
        history=inputs['schedules'][arm]
        actual[arm]=dict(encoded_rows_sha256=digest([digest(r) for r in rows]),
            supervised_response_tokens=sum(rows[i]['n_supervised'] for batch in history for i in batch),
            processed_nonpadding_tokens=sum(rows[i]['n_processed'] for batch in history for i in batch))
        registered=inputs['dose'].get(arm,{})
        if (registered.get('encoded_sha256')!=digest(rows) or
                registered.get('encoded_row_sha256')!=[digest(r) for r in rows]):
            raise ValueError('Released exact encoded row identities changed: '+arm)
        for field in actual[arm]:
            if field in registered and registered[field]!=actual[arm][field]:
                raise ValueError('Frozen serialized token budget changed: '+arm+'/'+field)
    return actual


def reference_progress(out,regs):
    # Intents retain possible interrupted work but are not completed forwards.
    references=[_read(path) for reg in regs for view in ('H','F') for stage in ('before','after')
                if (path:=Path(out)/reg['run_id']/f'reference_{view}_{stage}.json').exists()]
    pending=[str(path.relative_to(out)) for reg in regs for path in (Path(out)/reg['run_id']).glob('reference_*.intent.json')
             if not path.with_name(path.name.replace('.intent.json','.json')).exists()]
    return dict(reference_forward_calls=sum(r['forward_calls'] for r in references),
        reference_forward_seconds=sum(r['forward_seconds'] for r in references),
        reference_forward_input_tokens=sum(r['input_tokens'] for r in references),
        reference_incomplete_intents=pending)


def worker(snapshot,endpoint_root):
    if os.environ.get('GOAL_TRAINING_BOUNDED')!='post_e037_goal_training_v1':
        raise ValueError('Bounded launcher required')
    from .launcher import GenerationBudget,source
    import torch
    from transformers import AutoModelForCausalLM
    inputs,regs,release=frozen_inputs();events={e['name']:e for e in evaluation_queue()}
    deadline=float(os.environ['GOAL_TRAINING_DEADLINE'])
    parent=Path(endpoint_root)/'thu_v2_e031_r1/checkpoint_32'
    parent_identity=_read(parent/'checkpoint_identity.json')
    if parent_identity['parameter_digest']['sha256']!=PARENT_SHA:raise ValueError('Exact E031 parent required')
    for name,sha in parent_identity['files_sha256'].items():
        if Path(name).name!=name or sha256_file(parent/name)!=sha:raise ValueError('E031 parent bytes changed')
    src=source(os.environ['GOAL_TRAINING_PUBLISHED_COMMIT'])
    if isinstance(src,str):src=dict(source_commit=src)
    OUT.mkdir(parents=True,exist_ok=True);budget=GenerationBudget(OUT/'generation_ledger.json')
    release_hash=sha256_file(RELEASE/'manifest.json')
    immutable=dict(**src,release_manifest_sha256=release_hash,parent_adapter=parent_identity['parameter_digest'],
        parent_checkpoint_identity=parent_identity,
        parent='E031',base_parameter_sha256=BASE_SHA,model_revision=REVISION,
        seeds=dict(training=17,evaluation=2026091707,target_substreams={str(i):target_seed(i) for i in (0,1)}),
        inference='FP32 parameters/BF16 autocast/SDPA/TF32 off',scientific_selection_gates=[])
    if (OUT/'run_manifest.json').exists():
        if _read(OUT/'run_manifest.json')!=immutable:raise ValueError('Execution identity changed on resume')
    else:dump(OUT/'run_manifest.json',immutable)
    progress=dict(**immutable,status='running',runs=[],evaluations=[],operators=[],training_updates=0,
        forward_contexts=0,candidate_scores=0,reference_forward_calls=0,reference_forward_seconds=0)
    started=time.monotonic();model=None

    def publish():
        progress.update(training_updates=sum(r.get('completed_updates',0) for r in progress['runs']),
            **reference_progress(OUT,regs),
            generation_attempts=budget.used,updated_at_utc=stamp(),disk_free_gib=shutil.disk_usage(OUT).free/2**30)
        atomic_json(OUT/'progress.json',progress)

    def admit(seconds,minimum_free_gib=1.25):
        if time.time()+seconds+30>deadline or shutil.disk_usage(OUT).free/2**30<minimum_free_gib:
            raise SegmentPause('Time/disk insufficient for next durable unit')

    def on_signal(*_):raise TimeoutError('Bounded worker signal; preserve last durable cursor')
    signal.signal(signal.SIGTERM,on_signal)
    try:
        admit(150)
        tokenizer,tok=verified_tokenizer(Path(snapshot));tokenizer.pad_token=tokenizer.eos_token
        encoded={arm:[encode_row(r,tokenizer,1024) for r in inputs[arm]] for arm in ('single','paired')}
        doses=validate_encoded(encoded,inputs);progress.update(tokenizer=tok,actual_encoded_doses=doses)
        torch.manual_seed(17);torch.set_num_threads(8)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        base=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.float32,attn_implementation='sdpa',local_files_only=True).cuda()
        model=attach(base);model.eval();base_hash=parameter_digest(model)
        if base_hash['sha256']!=BASE_SHA:raise ValueError('Frozen base changed')
        restore_adapter(model,parent);checkpoints={'E031':parent};progress['base_parameter_digest']=base_hash

        def ev(e):
            key=e['interface'] if e['view']=='eval' else ('train_' if e['view']=='train16' else 'midpoint_')+e['interface']
            path=OUT/(e['name']+'.jsonl');adapter=parameter_digest(model,True)
            result=run_event(model,tokenizer,inputs[key],path,e,
                dict(model_hash=adapter['sha256'],split_hash=release_hash,batch_time_reserve_seconds=120.,exit_reserve_seconds=30.),
                10000,budget,deadline)
            view=dict(**e,status=result['status'],completed_records=result['completed_records'],adapter=adapter,
                predictions_sha256=sha256_file(path),release_manifest_sha256=release_hash,
                reason=result['reason'],batch_timings=result['batch_timings'],substreams=result.get('substreams',[]))
            atomic_json(path.with_suffix('.summary.json'),view)
            progress['evaluations']=[r for r in progress['evaluations'] if r['name']!=e['name']]+[view];publish()
            if result['status']!='completed':raise SegmentPause(result['reason'])

        def operators(state):
            from .data import load_operator_rows
            with _caller_state(model):
                model.eval()
                record=run_operator(model,load_operator_rows(),OUT,state,parameter_digest(model,True)['sha256'],release_hash,deadline)
            progress['operators']=[r for r in progress['operators'] if r['state']!=state]+[{k:v for k,v in record.items() if k!='records'}]
            for field in ('forward_contexts','candidate_scores','recorded_contexts','unavailable_contexts','forward_calls','input_tokens','seconds'):
                progress[{'input_tokens':'forward_tokens','seconds':'forward_seconds'}.get(field,field)]=sum(r[field] for r in progress['operators'])
            publish()
            if record['status']!='completed':raise SegmentPause('Partial operator evaluation')

        def nll_once(path,rows):
            binding=dict(adapter=parameter_digest(model,True),encoded_rows_sha256=digest(rows))
            if path.exists():
                result=_read(path)
                if result['identity']!=binding:raise ValueError('Recorded NLL model/data identity changed')
                return result
            intent=path.with_suffix('.intent.json')
            if intent.exists():raise RuntimeError('Ambiguous interrupted NLL; preserve intent and do not automatically repeat')
            from src.relation_experiment import reference_nll
            admit(120);tick=time.monotonic()
            dump(intent,dict(identity=binding,planned_forward_calls=len(rows),
                planned_input_tokens=sum(r['n_processed'] for r in rows),started_at_utc=stamp()))
            with _caller_state(model):result=reference_nll(model,rows,tokenizer,1)
            result.update(identity=binding,forward_calls=len(rows),forward_seconds=time.monotonic()-tick,
                input_tokens=sum(r['n_processed'] for r in rows))
            dump(path,result);return result

        def train(reg):
            state,arm=reg['state'],reg['data'];out=OUT/reg['run_id'];out.mkdir(exist_ok=True)
            final=out/'run_manifest_final.json'
            identity=dict(run_id=reg['run_id'],data_sha256=sha256_file(RELEASE/(arm+'.jsonl')),
                parent=parent_identity['parameter_digest'],source_commit=src['source_commit'],base=base_hash)
            if final.exists():
                record=_read(final)
                if record['status']!='completed' or record['identity']!=identity:raise ValueError('Training endpoint identity changed')
                checkpoints[state]=out/'checkpoint_256';restore_adapter(model,checkpoints[state])
                progress['runs']=[r for r in progress['runs'] if r['state']!=state]+[record];publish();return
            restore_adapter(model,parent);ensure_parent_reference(out,parent)
            initial=out/'run_manifest.json'
            if initial.exists():
                record=_read(initial)
                if record['identity']!=identity:raise ValueError('Training identity changed')
            else:
                record=dict(**reg,identity=identity,status='running',started_at_utc=stamp(),
                    parent_adapter=parent_identity['parameter_digest'],optimizer_reset=True,scheduler_reset=True,
                    checkpoint0_is_parent_reference=True,budget=doses[arm],seed=17,
                    source_commit=src['source_commit'],data_sha256=identity['data_sha256'])
                dump(initial,record)
            before={view:nll_once(out/f'reference_{view}_before.json',encoded[arm][section]) for view,section in [('H',slice(0,512)),('F',slice(512,None))]}
            pointer=out/'recovery/latest.json';cursor=_read(pointer)['step'] if pointer.exists() else 0
            history=[]
            # Midpoint evaluates its immutable128 adapter even when a prior process
            # interrupted just after the training commit or during its decoding.
            def midpoint():
                restore_adapter(model,out/'checkpoint_128');ev(events[f'{state}_midpoint_H_greedy'])
            if cursor>=128:midpoint()
            while cursor<256:
                end=min(256,((cursor//16)+1)*16)
                estimate=max(4.,sum(r['seconds'] for r in history[-16:])/len(history[-16:])*1.5) if history else 8.
                admit((end-cursor)*estimate+60)
                result=train_segment(model,encoded[arm],inputs['schedules'][arm],inputs['learning_rates'],tokenizer,out,
                    identity=identity,end_step=end,deadline=deadline)
                cursor=result['step'];history=result['cumulative_history']
                atomic_json(out/'segment_progress.json',result)
                progress['runs']=[r for r in progress['runs'] if r['state']!=state]+[{**reg,'status':'running','completed_updates':cursor}];publish()
                if cursor<end:raise SegmentPause('Saved partial training segment')
                if cursor==128:midpoint()
            # A final update may have been committed before the prior process's
            # final manifest; reload full optimizer/RNG/adapter before final NLL.
            if not history:
                result=train_segment(model,encoded[arm],inputs['schedules'][arm],inputs['learning_rates'],tokenizer,out,
                    identity=identity,end_step=256,deadline=deadline);history=result['cumulative_history']
            after={view:nll_once(out/f'reference_{view}_after.json',encoded[arm][section]) for view,section in [('H',slice(0,512)),('F',slice(512,None))]}
            if len(history)!=256 or any(sum(r[field] for r in history)!=doses[arm][wanted] for field,wanted in [('supervised_tokens','supervised_response_tokens'),('processed_tokens','processed_nonpadding_tokens')]):
                raise ValueError('Actual optimizer dose differs from frozen schedule')
            checkpoint=out/'checkpoint_256';actual=parameter_digest(model,True);restored=restore_adapter(model,checkpoint)
            if actual!=restored['parameter_digest'] or parameter_digest(model)!=base_hash:raise ValueError('Final weights/base changed')
            from .generation import _atomic
            _atomic(out/'train_history.jsonl',history,jsonl=True)
            record.update(status='completed',completed_updates=256,finished_at_utc=stamp(),final_adapter=actual,
                checkpoint=str(checkpoint),reference_nll_before=before,reference_nll_after=after,
                recoverable_state=_read(pointer),frozen_base_unchanged=True)
            dump(final,record);checkpoints[state]=checkpoint
            progress['runs']=[r for r in progress['runs'] if r['state']!=state]+[record];publish()

        # No metric value affects this fixed queue.
        for interface in 'FHC':ev(events[f'E031_{interface}_greedy'])
        operators('E031')
        for interface in 'FH':ev(events[f'E031_{interface}_sampled'])
        for reg in regs:train(reg)
        # Always recover midpoint views if the logical run was finalized before
        # this process started; scientific endpoints remain fixed at256.
        for reg in regs:
            restore_adapter(model,OUT/reg['run_id']/'checkpoint_128');ev(events[f"{reg['state']}_midpoint_H_greedy"])
        for state in STATES[1:]:
            restore_adapter(model,checkpoints[state])
            for interface in 'FHC':ev(events[f'{state}_{interface}_greedy'])
            operators(state)
            for interface in 'FH':ev(events[f'{state}_train_{interface}_greedy'])
        for state in STATES[1:]:
            restore_adapter(model,checkpoints[state])
            for interface in 'FH':ev(events[f'{state}_{interface}_sampled'])
        if len(progress['evaluations'])!=21 or sum(r['completed_records'] for r in progress['evaluations'])!=3344 or progress['training_updates']!=512:
            raise ValueError('Completed queue count changed')
        if not 3344<=budget.used<=3600 or progress['recorded_contexts']!=288 or parameter_digest(model)!=base_hash:
            raise ValueError('Completed queue budget/forward/base identity changed')
        progress['status']='completed';return 0
    except (SegmentPause,TimeoutError) as exc:
        progress.update(status='paused_resource',reason=str(exc));return 75
    except BaseException as exc:
        progress.update(status='failed_hard',exception_type=type(exc).__name__,exception_message=str(exc));raise
    finally:
        progress.update(seconds=time.monotonic()-started,finished_at_utc=stamp(),
            peak_memory_allocated_bytes=torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None)
        # Read actual durable run cursors even if a signal bypassed publish().
        for reg in regs:
            pointer=OUT/reg['run_id']/'recovery/latest.json'
            if pointer.exists() and not any(r['state']==reg['state'] and r.get('status')=='completed' for r in progress['runs']):
                progress['runs']=[r for r in progress['runs'] if r['state']!=reg['state']]+[{**reg,'status':'partial','completed_updates':_read(pointer)['step']}]
        publish();atomic_json(OUT/'run_manifest_final.json',progress)


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--snapshot');p.add_argument('--endpoint-root');a=p.parse_args()
    if a.worker:raise SystemExit(worker(a.snapshot,a.endpoint_root))
    print(json.dumps(dry_run(),indent=2))

if __name__=='__main__':main()
