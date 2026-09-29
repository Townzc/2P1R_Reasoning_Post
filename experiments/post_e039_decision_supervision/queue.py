"""Finite Stage A diagnostics followed by four equal-dose continuations."""
import argparse
from contextlib import nullcontext
import json
import math
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
from src.sft_data import sha256_file
from .generation import run_event, _caller_state, _read, target_seed, _atomic
from .runtime import prepare_encoded, train_segment
from .decision_spans import annotate

ROOT=Path('experiments/post_e039_decision_supervision')
RELEASE=ROOT/'release_v1'
OUT=Path(os.environ.get('DECISION_TRAINING_OUTPUT','runs/post_e039_decision_supervision_v1'))
STATES=('E038','E039','S-U','S-D','P-U','P-D')
BASE_SHA='0fe3fc99f6a3895a6896bf62fdd42853481646a93b45aa167e1084fa116ae142'
PARENTS={'E038':('goal_train_e038_r1','92da3a11e65e0de78012b6ab38d117554faa929f700dd95ed3f2df3c611fc5ae'),
         'E039':('goal_train_e039_r1','a97f622c76c5817f8f283aa2f0034e19d438e8dd0bbb91026d443f3ba2f23bba')}

class SegmentPause(Exception):pass


def event(state,interface,decoding='greedy',view='eval'):
    key={'eval':'eval_'+interface,'stage_a':'train_'+interface,
         'endpoint':'train_F64' if interface=='F' else 'train_H',
         'midpoint':'midpoint_'+interface}[view]
    questions={'eval':96,'stage_a':256 if interface=='F' else 64,
               'endpoint':64,'midpoint':16}[view]
    samples=4 if decoding=='sampled' else 1
    return dict(name=f'{state}_{view}_{interface}_{decoding}',state=state,interface=interface,
        decoding=decoding,view=view,data_key=key,questions=questions,samples=samples,
        sampling=samples==4,generations=questions*samples,expected_records=questions*samples,
        evaluation_seed=2026091713,
        checkpoint_step=256 if state in PARENTS else 64 if view=='midpoint' else 128)


def evaluation_queue():
    events=[event(s,i,view='stage_a') for s in STATES[:2] for i in 'FH']
    events += [event(s,i,mode) for s in STATES for i,mode in [('H','greedy'),('F','greedy'),('F','sampled')]]
    events += [event(s,i,view=v) for s in STATES[2:] for v in ('endpoint','midpoint') for i in 'FH']
    if len(events)!=38 or sum(e['generations'] for e in events)!=4736:
        raise ValueError('Frozen finite evaluation accounting changed')
    return events


def frozen_inputs():
    from .data import load_inputs
    manifest=verify_manifest(RELEASE);inputs=load_inputs();regs=_read(ROOT/'registration.json')['entries']
    if [(r['state'],r['data'],r['parent'],r['objective'],r['updates']) for r in regs]!=[
        ('S-U','single','E038','U',128),('S-D','single','E038','D',128),
        ('P-U','paired','E039','U',128),('P-D','paired','E039','D',128)]:
        raise ValueError('The complete registered four-arm factorial is required')
    if len({r['run_id'] for r in regs})!=4:raise ValueError('Distinct training identities required')
    counts=dict(single=1024,paired=1024,eval_F=96,eval_H=96,train_F=256,train_F64=64,
        train_H=64,midpoint_F=16,midpoint_H=16)
    for key,count in counts.items():
        if len(inputs[key])!=count:raise ValueError('Frozen input shape changed: '+key)
    frozen=inputs['learning_rates'];computed=learning_rates(128)
    if len(frozen)!=128 or any(not math.isfinite(x) or x<=0 or abs(x-y)>2*max(math.ulp(x),math.ulp(y)) for x,y in zip(frozen,computed)):
        raise ValueError('Frozen128-step LR differs beyond2ULP validation roundoff')
    for arm in ('single','paired'):
        schedule=inputs['schedules'][arm]
        if len(schedule)!=128:raise ValueError('Exactly128 additional updates required')
        for batch in schedule:
            if len(batch)!=16 or sum(i<512 for i in batch)!=8 or len(set(batch))!=16:
                raise ValueError('Every update must use8H+8F distinct slots')
        for start in (0,64):
            if sorted(i for batch in schedule[start:start+64] for i in batch)!=list(range(1024)):
                raise ValueError('Every source slot must occur once per epoch')
    if inputs['single'][512:]!=inputs['paired'][512:]:raise ValueError('Shared original F changed')
    return inputs,regs,manifest


def dry_run():
    inputs,regs,_=frozen_inputs()
    return dict(status='prepared_not_run',runs=regs,training_updates=512,updates=512,
        planned_generations=4736,generation_cap=5000,forward_sequence_equivalent_cap=16384,
        planned_forward_sequence_equivalents=7552,diagnostic_views=28,
        release_manifest_sha256=sha256_file(RELEASE/'manifest.json'),evaluations=evaluation_queue(),
        parents={k:v[1] for k,v in PARENTS.items()},training_seed=17,evaluation_seed=2026091713,
        bootstrap_seed=2026091714,target_seeds={str(i):target_seed(i) for i in (0,1)},
        outcomes_affect_queue=False,hard_consistency_gate='Stage A same-prefix/logits agreement and all H masks valid',
        admission='Next recoverable16-update unit or fixed generation/forward record; no accuracy gate')


def ensure_parent_reference(out,parent):
    link=Path(out)/'checkpoint_0';parent=Path(parent).resolve()
    if link.is_symlink():
        if link.resolve()!=parent:raise ValueError('Step0 parent reference changed')
    elif link.exists():raise ValueError('Step0 must be the exact parent reference')
    else:link.symlink_to(parent,target_is_directory=True)


def worker(snapshot,endpoint_root):
    if os.environ.get('DECISION_TRAINING_BOUNDED')!='post_e039_decision_supervision_v1':
        raise ValueError('Bounded launcher required')
    from .launcher import GenerationBudget,ForwardBudget,source
    from .diagnostics import run_decomposition,run_candidates,observe_greedy_alignment,make_alignment_cases
    import torch
    from transformers import AutoModelForCausalLM
    inputs,regs,release=frozen_inputs();events={e['name']:e for e in evaluation_queue()}
    deadline=float(os.environ['DECISION_TRAINING_DEADLINE']);src=source(os.environ['DECISION_TRAINING_PUBLISHED_COMMIT'])
    parent_paths={state:Path(endpoint_root)/run/'checkpoint_256' for state,(run,_) in PARENTS.items()}
    parent_ids={}
    for state,path in parent_paths.items():
        identity=_read(path/'checkpoint_identity.json')
        if identity['parameter_digest']['sha256']!=PARENTS[state][1]:raise ValueError('ExactE038/E039 parent required')
        for name,sha in identity['files_sha256'].items():
            if Path(name).name!=name or sha256_file(path/name)!=sha:raise ValueError('Parent bytes changed')
        parent_ids[state]=identity
    OUT.mkdir(parents=True,exist_ok=True);budget=GenerationBudget(OUT/'generation_ledger.json');forwards=ForwardBudget(OUT/'forward_ledger.json')
    release_hash=sha256_file(RELEASE/'manifest.json')
    immutable=dict(**src,release_manifest_sha256=release_hash,parents=parent_ids,base_parameter_sha256=BASE_SHA,
        model_revision=REVISION,seeds=dict(training=17,evaluation=2026091713,bootstrap=2026091714,
        target_substreams={str(i):target_seed(i) for i in (0,1)}),
        inference='FP32 parameters/BF16 autocast/SDPA/TF32 off',scientific_selection_gates=[])
    initial=OUT/'run_manifest.json'
    if initial.exists():
        if _read(initial)!=immutable:raise ValueError('Execution identity changed on resume')
    else:dump(initial,immutable)
    progress=dict(**immutable,status='running',runs=[],evaluations=[],diagnostics=[],training_updates=0,
        stage_a_alignment_passed=False,diagnostic_views_complete=False)
    started=time.monotonic();model=None

    def publish():
        progress.update(training_updates=sum(r.get('completed_updates',0) for r in progress['runs']),
            generation_attempts=budget.used,forward_sequence_equivalents=forwards.used,
            updated_at_utc=stamp(),disk_free_gib=shutil.disk_usage(OUT).free/2**30)
        atomic_json(OUT/'progress.json',progress)
    def admit(seconds):
        if time.time()+seconds+30>deadline or shutil.disk_usage(OUT).free/2**30<1.25:
            raise SegmentPause('Time/disk insufficient for next durable unit')
    def on_signal(*_):raise TimeoutError('Bounded signal; preserve durable cursors')
    signal.signal(signal.SIGTERM,on_signal)
    try:
        admit(150)
        tokenizer,tok=verified_tokenizer(Path(snapshot));tokenizer.pad_token=tokenizer.eos_token
        spans={arm:inputs['spans_'+arm] for arm in ('single','paired')}
        encoded={arm:prepare_encoded(inputs[arm],spans[arm],tokenizer) for arm in ('single','paired')}
        other_spans={key:[annotate(row,tokenizer) for row in inputs[key]] for key in ('eval_H','train_H','midpoint_H','midpoint_F')}
        doses={arm:dict(supervised_response_tokens=sum(encoded[arm][i]['n_supervised'] for b in inputs['schedules'][arm] for i in b),
            processed_nonpadding_tokens=sum(encoded[arm][i]['n_processed'] for b in inputs['schedules'][arm] for i in b),
            encoded_rows_sha256=digest(encoded[arm])) for arm in ('single','paired')}
        for arm in ('single','paired'):
            for field in ('supervised_response_tokens','processed_nonpadding_tokens'):
                if doses[arm][field]!=inputs['dose'][arm][field]:
                    raise ValueError('Serialized runtime dose differs from frozen release')
        progress.update(tokenizer=tok,actual_encoded_doses=doses)
        torch.manual_seed(17);torch.set_num_threads(8);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        base=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.float32,attn_implementation='sdpa',local_files_only=True).cuda()
        model=attach(base);model.eval();base_hash=parameter_digest(model)
        if base_hash['sha256']!=BASE_SHA:raise ValueError('Frozen base changed')
        checkpoints=dict(parent_paths);progress['base_parameter_digest']=base_hash

        def ev(e,alignment=False):
            rows=inputs[e['data_key']];path=OUT/(e['name']+'.jsonl');adapter=parameter_digest(model,True)
            identity=dict(model_hash=adapter['sha256'],split_hash=release_hash,batch_time_reserve_seconds=120.,exit_reserve_seconds=30.)
            observer=nullcontext()
            if alignment:
                key='midpoint_'+e['interface'];cases=make_alignment_cases(inputs[key],other_spans[key],tokenizer)
                observer=observe_greedy_alignment(model,tokenizer,cases,OUT/'alignment'/(e['name']+'.json'),identity=identity)
            with observer:
                result=run_event(model,tokenizer,rows,path,e,identity,10000,budget,deadline)
            view=dict(**e,status=result['status'],completed_records=result['completed_records'],adapter=adapter,
                predictions_sha256=sha256_file(path),release_manifest_sha256=release_hash,reason=result['reason'],
                batch_timings=result['batch_timings'],substreams=result.get('substreams',[]))
            atomic_json(path.with_suffix('.summary.json'),view)
            progress['evaluations']=[r for r in progress['evaluations'] if r['name']!=e['name']]+[view];publish()
            if result['status']!='completed':raise SegmentPause(result['reason'])

        def diag(state,kind,rows,row_spans=None):
            path=OUT/'diagnostics'/state/(kind+'.json');path.parent.mkdir(parents=True,exist_ok=True)
            identity=dict(state=state,adapter_sha256=parameter_digest(model,True)['sha256'],
                release_manifest_sha256=release_hash,rows_sha256=digest(rows))
            with _caller_state(model):
                model.eval()
                if kind.endswith('candidates'):
                    result=run_candidates(model,rows,path,identity=identity,forward_budget=forwards,deadline=deadline)
                else:result=run_decomposition(model,tokenizer,rows,row_spans,path,identity=identity,forward_budget=forwards,deadline=deadline)
            record=dict(name=state+'/'+kind,state=state,kind=kind,path=str(path.relative_to(OUT)),
                **{k:v for k,v in result.items() if k!='records'})
            progress['diagnostics']=[r for r in progress['diagnostics'] if r['name']!=record['name']]+[record];publish()
            if result['status']!='completed':raise SegmentPause('Partial registered forward view')

        def contexts(records):
            rows={r['problem_id']:r for key in ('eval_H','train_H') for r in inputs[key]}
            return [dict(problem_id=r['problem_id'],group_id=rows[r['problem_id']]['group_id'],
                target_index=rows[r['problem_id']]['target_index'],context_ids=r['prefix_input_ids'],
                candidates=r['candidates'],correct_operator=r['correct_operator']) for r in records]

        # Stage A is complete before any additional training, irrespective of scores.
        for state,arm in [('E038','single'),('E039','paired')]:
            restore_adapter(model,parent_paths[state])
            for interface in 'FH':ev(events[f'{state}_stage_a_{interface}_greedy'],alignment=True)
            for interface,section in [('H',slice(0,512)),('F',slice(512,None))]:
                diag(state,'reference_'+interface,inputs[arm][section],spans[arm][section])
            diag(state,'train_H',inputs['train_H'],other_spans['train_H'])
            diag(state,'train_H_candidates',contexts(other_spans['train_H']))
        alignment_files=[OUT/'alignment'/f'{s}_stage_a_{i}_greedy.json' for s in STATES[:2] for i in 'FH']
        alignment_records=[_read(p) for p in alignment_files]
        if any(r.get('status')!='passed' or r.get('genuine_mismatches',0) for r in alignment_records):
            raise ValueError('Stage A actual same-prefix effective-logit consistency failed')
        progress['stage_a_alignment_passed']=True;publish()

        def train(reg):
            state,arm=reg['state'],reg['data'];out=OUT/reg['run_id'];out.mkdir(exist_ok=True)
            final=out/'run_manifest_final.json';parent=parent_paths[reg['parent']]
            identity=dict(run_id=reg['run_id'],data_sha256=sha256_file(RELEASE/(arm+'.jsonl')),
                parent=parent_ids[reg['parent']]['parameter_digest'],source_commit=src['source_commit'],
                base=base_hash,objective=reg['objective'],decision_spans_sha256=digest(spans[arm]))
            if final.exists():
                record=_read(final)
                if record['status']!='completed' or record['identity']!=identity:raise ValueError('Endpoint identity changed')
                checkpoints[state]=out/'checkpoint_128';restore_adapter(model,checkpoints[state])
                progress['runs']=[r for r in progress['runs'] if r['state']!=state]+[record];publish();return
            restore_adapter(model,parent);ensure_parent_reference(out,parent)
            initial=out/'run_manifest.json'
            if initial.exists():
                record=_read(initial)
                if record['identity']!=identity:raise ValueError('Training identity changed')
            else:
                record=dict(**reg,identity=identity,status='running',started_at_utc=stamp(),
                    parent_adapter=parent_ids[reg['parent']]['parameter_digest'],
                    optimizer_reset=True,scheduler_reset=True,checkpoint0_is_parent_reference=True,
                    budget=doses[arm],seed=17,source_commit=src['source_commit'])
                dump(initial,record)
            pointer=out/'recovery/latest.json';cursor=_read(pointer)['step'] if pointer.exists() else 0;history=[]
            def midpoint():
                restore_adapter(model,out/'checkpoint_64')
                for interface in 'FH':ev(events[f'{state}_midpoint_{interface}_greedy'])
            if cursor>=64:midpoint()
            while cursor<128:
                end=min(128,((cursor//16)+1)*16)
                estimate=max(4.,sum(r['seconds'] for r in history[-16:])/len(history[-16:])*1.5) if history else 8.
                admit((end-cursor)*estimate+60)
                result=train_segment(model,encoded[arm],inputs['schedules'][arm],inputs['learning_rates'],tokenizer,out,
                    identity=identity,objective=reg['objective'],end_step=end,deadline=deadline)
                cursor=result['step'];history=result['cumulative_history'];atomic_json(out/'segment_progress.json',result)
                progress['runs']=[r for r in progress['runs'] if r['state']!=state]+[{**reg,'status':'running','completed_updates':cursor}];publish()
                if cursor<end:raise SegmentPause('Saved partial training segment')
                if cursor==64:midpoint()
            if not history:
                result=train_segment(model,encoded[arm],inputs['schedules'][arm],inputs['learning_rates'],tokenizer,out,
                    identity=identity,objective=reg['objective'],end_step=128,deadline=deadline);history=result['cumulative_history']
            if len(history)!=128 or any(sum(r[field] for r in history)!=doses[arm][wanted] for field,wanted in [('supervised_tokens','supervised_response_tokens'),('processed_tokens','processed_nonpadding_tokens')]):
                raise ValueError('Actual optimizer dose differs from frozen schedule')
            checkpoint=out/'checkpoint_128';actual=parameter_digest(model,True);restored=restore_adapter(model,checkpoint)
            if actual!=restored['parameter_digest'] or parameter_digest(model)!=base_hash:raise ValueError('Final weights/base changed')
            _atomic(out/'train_history.jsonl',history,jsonl=True)
            record.update(status='completed',completed_updates=128,finished_at_utc=stamp(),final_adapter=actual,
                checkpoint=str(checkpoint),recoverable_state=_read(pointer),frozen_base_unchanged=True)
            dump(final,record);checkpoints[state]=checkpoint
            progress['runs']=[r for r in progress['runs'] if r['state']!=state]+[record];publish()

        for reg in regs:train(reg)
        for reg in regs:
            state,arm=reg['state'],reg['data'];restore_adapter(model,OUT/reg['run_id']/'checkpoint_64')
            for interface in 'FH':ev(events[f'{state}_midpoint_{interface}_greedy'])
            restore_adapter(model,checkpoints[state])
            for interface in 'FH':ev(events[f'{state}_endpoint_{interface}_greedy'])
            for interface,section in [('H',slice(0,512)),('F',slice(512,None))]:
                diag(state,'reference_'+interface,inputs[arm][section],spans[arm][section])
        for state in STATES:
            restore_adapter(model,checkpoints[state])
            for interface in 'HF':ev(events[f'{state}_eval_{interface}_greedy'])
            diag(state,'eval_H',inputs['eval_H'],other_spans['eval_H'])
            diag(state,'eval_H_candidates',contexts(other_spans['eval_H']))
        for state in STATES:
            restore_adapter(model,checkpoints[state]);ev(events[f'{state}_eval_F_sampled'])
        if len(progress['evaluations'])!=38 or sum(r['completed_records'] for r in progress['evaluations'])!=4736 or progress['training_updates']!=512:
            raise ValueError('Completed finite queue counts changed')
        if len(progress['diagnostics'])!=28 or any(r['status']!='completed' for r in progress['diagnostics']):
            raise ValueError('Registered diagnostics incomplete')
        progress['diagnostic_views_complete']=True
        if not 4736<=budget.used<=5000 or forwards.used>16384 or parameter_digest(model)!=base_hash:
            raise ValueError('Budget/base identity changed')
        progress['status']='completed';return 0
    except (SegmentPause,TimeoutError) as exc:
        progress.update(status='paused_resource',reason=str(exc));return 75
    except BaseException as exc:
        progress.update(status='failed_hard',exception_type=type(exc).__name__,exception_message=str(exc));raise
    finally:
        progress.update(seconds=time.monotonic()-started,finished_at_utc=stamp(),
            peak_memory_allocated_bytes=torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None)
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
