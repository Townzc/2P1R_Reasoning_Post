"""Prepared NC/S1 scientific core; no dispatch or runtime admission authority.

The future entry must bind original corpora, G0/P1, exact code/input/numeric
reviews, a single-use claim and a whole-worker timer before calling this core.
Training is in a dedicated process which must exit before vLLM is constructed.
No old experiment worker, evaluation or checkpoint-selection path is called.
"""
from pathlib import Path

from experiments.sft_allocation_midpoint import runtime as rt
from experiments.sft_allocation_midpoint.common import digest, dump, manifest, read
from experiments.learning_regime_p009.p0_engine import software
from experiments.learning_regime_p009.stage0_generation_contract_v2 import MODELS
from experiments.learning_regime_p009.training_plan import (
    UPDATES, TARGETS, validate_plan, LR_VECTOR_SHA256,
)

SIZES = {17: (100, 400, 1600, 3200), 29: (400, 3200)}


def checked_recipe(config, encoded, plan):
    """Check exact actual input/plan identity before a model can be loaded."""
    setting, seed, n = config['setting'], config['seed'], config['n']
    if (setting not in ('NC', 'S1') or type(seed) is not int or seed not in SIZES
            or type(n) is not int or n not in SIZES[seed]
            or (setting == 'NC' and (seed != 17 or n not in (400, 3200)))
            or config['model'] != MODELS['qwen'] or len(encoded) != n
            or type(config['updates']) is not int or config['updates'] != UPDATES
            or type(config['targets']) is not int or config['targets'] != TARGETS
            or config['encoded_rows_sha256'] != digest(encoded)
            or config['plan_sha256'] != digest(plan)
            or config['lr_vector_sha256'] != LR_VECTOR_SHA256):
        raise ValueError('Exact registered NC/S1 recipe required; S2 is not admitted')
    budget = validate_plan(encoded, plan, seed, 151643)
    return dict(setting=setting, seed=seed, n=n, budget=budget,
        final_checkpoint_only=True, endpoint_count=1319 if setting == 'NC' else 500,
        endpoint_max_new_tokens=512 if setting == 'NC' else 1024,
        no_training_data_filter_at_runtime=True, runtime_admitted=False)


def training_environment():
    """Current P009 pinned Linux stack; unchanged P008 training primitives."""
    import torch
    info = software()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)
    info.update(deterministic_algorithms=True, allow_tf32=False,
                training_parameters='float32', forward_autocast='bfloat16',
                training_function='sft_allocation_midpoint.runtime.train',
                numpy_version_note='Pinned P009 2.2.6; old P008 environment was 2.3.2')
    return info


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
    if (len(rows) != config['n'] or digest(rows) != config['training_rows_sha256']
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
    if tokenizer.eos_token_id != 151643:
        raise ValueError('Exact Qwen terminal EOS required')
    actual_encoded = rt.encode(rows, tokenizer)
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
        merged_files=manifest(merged_path), model=MODELS['qwen'])
    dump(out/'MERGE_PROOF.json', proof); journal.commit()
    journal.end('terminal_merge', dict(proof_sha256=digest(proof), targets=targets,
        processed_tokens=processed, completed_updates=len(history)))
    journal.commit()
    return dict(updates=len(history), targets=targets, processed_tokens=processed,
        checkpoint=state, merge_proof_sha256=digest(proof), evaluation_performed=False,
        requested_seed=config['seed'], no_intermediate_checkpoint_selection=True)
