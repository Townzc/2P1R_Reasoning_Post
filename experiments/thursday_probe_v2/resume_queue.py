"""Registered post-E030 continuation; admit only the next durable unit."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import time

from experiments.thursday_probe.common import dump, stamp, verify_manifest, SEEDS
from experiments.thursday_probe.lora import attach, parameter_digest
from experiments.thursday_probe.arithmetic_eval import summarize
from experiments.thursday_probe_v2.config import DATA, RELEASE, REVISION, STATES, evaluation_queue
from experiments.thursday_probe_v2.queue import load_inputs, source
from experiments.thursday_probe_v2.training import restore_adapter, atomic_json
from experiments.thursday_probe_v2.resumable_training import train_segment
from experiments.thursday_probe_v2.resumable_generation import run_batches, _caller_state
from experiments.thursday_probe_v2.resume_resources import ResumeGenerationBudget, admit_unit
from experiments.thursday_probe_v2.resume_diagnostics import RESUME_RELEASE, load_generation_rows, load_reference_rows
from scripts.audit_family_matching import verified_tokenizer
from src.relation_experiment import reference_nll
from src.sft_data import encode_row, sha256_file, read_jsonl

OUT = Path('runs/thursday_arithmetic_resume_r1')
BASE_SHA = '0fe3fc99f6a3895a6896bf62fdd42853481646a93b45aa167e1084fa116ae142'
C0_SHA = 'e93d954e27a0996330492e59b642d6bd50cdb2981d81ccf0622bae3e705796c2'


class SegmentPause(Exception):
    """A durable cursor can be resumed within the same cumulative envelope."""


def frozen_inputs():
    inputs, regs, schedules, lrs, doses = load_inputs()
    verify_manifest(RESUME_RELEASE)
    inputs['train_diagnostic'] = load_generation_rows()
    events = [e for e in evaluation_queue() if e['state'] not in ('C0', 'calibration')]
    events += json.loads((RESUME_RELEASE/'evaluation_queue.json').read_text())
    regs = [r for r in regs if r['state'] != 'calibration']
    if sum(r['updates'] for r in regs) != 1088 or sum(e['generations'] for e in events) != 4192:
        raise ValueError('Six-run continuation changed')
    return inputs, regs, schedules, lrs, doses, events


def dry_run():
    _, regs, _, _, _, events = frozen_inputs()
    return dict(status='prepared_not_run', runs=regs, updates=1088, new_generations=4192,
        historical_generations=592, planned_cumulative_generations=4784, cap=4864,
        events=events, admission='Next saveable training segment or fixed evaluation batch only',
        first_profiles='First registered probe batch and discovery_sampled batch after each parent',
        outcomes_affect_queue=False, calibration_repeated=False,
        diagnostic_manifest_sha256=sha256_file(RESUME_RELEASE/'manifest.json'))


def worker(snapshot, initial_checkpoint):
    if os.environ.get('THU_RESUME_BOUNDED') != OUT.name:
        raise ValueError('Bounded launcher required')
    import torch
    from transformers import AutoModelForCausalLM
    inputs, regs, schedules, lrs, doses, event_list = frozen_inputs()
    events = {e['name']: e for e in event_list}
    deadline = float(os.environ['THU_RESUME_DEADLINE'])
    OUT.mkdir(parents=True, exist_ok=True)
    provenance = source()
    immutable = OUT/'run_manifest.json'
    if immutable.exists():
        initial = json.loads(immutable.read_text())
        if any(initial[k] != provenance[k] for k in provenance):
            raise ValueError('Published execution source changed on resume')
    else:
        initial = dict(**provenance, started_at_utc=stamp(), model_revision=REVISION,
            data_manifest_sha256=sha256_file(DATA/'manifest.json'),
            release_manifest_sha256=sha256_file(RELEASE/'manifest.json'),
            diagnostic_manifest_sha256=sha256_file(RESUME_RELEASE/'manifest.json'),
            original_initial_checkpoint=str(initial_checkpoint), initial_adapter_sha256=C0_SHA,
            original_model_sha256=BASE_SHA, seeds=SEEDS, prior_actual_generations=592,
            inference='FP32 parameters, BF16 autocast, SDPA, TF32 off',
            scientific_selection_gates=[], admission='next_durable_unit_only')
        dump(immutable, initial)
    progress = {**initial, 'status':'running', 'runs':[], 'evaluations':[]}
    budget = ResumeGenerationBudget(OUT/'generation_ledger.json')
    started = time.monotonic()

    def publish():
        progress.update(reserved_generations=budget.used, updated_at_utc=stamp(),
            disk_free_gib=shutil.disk_usage(OUT).free/2**30)
        atomic_json(OUT/'progress.json', progress)

    def admit(seconds):
        if not admit_unit(deadline, seconds, shutil.disk_usage(OUT).free/2**30, minimum_free_gib=1.25):
            raise SegmentPause('Insufficient time or disk for next saveable unit')

    def on_signal(*_):
        raise TimeoutError('Bounded worker termination signal')

    signal.signal(signal.SIGTERM, on_signal)
    try:
        admit(180)
        tokenizer, tok = verified_tokenizer(Path(snapshot)); tokenizer.pad_token=tokenizer.eos_token
        encoded = {n:[encode_row(r, tokenizer, 1024) for r in inputs[n]]
                   for n in ('surface','paths','prep_control','prep_bridge')}
        torch.manual_seed(17); torch.set_num_threads(8)
        torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False
        torch.cuda.reset_peak_memory_stats()
        base = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.float32,
            attn_implementation='sdpa', local_files_only=True).cuda()
        model = attach(base)
        if any(p.dtype != torch.float32 for p in model.parameters()):
            raise ValueError('Frozen precision differs')
        base_hash=parameter_digest(model)
        if base_hash['sha256'] != BASE_SHA:
            raise ValueError('Original base model digest differs')
        original=restore_adapter(model, Path(initial_checkpoint))
        if original['parameter_digest']['sha256'] != C0_SHA:
            raise ValueError('Exact original C0 initialization required')
        progress.update(tokenizer=tok, base_parameter_digest=base_hash, initial_adapter=original)
        checkpoints={'C0':Path(initial_checkpoint)}

        def nll_once(path, rows):
            if path.exists(): return json.loads(path.read_text())
            admit(180)
            tick=time.monotonic()
            with _caller_state(model): result=reference_nll(model, rows, tokenizer, 1)
            result['forward_seconds']=time.monotonic()-tick
            dump(path,result)
            return result

        def ev(state, view, first_batch=False):
            name=state+'_'+view; event=events[name]; path=OUT/(name+'.jsonl')
            key='discovery_problems' if view.startswith('discovery_') else view
            split_path=(RESUME_RELEASE/'train_diagnostic.jsonl' if key=='train_diagnostic' else
                (RELEASE if key in ('sentinel','midpoint') else DATA)/(key+'.jsonl'))
            summary_path=OUT/(name+'.summary.json')
            if summary_path.exists():
                record=json.loads(summary_path.read_text())
                if record['status']=='completed':
                    if record['predictions_sha256'] != sha256_file(path):
                        raise ValueError('Completed prediction file changed')
                    progress['evaluations']=[r for r in progress['evaluations'] if r['name']!=name]+[record]
                    return
            # A first-batch profile already committed is never followed by a second
            # batch merely because the launcher resumed the parent stage.
            resume_progress=path.with_suffix('.resume')/'progress.json'
            committed=json.loads(resume_progress.read_text()).get('completed_batches',0) if resume_progress.exists() else 0
            if first_batch and committed>=1:return
            adapter=parameter_digest(model,True)
            while True:
                timings=[]
                for p in (path.with_suffix('.resume')/'batches').glob('*.timing.json'):
                    timings.append(json.loads(p.read_text()))
                # Separate measured profiles per model/task/view. Initial reserve
                # covers a full512-token batch and CPU scoring without changing it.
                reserve=max(120.,max((t['generation_seconds']+(t.get('cpu_score_seconds') or 0)
                    for t in timings),default=0)*1.5+30)
                admit(reserve+30)
                result=run_batches(model,tokenizer,inputs[key],path,event,
                    dict(model_hash=adapter['sha256'],split_hash=sha256_file(split_path),
                        batch_time_reserve_seconds=reserve,exit_reserve_seconds=30),
                    1 if first_batch else (event['generations']+7)//8,budget,deadline)
                record=dict(**event,status=result['status'],completed_records=len(result['records']),
                    metrics=summarize(result['records']) if result['records'] else None,
                    predictions_sha256=sha256_file(path),adapter=adapter,
                    batch_timings=result['batch_timings'],seconds=sum(t['generation_seconds'] for t in result['batch_timings']),
                    reason=result['reason'],request_count=len(result['request_ids']))
                atomic_json(summary_path,record)
                progress['evaluations']=[r for r in progress['evaluations'] if r['name']!=name]+[record]
                publish()
                print(json.dumps(dict(event=name,status=result['status'],completed_records=len(result['records']),
                    cumulative_generations=budget.used,disk_free_gib=progress['disk_free_gib'])),flush=True)
                if result['status']=='completed' or first_batch:return
                if result['new_batches']==0:raise SegmentPause(result['reason'])

        def training_run(reg):
            state,parent,name=reg['state'],reg['parent'],reg['data']
            out=OUT/reg['run_id']; out.mkdir(exist_ok=True)
            final=out/'run_manifest_final.json'
            if final.exists():
                record=json.loads(final.read_text())
                if record['status']!='completed':raise ValueError('Unexpected terminal run record')
                checkpoints[state]=out/f"checkpoint_{reg['updates']}"
                restore_adapter(model,checkpoints[state])
                progress['runs'].append(record);publish();return
            parent_identity=restore_adapter(model,checkpoints[parent])
            stage='prep' if state in ('C','B') else 'main'
            identity=dict(run_id=reg['run_id'],data_sha256=sha256_file(DATA/(name+'.jsonl')),
                parent=parent_identity['parameter_digest'],source_commit=initial['source_commit'],base=base_hash)
            record_path=out/'run_manifest.json'
            if record_path.exists():
                record=json.loads(record_path.read_text())
                if record['identity']!=identity:raise ValueError('Training run identity changed')
            else:
                record=dict(**reg,identity=identity,status='running',started_at_utc=stamp(),
                    parent_checkpoint=str(checkpoints[parent]),parent_adapter=parent_identity['parameter_digest'],
                    optimizer_reset=True,scheduler_reset=True,budget=doses[name],seed=17,
                    source_commit=initial['source_commit'],data_sha256=identity['data_sha256'])
                dump(record_path,record)
            nll_before=nll_once(out/'reference_nll_before.json',encoded[name])
            pointer=out/'recovery/latest.json'
            cursor=json.loads(pointer.read_text())['step'] if pointer.exists() else 0
            history=[]
            while cursor<reg['updates']:
                end=min(reg['updates'],((cursor//64)+1)*64) if stage=='main' else 32
                estimated_step=max(8.,sum(r['seconds'] for r in history)/len(history)*1.5) if history else 8.
                admit((end-cursor)*estimated_step+90)
                result=train_segment(model,encoded[name],schedules[stage],lrs[stage],tokenizer,out,
                    identity=identity,end_step=end,deadline=deadline)
                cursor=result['step'];history=result['cumulative_history']
                atomic_json(out/'segment_progress.json',result)
                progress['runs']=[r for r in progress['runs'] if r['state']!=state]+[
                    {**reg,'status':'running','completed_updates':cursor}];publish()
                if cursor<end:raise SegmentPause('Training saved a partial segment')
                if stage=='main' and cursor==128:ev(state,'midpoint')
            if not history:
                # Recovery may have committed the last step immediately before a
                # process interruption, without writing the logical final record.
                result=train_segment(model,encoded[name],schedules[stage],lrs[stage],tokenizer,out,
                    identity=identity,end_step=reg['updates'],deadline=deadline)
                history=result['cumulative_history']
            nll_after=nll_once(out/'reference_nll_after.json',encoded[name])
            checkpoint=out/f"checkpoint_{reg['updates']}"; actual=parameter_digest(model,True)
            restored=restore_adapter(model,checkpoint)
            if restored['parameter_digest']!=actual or parameter_digest(model)!=base_hash:
                raise ValueError('Final checkpoint or frozen base changed')
            if (len(history)!=reg['updates'] or
                sum(r['supervised_tokens'] for r in history)!=doses[name]['supervised_response_tokens'] or
                sum(r['processed_tokens'] for r in history)!=doses[name]['processed_nonpadding_tokens']):
                raise ValueError('Frozen total dose differs')
            history_path=out/'train_history.jsonl'
            history_pending=out/'train_history.jsonl.pending'
            with history_pending.open('w') as f:
                for row in history:f.write(json.dumps(row,sort_keys=True)+'\n')
                f.flush();os.fsync(f.fileno())
            os.replace(history_pending,history_path)
            record.update(status='completed',finished_at_utc=stamp(),final_adapter=actual,
                checkpoint=str(checkpoint),reference_nll_before=nll_before,reference_nll_after=nll_after,
                elapsed_seconds=sum(r['seconds'] for r in history),frozen_base_unchanged=True,
                recoverable_state=json.loads(pointer.read_text()))
            dump(final,record);checkpoints[state]=checkpoint
            progress['runs']=[r for r in progress['runs'] if r['state']!=state]+[record];publish()

        for reg in regs[:2]:
            training_run(reg)
            ev(reg['state'],'probes',True);ev(reg['state'],'discovery_sampled',True)
        for reg in regs[2:]:training_run(reg)
        # Recover an interrupted midpoint evaluation from its immutable128 adapter.
        for reg in regs[2:]:
            restore_adapter(model,OUT/reg['run_id']/'checkpoint_128');ev(reg['state'],'midpoint')
        for state in ('C','B'):
            restore_adapter(model,checkpoints[state]);ev(state,'probes')
        for state in STATES:
            restore_adapter(model,checkpoints[state])
            ev(state,'discovery_sampled');ev(state,'discovery_greedy')
        for state in STATES[2:]:
            restore_adapter(model,checkpoints[state]);ev(state,'sentinel')
        for state in STATES[2:]:
            restore_adapter(model,checkpoints[state]);ev(state,'train_diagnostic')
            for family in ('A','B'):
                path=OUT/(state+'_train_reference_'+family+'.json')
                if not path.exists() and admit_unit(deadline,120,shutil.disk_usage(OUT).free/2**30,1.25):
                    rows=[encode_row(r,tokenizer,1024) for r in load_reference_rows(family)]
                    nll_once(path,rows)
        if (not 4784<=budget.used<=4864 or len(progress['evaluations'])!=len(events) or
            sum(r['completed_records'] for r in progress['evaluations'])!=4192 or
            any(r['status']!='completed' for r in progress['evaluations'])):
            raise ValueError('Completed queue cumulative accounting differs')
        if parameter_digest(model)!=base_hash:raise ValueError('Frozen base changed')
        progress['status']='completed';return 0
    except SegmentPause as exc:
        progress.update(status='partial_resource_pause',reason=str(exc));return 75
    except BaseException as exc:
        progress.update(status='failed_hard',exception_type=type(exc).__name__,exception_message=str(exc))
        raise
    finally:
        progress.update(process_worker_seconds=time.monotonic()-started,finished_at_utc=stamp(),
            peak_memory_allocated_bytes=torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None)
        publish();atomic_json(OUT/'run_manifest_final.json',progress)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',action='store_true');parser.add_argument('--snapshot')
    parser.add_argument('--initial-checkpoint')
    args=parser.parse_args()
    if args.worker:
        if not args.snapshot or not args.initial_checkpoint:parser.error('Worker requires snapshot and initial checkpoint')
        raise SystemExit(worker(args.snapshot,args.initial_checkpoint))
    print(json.dumps(dry_run(),indent=2))


if __name__=='__main__':main()
