"""New owner-authorized 4B checkpoint/resume adapter; original update math retained.

Only infrastructure failures may enter one separately admitted resumed attempt.
Completed prefixes and RNG are restored, never treated as fresh independent runs.
The original train_terminal implementation is not edited or invoked twice.
"""
from pathlib import Path
import math
import time
from experiments.sft_allocation_midpoint import checkpoint
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,manifest
from experiments.p011 import long_checkpoint
from experiments.p011.long_lr_r2_training import ARMS,validate_plan,accumulate
from experiments.p011.long_owner_execution import WholeAnswerJournal


def validate_resume_metadata(state, record, identity, plan, rates):
    step=state.get('step')
    if (state.get('schema') not in ('p011_ext4b_resume_state_v1','p011_complete_training_state_v1')
            or state.get('adaptation_mode')!='full' or state.get('identity')!=identity
            or type(step) is not int or not 0<step<=plan['optimizer_updates']
            or (step!=plan['optimizer_updates'] and step%500!=0)
            or state.get('cursor')!=step or state.get('schedule')!=plan['updates']
            or state.get('lrs')!=rates or record.get('identity_sha256')!=digest(identity)
            or any(state.get(k)!=record.get(k) for k in ('step','supervised_tokens','processed_tokens'))):
        raise ValueError('Foreign/incomplete resume state, schedule, identity or cursor')
    optimizer=state.get('optimizer',{});groups=optimizer.get('param_groups',[])
    if (len(groups)!=1 or not groups[0].get('params')
            or len(groups[0]['params'])!=len(state.get('trainable_names',[]))
            or set(state.get('adapter',{}))!=set(state.get('trainable_names',[]))
            or set(optimizer.get('state',{}))!=set(groups[0]['params'])
            or groups[0]['lr']!=rates[step-1]
            or tuple(groups[0]['betas'])!=(.9,.999) or groups[0]['eps']!=1e-8
            or groups[0]['weight_decay']!=0 or groups[0]['foreach'] is not False):
        raise ValueError('Original optimizer group/slot coverage required on resume')
    import torch
    for name,index in zip(state['trainable_names'],groups[0]['params']):
        tensor=state['adapter'][name];slot=optimizer['state'][index]
        if tensor.dtype!=torch.float32 or not torch.isfinite(tensor).all():
            raise ValueError('Resume trainable tensor invalid')
        for field in ('exp_avg','exp_avg_sq'):
            value=slot[field]
            if value.shape!=tensor.shape or value.dtype!=tensor.dtype or not torch.isfinite(value).all() or (field=='exp_avg_sq' and bool((value<0).any())):
                raise ValueError('Resume AdamW moments invalid')
    for slot in optimizer['state'].values():
        if set(slot)!={'step','exp_avg','exp_avg_sq'} or float(slot['step'])!=step:
            raise ValueError('Resume AdamW step differs from committed cursor')


def load_resume_state(directory, identity, plan, rates):
    import torch
    directory=Path(directory);record=read(directory/'manifest.json');file=directory/'state.pt'
    if record.get('file')!='state.pt' or file.stat().st_size!=record['bytes'] or sha(file)!=record['sha256']:
        raise ValueError('Exact committed resume checkpoint bytes required')
    state=torch.load(file,map_location='cpu',weights_only=True,mmap=True)
    validate_resume_metadata(state,record,identity,plan,rates)
    return state


class ResumableJournal(WholeAnswerJournal):
    def restore_prefix(self, parent_output, step, supervised, processed, cycles):
        if self.cursor or self.pending is not None or self.terminal_cursor:
            raise ValueError('Resume prefix can only initialize a new attempt')
        parent=Path(parent_output);s=p=0;copied=[]
        for i in range(1,step+1):
            name=f'update_{i:05d}';value=read(parent/'completed'/(name+'.json'))
            expected=self.records[i-1];s+=expected['supervised_tokens'];p+=expected['processed_tokens']
            if (any(value.get(k)!=v for k,v in expected.items())
                    or value.get('cumulative_supervised')!=s or value.get('cumulative_processed')!=p):
                raise ValueError('Resume prefix trajectory differs from frozen schedule')
            for folder in ('completed','intents','forecasts'):
                source=parent/folder/(name+'.json');dest=self.out/folder/(name+'.json')
                dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb') as f:f.write(source.read_bytes())
                copied.append({'source':str(source),'destination':str(dest),'sha256':sha(dest)})
        if (s,p)!=(supervised,processed):raise ValueError('Resume dose/cursor mismatch')
        dump(self.out/'RESTORED_PREFIX_BINDING.json',{'parent_output':str(parent),'step':step,'copies':copied,
            'prior_attempt_tail_retained':True,'not_new_optimizer_updates':True})
        if len(cycles)!=step or any(c.get('step')!=i+1 or c.get('seconds',0)<c.get('body_seconds',0)
                or c.get('seconds',0)<=0 for i,c in enumerate(cycles)):
            raise ValueError('Committed resume full-cycle prefix required')
        self.cursor=step;self.total_supervised=s;self.total_processed=p
        self.cycles=list(cycles);self.times=[c['seconds'] for c in cycles]


def train_with_checkpoints(model, tokenizer, optimizer, encoded, plan, rates, arm, out, journal, identity, resume=None):
    """Caller must provide an admitted once-only journal; every step is durably bounded."""
    import torch
    proof = validate_plan(encoded, plan, rates, arm)
    if identity['arm'] != arm or identity['input_plan_sha256'] != proof['plan_sha256']:
        raise ValueError('Runtime identity differs from frozen input plan')
    out = Path(out)
    params = [p for p in model.parameters() if p.requires_grad]
    supervised, processed, resume_step = 0, 0, 0
    if resume is not None:
        state = load_resume_state(resume['checkpoint'], identity, plan, rates)
        checkpoint.restore(model, optimizer, state)
        resume_step = state['step']
        supervised, processed = state['supervised_tokens'], state['processed_tokens']
        journal.restore_prefix(resume['parent_output'], resume_step, supervised, processed, state['ext4b_complete_cycle_prefix'])
        dump(out/'RESTORED_CHECKPOINT.json', {'checkpoint':resume['checkpoint'],
            'step':resume_step, 'manifest_sha256':sha(Path(resume['checkpoint'])/'manifest.json'),
            'full_optimizer_RNG_restored':True, 'schedule_restarted':False})
        del state
        journal.commit()
    for step, indices in enumerate(plan['updates'], 1):
        if step <= resume_step:
            continue
        rows = [encoded[i] for i in indices]
        intent = {'step': step, 'indices': indices, 'lr': rates[step - 1],
                  'supervised_tokens': sum(r['n_supervised'] for r in rows),
                  'processed_tokens': sum(r['n_processed'] for r in rows)}
        journal.begin(f'update_{step:05}', intent)
        journal.commit()
        model.train()
        optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        start = time.monotonic()
        loss = accumulate(model, rows, journal.check)
        norm = torch.nn.utils.clip_grad_norm_(params, 1.)
        if not torch.isfinite(norm) or not math.isfinite(loss):
            raise ValueError('Nonfinite update; preserve attempted unit, no retry')
        for group in optimizer.param_groups:
            group['lr'] = rates[step - 1]
        optimizer.step()
        torch.cuda.synchronize()
        supervised += intent['supervised_tokens']
        processed += intent['processed_tokens']
        journal.end(f'update_{step:05}', {**intent, 'loss': loss, 'gradient_norm': norm.item(),
            'seconds': time.monotonic() - start, 'cumulative_supervised': supervised,
            'cumulative_processed': processed, 'max_allocated_bytes': torch.cuda.max_memory_allocated()})
        journal.commit()
        journal.finish_update()
        if step % 500 == 0 and step < proof['U']:
            journal.check()
            optimizer.zero_grad(set_to_none=True)
            state = checkpoint.snapshot(model, optimizer, identity, step, supervised, processed, rates, plan['updates'])
            state['ext4b_complete_cycle_prefix'] = list(journal.cycles)
            state['schema'] = 'p011_ext4b_resume_state_v1'
            state['adaptation_mode'] = ARMS[arm]['mode']
            state['parameter_payload_meaning'] = 'all_trainable_full_model_parameters'
            saved = long_checkpoint.save(out, state, journal.commit)
            del state
            dump(out/'resume_checkpoints'/f'{step:05d}.json', saved)
            journal.commit()
            journal.check()
    if supervised != proof['B']:
        raise ValueError('Actual full dose differs')
    optimizer.zero_grad(set_to_none=True)
    journal.begin('terminal_state', proof)
    journal.commit()
    state = checkpoint.snapshot(model, optimizer, identity, proof['U'], supervised, processed, rates, plan['updates'])
    state['ext4b_complete_cycle_prefix'] = list(journal.cycles)
    state['schema'] = 'p011_complete_training_state_v1'
    state['adaptation_mode'] = ARMS[arm]['mode']
    state['parameter_payload_meaning'] = 'all_trainable_parameters; full model for full arm, adapters for LoRA'
    state_record = long_checkpoint.save(out, state, journal.commit)
    del state
    journal.end('terminal_state', state_record)
    journal.commit()
    destination = out / 'model_for_vllm'
    journal.begin('terminal_model_export', {'mode': ARMS[arm]['mode'], 'final_state': state_record})
    journal.commit()
    model.eval()
    final = model.merge_and_unload(safe_merge=True) if ARMS[arm]['mode'] == 'lora' else model
    final = final.to(dtype=torch.bfloat16)
    destination.mkdir(exist_ok=False)
    final.save_pretrained(destination, safe_serialization=True)
    tokenizer.save_pretrained(destination)
    exported = {'relative_path': 'model_for_vllm', 'files': manifest(destination),
                'final_state': state_record, 'mode': ARMS[arm]['mode'],
                'optimizer_updates_after_terminal_state': 0, 'evaluation_performed': False}
    dump(out / 'MODEL_EXPORT.json', exported)
    journal.commit()
    journal.end('terminal_model_export', {'proof_sha256': digest(exported)})
    journal.commit()
    return {**proof, 'actual_supervised_tokens': supervised, 'actual_processed_tokens': processed,
            'terminal_state': state_record, 'model_export_sha256': digest(exported)}
