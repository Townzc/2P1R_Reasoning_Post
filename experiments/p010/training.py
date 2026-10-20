"""P010 E4 adapter of immutable P009 stage1_training_core.

Original runtime.train, gradients, optimizer, checkpoint, merge and LR are reused.
Only the authorized OLMo identity/EOS and exact input validation are adapted.
No dispatch or test selection in this module.
"""
from pathlib import Path
from experiments.sft_allocation_midpoint import runtime as rt
from experiments.p010.common import MODELS, dump, read, digest, manifest
from experiments.learning_regime_p009.training_plan import UPDATES,TARGETS,validate_plan,LR_VECTOR_SHA256
from experiments.learning_regime_p009.stage1_training_core import training_environment
from src.sft_data import encode_row


def checked_recipe(config, encoded, plan):
    if (config['experiment']!='P010' or config['arm']!='E4' or config['n'] not in (400,3200)
        or config['seed']!=17 or config['model']!=list(MODELS['olmo'])
        or config['updates']!=UPDATES or config['targets']!=TARGETS
        or len(encoded)!=config['n'] or config['eos_token_id']!=100257
        or config['encoded_sha256']!=digest(encoded) or config['plan_sha256']!=digest(plan)
        or config['lr_vector_sha256']!=LR_VECTOR_SHA256):
        raise ValueError('Only the two original-dose P010 E4 cells')
    budget=validate_plan(encoded,plan,17,100257)
    return dict(arm='E4',budget=budget,final_checkpoint_only=True,endpoint_count=1319,
        endpoint_max_new_tokens=512,no_training_data_filter_at_runtime=True)


def train_and_merge(base, rows, encoded, plan, out, merged_path, journal, identity):
    """Exactly1024 updates, one complete state, then FP32 merge/BF16 storage.

    There is no continuation/retry loop or intermediate evaluation. The caller's
    BlockTrainingJournal must reserve all64 sixteen-update blocks before work,
    check its remote fence at block boundaries and its deadline on every step.
    """
    from experiments.sft_allocation_p008.block_journal import BlockTrainingJournal
    config = identity['config']; recipe = checked_recipe(config, encoded, plan)
    if (not isinstance(journal, BlockTrainingJournal)
            or journal.expected_updates != UPDATES or journal.records is not None
            or journal.cursor or journal.active or journal.pending or journal.failed):
        raise ValueError('Fresh exact1024-update block journal required')
    if (len(rows) != config['n'] or digest(rows) != config['rows_sha256']
            or [r['problem_id'] for r in rows] != [r['problem_id'] for r in encoded]
            or [r['path_id'] for r in rows] != [r['path_id'] for r in encoded]):
        raise ValueError('Frozen untruncated source answers differ')
    out = Path(out); merged_path = Path(merged_path)
    if Path(journal.out) != out or merged_path.exists():
        raise ValueError('Foreign journal or prior merged model; no replay')
    journal.check(); journal.deadline()
    dump(out/'TRAINING_STARTED.json', dict(recipe=recipe, identity_sha256=digest(identity),
        encoded_rows_sha256=digest(encoded), plan_sha256=digest(plan), automatic_retry=False))
    journal.commit()
    dump(out/'training_environment.json', training_environment()); journal.commit()
    model, tokenizer = rt.new_model(base, config['seed'])
    if tokenizer.eos_token_id != config['eos_token_id']:
        raise ValueError('Exact pinned model terminal EOS required')
    actual_encoded = [encode_row(r, tokenizer, 2048) for r in rows]
    if actual_encoded != encoded:
        raise ValueError('Actual whole-answer tokenization differs; no filtering/truncation')
    dump(out/'recipe.json', dict(identity=identity, recipe=recipe, schedule=plan['updates'],
        lrs=plan['lrs'], row_path_ids=plan['row_path_ids'], row_exposures=plan['row_exposures'],
        encoded_rows_sha256=digest(encoded), targets=TARGETS, seed=config['seed']))
    optimizer = rt.optimizer_for(model)
    journal.configure_training(encoded, plan['updates'], plan['lrs'])
    history, targets, processed = rt.train(model, tokenizer, optimizer, encoded,
        plan['updates'], plan['lrs'], out, journal, identity, save_steps=(UPDATES,))
    journal.assert_training_complete()
    if len(history) != UPDATES or targets != TARGETS:
        raise ValueError('Actual full scientific dose differs')
    state = read(out/'checkpoint_1024/manifest.json')
    if (state['step'] != UPDATES or state['supervised_tokens'] != TARGETS
            or state['processed_tokens'] != processed or state['identity_sha256'] != digest(identity)):
        raise ValueError('Original complete terminal state differs')
    journal.begin('terminal_merge', dict(checkpoint=state, training_updates=UPDATES,
        merge_dtype='float32', saved_dtype='bfloat16'))
    import torch
    model.eval()
    # No intervening optimizer update after the immutable terminal state saved
    # and read back by runtime.train/checkpoint.save. Do not reload an old state.
    merged = model.merge_and_unload(safe_merge=True).to(dtype=torch.bfloat16)
    merged_path.mkdir(parents=True, exist_ok=False)
    merged.save_pretrained(merged_path, safe_serialization=True)
    tokenizer.save_pretrained(merged_path)
    proof = dict(checkpoint=state, merge_dtype='float32', saved_dtype='bfloat16',
        complete_optimizer_rng_preserved=True, terminal_state_saved_before_merge=True,
        optimizer_updates_after_terminal_save=0, final_checkpoint_only=True,
        merged_files=manifest(merged_path), model=config['model'])
    dump(out/'MERGE_PROOF.json', proof); journal.commit()
    journal.end('terminal_merge', dict(proof_sha256=digest(proof), targets=targets,
        processed_tokens=processed, completed_updates=len(history)))
    journal.commit()
    return dict(updates=len(history), targets=targets, processed_tokens=processed,
        checkpoint=state, merge_proof_sha256=digest(proof), evaluation_performed=False,
        requested_seed=config['seed'], no_intermediate_checkpoint_selection=True)
