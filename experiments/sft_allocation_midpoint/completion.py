"""Explicit remaining-work admission and stateful continuation; never replay a batch."""
from pathlib import Path
from .common import read, digest, sha, verify, dump


def validate_completion(store, plan, binding, queue, base, audit):
    if (binding['schema'] != 'remaining_work_v1' or
            binding['campaign'] != plan['campaign_id'] or
            binding['parent_campaign'] == plan['campaign_id'] or
            binding['deadline_epoch'] != plan['deadline_epoch'] or
            binding['plan_sha256'] != digest(plan) or
            binding['old_app_stopped'] is not True or binding['old_containers'] != 0 or
            binding['configs_sha256'] != digest([queue, base, audit])):
        raise ValueError('Remaining-work binding differs')
    prefix = 'midpoint/' + binding['parent_campaign'] + '/'
    for name in ('controller', 'breadth_17'):
        terminal = binding['parent_terminals'][name]
        if terminal['status'] != 'failed' or store.get(prefix+'terminal/'+name) != terminal:
            raise ValueError('Parent must be terminal failed: '+name)
    for name in ('mixed_17', 'mixed_23', 'base', 'audit'):
        if any(store.get(prefix+k+'/'+name) is not None for k in ('claim', 'intent', 'terminal')):
            raise ValueError('Unattempted slot was already admitted: '+name)
        if store.get(prefix+'dispatch/'+name+'/intent') is not None:
            raise ValueError('Unattempted dispatch is ambiguous: '+name)
    if [c['run_id'] for c in queue] != ['breadth_17_resume', 'mixed_17', 'mixed_23']:
        raise ValueError('Only the reconciled remaining queue is permitted')
    if (queue[0]['kind'] != 'continue_main' or queue[0]['arm']!='breadth' or queue[0]['seed']!=17 or
            [(c['kind'],c['arm'],c['seed']) for c in queue[1:]] != [('main','mixed',17),('main','mixed',23)] or
            base['kind'] != 'base' or base['run_id'] != 'base' or audit['kind'] != 'audit' or
            set(plan['slots']) != {'breadth_17_resume','mixed_17','mixed_23','base','audit','controller'}):
        raise ValueError('Changed dose or scientific queue')
    return True


def inspect_parent(parent, expected_digest, checkpoint_manifest, *, verify_files=True):
    """Inspect only a terminal, immutable failed attempt with no uncertain update."""
    parent = Path(parent)
    files = read(parent/'failure_manifest.json')
    if digest(files) != expected_digest:
        raise ValueError('Parent failure manifest differs')
    if verify_files:verify(parent, files)
    intents = {p.stem:read(p) for p in (parent/'intents').glob('*.json')}
    done = {p.stem:read(p) for p in (parent/'completed').glob('*.json')}
    updates = {f'update_{i:04d}' for i in range(1,129)}
    if ({k for k in intents if k.startswith('update_')} != updates or
            {k for k in done if k.startswith('update_')} != updates):
        raise ValueError('Training dose is ambiguous or differs from checkpoint128')
    if set(intents)-set(done) != {'observed80_step128_batch_0048'}:
        raise ValueError('Unexpected pending work; do not infer replay permission')
    if set(done)-set(intents):raise ValueError('Completion without an intent')
    expected_eval={f'observed80_step64_batch_{i:04d}' for i in range(0,80,8)} | {f'observed80_step128_batch_{i:04d}' for i in range(0,48,8)}
    if set(done)-updates!=expected_eval or any(done[k]['count']!=8 for k in expected_eval):
        raise ValueError('Saved diagnostic dose differs')
    for k in updates:
        if any(done[k].get(f) != v for f,v in intents[k].items()):
            raise ValueError('Completed update differs from its intent')
    if read(parent/'checkpoint_0128/manifest.json') != checkpoint_manifest:
        raise ValueError('Parent checkpoint changed')
    last = done['update_0128']
    if (last['cumulative_targets'] != checkpoint_manifest['supervised_tokens'] or
            last['cumulative_processed'] != checkpoint_manifest['processed_tokens']):
        raise ValueError('Checkpoint is not the final committed training state')
    if (sum(done[k]['supervised_tokens'] for k in updates)!=last['cumulative_targets'] or
            sum(done[k]['processed_tokens'] for k in updates)!=last['cumulative_processed']):
        raise ValueError('Cumulative dose differs from committed units')
    for start in range(56,80,8):
        if f'observed80_step128_batch_{start:04d}' in intents:
            raise ValueError('Remaining diagnostic batch was already attempted')
    if any(k.startswith(('endpoint431','observed80_step256')) for k in intents):
        raise ValueError('Future evaluation already attempted')
    return intents, done


def continue_main(assets, parent, out, journal, config, environment):
    from . import runtime as rt, checkpoint as ck
    import torch
    parent = Path(parent);out = Path(out)
    recovery = config['recovery']
    intents, done = inspect_parent(parent, recovery['failure_manifest_digest'], recovery['checkpoint_manifest'])
    recipe = read(parent/'recipe.json')
    if recipe['arm'] != 'breadth' or recipe['seed'] != 17:
        raise ValueError('Foreign training trajectory')
    old_environment=read(parent/'environment.json')
    # State restoration is verified exactly; numerical counterfactual identity
    # across a different GPU variant/driver is not claimed.
    if any(environment[k] != old_environment[k] for k in ('versions','cuda','deterministic_algorithms')):
        raise ValueError('Recovery software/CUDA contract differs')
    state=ck.load(parent/'checkpoint_0128',recipe['identity'])
    if state['step']!=128 or state['supervised_tokens']!=262077:
        raise ValueError('Unexpected resume dose')
    inputs=Path(assets)/'inputs';rows=rt.read_jsonl(inputs/'breadth_train.jsonl')
    schedule=read(inputs/'breadth_seed17.json')['updates']
    if state['schedule']!=schedule or state['lrs']!=recipe['lrs'] or config['lrs']!=recipe['lrs']:
        raise ValueError('Recovery schedule changed')
    model,tok=rt.new_model(Path(assets)/'model',17);opt=rt.optimizer_for(model);encoded=rt.encode(rows,tok)
    budget=rt.budget_report(encoded,schedule,1)
    if budget!=recipe['budget']:raise ValueError('Retokenization changed the frozen budget')
    ck.restore(model,opt,state)
    restored=ck.snapshot(model,opt,state['identity'],128,state['supervised_tokens'],state['processed_tokens'],state['lrs'],schedule)
    if not ck.same(state,restored):raise ValueError('Restored full state differs before any new model work')
    dump(out/'restore_verification.json',dict(full_state_equal=True,parent_state_sha256=sha(parent/'checkpoint_0128/state.pt'),
         parent_gpu=old_environment['gpu'],child_gpu=environment['gpu'],counterfactual_bit_exact_claim=False,
         new_optimizer_updates_for_verification=0))
    dump(out/'recipe.json',recipe)
    observed=rt.read_jsonl(inputs/'observed80.jsonl')
    # Rows48:56 were attempted but not returned. They stay unknown forever.
    remaining=rt.evaluate(model,tok,observed[56:],out,'observed80_step128_remaining',journal)
    ck.restore_rng(state['rng'])
    known=[]
    for start in range(0,48,8):known.extend(rt.read_jsonl(parent/'observed80_step128'/f'batch_{start:04d}_scored.jsonl'))
    qc={r['problem_id']:r['task_score']['task_answer_correct'] for r in known};qc.update(remaining['question_correct'])
    for row in observed[48:56]:qc[row['problem_id']]=None
    partial=dict(n=80,known_n=72,unknown_n=8,known_correct=sum(v is True for v in qc.values()),question_correct=qc,
                 interpretation='Interrupted diagnostic: 8 attempted outputs unknown; never regenerated. Not used to choose checkpoint.')
    dump(out/'observed80_step128_reconciled.json',partial)
    curve={'64':read(parent/'observed80_step64/summary.json'),'128':partial}
    def callback(step,model):curve[str(step)]=rt.evaluate(model,tok,observed,out,f'observed80_step{step}',journal)
    history,targets,processed=rt.train(model,tok,opt,encoded,schedule,state['lrs'],out,journal,state['identity'],
         start=128,targets=state['supervised_tokens'],processed=state['processed_tokens'],
         save_steps={160,192,224,256},callback=callback)
    final_nll=rt.nll(model,encoded[:32],tok,journal.check)
    endpoint=rt.evaluate(model,tok,rt.read_jsonl(inputs/'endpoint431.jsonl'),out,'endpoint431',journal)
    return dict(status='completed',arm='breadth',seed=17,committed_updates=256,new_committed_updates=128,
         supervised_tokens=targets,new_supervised_tokens=targets-state['supervised_tokens'],processed_tokens=processed,
         physical_generated_outputs=535,parent_saved_outputs=128,total_saved_outputs=663,unknown_attempted_outputs=8,
         endpoint=endpoint,curve=curve,budget=budget,final_reference_nll=final_nll,
         initial_reference_nll=None,train_seconds=sum(r['seconds'] for r in history)+sum(done[f'update_{i:04d}']['seconds'] for i in range(1,129)),
         recovery=recovery,interpretation='Stateful continuation from last fully committed checkpoint; no update replay. Fixed endpoint, interrupted diagnostic retained as unknown. No bit-exact counterfactual claim across hardware variants.')
