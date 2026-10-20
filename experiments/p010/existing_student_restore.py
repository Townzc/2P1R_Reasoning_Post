"""New inference-only restore of original saved S1 final adapters; no optimizer."""
from pathlib import Path
from experiments.p010.common import dump,read,sha,digest,manifest,verify,utc


def copy_adapter(model,state):
    import torch
    parameters={name:p for name,p in model.named_parameters() if p.requires_grad}
    if list(parameters)!=state['trainable_names'] or set(parameters)!=set(state['adapter']):
        raise ValueError('Original final adapter parameter names differ')
    with torch.no_grad():
        for name,param in parameters.items():
            value=state['adapter'][name]
            if (param.dtype!=torch.float32 or value.dtype!=torch.float32
                    or param.shape!=value.shape or not torch.isfinite(value).all()):
                raise ValueError('Original final adapter shape/dtype/finiteness differs')
            param.copy_(value)
            if not torch.equal(param.detach().cpu(),value):
                raise ValueError('Original final adapter copy changed')
    return len(parameters)


def restore_once(base,checkpoint,expected,out,merged):
    import torch
    from experiments.sft_allocation_midpoint.checkpoint import load
    from experiments.sft_allocation_midpoint.runtime import new_model
    from experiments.learning_regime_p009.stage1_training_core import training_environment
    out,checkpoint,merged=map(Path,[out,checkpoint,merged])
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),original_state_sha256=expected['checkpoint']['sha256'],
        new_training_updates=0,new_optimizer_instances=0,automatic_retry=False))
    if read(checkpoint/'manifest.json')!=expected['checkpoint']:
        raise ValueError('Original saved final checkpoint manifest differs')
    # One actual state read is needed for this new inference-only model. The
    # old full-state oracle is not rerun; no optimizer/RNG state is restored.
    state=load(checkpoint)
    if (state['step']!=1024 or state['supervised_tokens']!=2097148
            or digest(state['identity'])!=expected['checkpoint']['identity_sha256']):
        raise ValueError('Original final checkpoint identity/dose differs')
    environment=training_environment()
    model,tokenizer=new_model(base,17)
    if tokenizer.eos_token_id!=151643:raise ValueError('Original base EOS differs')
    count=copy_adapter(model,state)
    model.eval()
    merged_model=model.merge_and_unload(safe_merge=True).to(dtype=torch.bfloat16)
    merged.mkdir(parents=True,exist_ok=False)
    merged_model.save_pretrained(merged,safe_serialization=True)
    tokenizer.save_pretrained(merged)
    # Original temporary merged files no longer exist. Their immutable saved
    # hashes bind this reconstruction to the exact earlier evaluated model.
    actual=manifest(merged)
    if actual!=expected['merged_files']:
        raise ValueError('Reconstructed merged model/tokenizer differs from original greedy model')
    proof=dict(utc=utc(),original_state_sha256=sha(checkpoint/'state.pt'),
        original_identity_sha256=digest(state['identity']),adapter_parameters=count,
        actual_merged_files=actual,original_merged_files=expected['merged_files'],
        original_greedy_model_bytes_reproduced=True,merge_dtype='float32',saved_dtype='bfloat16',
        new_training_updates=0,new_optimizer_instances=0,optimizer_rng_preserved_not_restored=True,
        state_loads_for_this_new_inference=1,old_full_state_oracle_repeated=False,
        environment=environment)
    dump(out/'COMPLETED.json',proof)
    return proof


def child(connection,base,checkpoint,expected,out,merged,deadline_epoch):
    import time,os,traceback
    try:
        if time.time()>=deadline_epoch-30:raise TimeoutError('Original inference restore window expired')
        proof=restore_once(base,checkpoint,expected,out,merged)
        if time.time()>=deadline_epoch-30:raise TimeoutError('Original inference restore deadline')
        connection.send(('restored',dict(pid=os.getpid(),proof=proof)))
    except BaseException:
        connection.send(('error',traceback.format_exc()))
        raise
    finally:connection.close()
