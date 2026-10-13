"""Prepared read-only CPU integrity audit of compact evidence and full states.

Original Volume files are never changed. Compact records are verified through
an immutable archive plus its per-file manifest; this does not claim to reread
each separate remote inode or to independently reproduce model inference.
"""
from pathlib import Path
import time
from experiments.sft_allocation_midpoint.common import read,sha,digest,verify
from experiments.sft_allocation_midpoint import checkpoint as ck
from .evidence_bundle import safe_name,unpack
from .contract import lrs

CONTAINERS={'compact_evidence.tar.gz','compact_manifest.json','bundle_receipt.json'}


def copy_checked(source,target,record,check):
    tick=time.monotonic()
    source=Path(source);target=Path(target)
    if source.is_symlink() or source.stat().st_size!=record['bytes']:
        raise ValueError('Foreign/symlink/size-changed source')
    target.parent.mkdir(parents=True,exist_ok=True)
    with source.open('rb') as src,target.open('xb') as dst:
        while True:
            check();block=src.read(8*1024*1024)
            if not block:break
            dst.write(block)
    if target.stat().st_size!=record['bytes'] or sha(target)!=record['sha256']:
        raise ValueError('Audit transfer SHA mismatch')
    check()
    return dict(bytes=record['bytes'],seconds=time.monotonic()-tick,
                scope='Remote file read, local write and local SHA check; not isolated network bandwidth')


def finite(value):
    import torch
    if isinstance(value,torch.Tensor):return bool(torch.isfinite(value).all())
    if isinstance(value,dict):return all(finite(x) for x in value.values())
    if isinstance(value,(list,tuple)):return all(finite(x) for x in value)
    return True


def verify_packed_run(source,destination,label,check=lambda:None):
    started=time.monotonic()
    source=Path(source);dst=Path(destination);dst.mkdir(parents=True,exist_ok=False)
    envelope=label['envelope'];files=envelope['artifact_manifest'];receipt=envelope['receipt'];cfg=label['config']
    if receipt['status']!='completed' or digest(files)!=receipt['evidence_sha256']:
        raise ValueError('Original completed artifact envelope required')
    oracle=label['local_oracle']
    if oracle.get('passed') is not True or oracle.get('artifact_digest',oracle.get('manifest_digest'))!=digest(files):
        raise ValueError('Independent local oracle does not bind this run')
    if read(source/'artifact_manifest.json')!=files:raise ValueError('Original remote manifest differs')
    for name in files:safe_name(name)
    if cfg['role'] in ('main','bridge'):
        steps=[1024,2048] if cfg['updates']==2048 else [cfg['updates']]
        states={f'checkpoint_{step:04d}/state.pt' for step in steps}
    elif cfg['role'] in ('pool','base'):steps=[];states=set()
    else:raise ValueError('Unknown audit role')
    if {n for n in files if n.endswith('.pt')}!=states:raise ValueError('Unexpected/missing complete states')
    if not CONTAINERS<=set(files):raise ValueError('Missing packed evidence')
    transfer=dst/'transfer';transfer.mkdir()
    timings={}
    for name in sorted(CONTAINERS|states):
        timings[name]=copy_checked(source/name,transfer/name,files[name],check)
    compact=read(transfer/'compact_manifest.json')
    expected=set(files)-CONTAINERS-states
    if set(compact)!=expected or any(compact[n]!=files[n] for n in expected):
        raise ValueError('Archive content manifest differs from original envelope')
    evidence=dst/'evidence';check();unpack_started=time.monotonic()
    unpack(transfer/'compact_evidence.tar.gz',transfer/'compact_manifest.json',transfer/'bundle_receipt.json',evidence)
    for name in CONTAINERS|states:
        p=evidence/name;p.parent.mkdir(parents=True,exist_ok=True);p.hardlink_to(transfer/name)
    verify(evidence,files)
    check();unpack_seconds=time.monotonic()-unpack_started
    sent=read(evidence/'intent.json');result=read(evidence/'result.json')
    if sent['config']!=cfg or sent['plan']['campaign_id']!=label['campaign'] or result!=envelope['result']:
        raise ValueError('Archived run/config/result identity differs')
    if cfg['run_id']!=label['run_id']:raise ValueError('Foreign run label')
    if cfg['role']=='pool':
        if oracle['draw']!=cfg['draw'] or oracle['physical_outputs']!=result['physical_outputs']:
            raise ValueError('Independent pool oracle differs')
        if not oracle['all_raw_redecoded'] or not oracle['all_wallets_replayed']:
            raise ValueError('Incomplete pool oracle')
    elif oracle['run_id']!=cfg['run_id'] or oracle['role']!=cfg['role']:
        raise ValueError('Independent student oracle identity differs')
    hashes={};state_seconds={}
    if steps:
        recipe=read(evidence/'recipe.json');identity=recipe['identity']
        if identity['config']!=cfg or identity['source_commit']!=sent['release']['commit'] or identity['source_sha256']!=digest(sent['release']['source_files']):
            raise ValueError('Full state provenance differs')
        for step in steps:
            check();tick=time.monotonic();path=evidence/f'checkpoint_{step:04d}';state=ck.load(path,identity);check()
            if state['step']!=step or state['cursor']!=step or state['schedule']!=recipe['schedule'] or state['lrs']!=lrs(cfg['updates']):
                raise ValueError('Forensic/full state trajectory differs')
            done=read(evidence/'completed'/f'update_{step:04d}.json')
            if state['supervised_tokens']!=done['cumulative_targets'] or state['processed_tokens']!=done['cumulative_processed']:
                raise ValueError('Checkpoint prefix dose differs')
            if set(state['adapter'])!=set(state['trainable_names']) or not state['adapter'] or not state['optimizer']['state']:
                raise ValueError('Incomplete adapter/optimizer state')
            if set(state['rng'])!={'python','numpy','torch','cuda'} or not finite(state['adapter']) or not finite(state['optimizer']):
                raise ValueError('Incomplete/nonfinite training state')
            check()
            if step==cfg['updates'] and (state['supervised_tokens']!=cfg['targets'] or result['updates']!=step or result['targets']!=cfg['targets']):
                raise ValueError('Terminal scientific dose differs')
            hashes[str(step)]=sha(path/'state.pt');del state
            prior=(oracle['state_sha256'] if step==cfg['updates']
                   else oracle['forensic_checkpoints'][str(step)]['sha256'])
            if hashes[str(step)]!=prior:raise ValueError('Independent full-state oracle differs')
            state_seconds[str(step)]=time.monotonic()-tick
    if cfg['role']!='pool':
        summary=result['endpoint'];scores=summary['question_correct']
        if len(scores)!=1319 or any(type(x)is not bool for x in scores.values()) or sum(scores.values())!=summary['correct']:
            raise ValueError('Incomplete endpoint identity')
        if oracle['outputs_rescored']!=1319 or oracle['correct']!=summary['correct']:
            raise ValueError('Independent endpoint oracle differs')
        if oracle['updates_verified']!=cfg['updates'] or oracle['targets_verified']!=cfg['targets']:
            raise ValueError('Independent dose oracle differs')
    return dict(passed=True,campaign=label['campaign'],run_id=label['run_id'],role=cfg['role'],
      files_verified=len(files),original_artifact_digest=digest(files),checkpoint_sha256=hashes,
      local_oracle_sha256=digest(oracle),copied_bytes=sum(files[n]['bytes'] for n in CONTAINERS|states),
      timings=dict(copy_and_sha=timings,unpack_and_all_file_sha_seconds=unpack_seconds,
                   complete_state_validation_seconds=state_seconds,total_seconds=time.monotonic()-started),
      packed_read_scope='Per-file original bytes verified from immutable compact snapshot; full state binaries copied and loaded separately',
      new_model_calls=0,raw_rescoring_scope='Existing independent local oracle bound, not repeated in this integrity audit')
