"""Create-only C6 input upload and bounded stopped-worker evidence collection."""
import argparse
import hashlib
import os
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from experiments.p010.common import dump,read,sha,utc
from experiments.p010.cue_search_evidence import record_keys


def upload(root,spec_file):
    import modal
    from modal.exception import NotFoundError
    root=Path(root);spec=read(spec_file);source=root/'cue_inputs_r1/DEV_PROMPTS.json'
    if sha(source)!=spec['dev_input_sha256']:
        raise ValueError('Exact original gold-free input required')
    out=root/'cue_input_upload_r1';out.mkdir(exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),dev_input_sha256=sha(source),new_model_calls=0))
    timer=threading.Timer(600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
        remote='/p010-20261019/cue_inputs_r1/DEV_PROMPTS.json'
        try:prior=b''.join(volume.read_file(remote))
        except (NotFoundError,FileNotFoundError):prior=None
        if prior is not None:
            if hashlib.sha256(prior).hexdigest()!=sha(source):raise ValueError('Remote input differs; no overwrite')
        else:
            with volume.batch_upload(force=False) as batch:batch.put_file(source,remote)
        returned=b''.join(volume.read_file(remote))
        if hashlib.sha256(returned).hexdigest()!=sha(source):raise ValueError('Actual input readback differs')
        dump(out/'COMPLETED.json',dict(utc=utc(),dev_input_sha256=sha(source),bytes=len(returned),
            reused_original=prior is not None,new_model_calls=0))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False))
        raise
    finally:timer.cancel()


def collect(receipt,out):
    from scripts.p010_transfer import collect as original
    out=Path(out)
    dump(out.with_name(out.name+'_INTENT.json'),dict(utc=utc(),original_receipt_sha256=sha(Path(receipt)/'RESULT.json'),
        local_seconds=1200,automatic_retry=False))
    timer=threading.Timer(1200,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:original(receipt,'/p010-20261019/cue/search_r1',out)
    except BaseException as exc:
        dump(out.with_name(out.name+'_FAILED.json'),dict(type=type(exc).__name__,error=str(exc),
            partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


def records(receipt,export,out):
    import modal
    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    receipt,export,out=map(Path,[receipt,export,out]);env=read(receipt/'RESULT.json');sent=read(receipt/'SUBMITTED.json')
    collected=read(export/'COMPLETED.json');provider=read(export/'PROVIDER_PRIVATE.json')
    if env['status']!='completed' or collected['original_result_sha256']!=sha(receipt/'RESULT.json') or not collected['provider_stopped']:
        raise ValueError('Original complete stopped collection required')
    validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
    keys=record_keys();out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(keys=keys,utc=utc(),local_seconds=600,remote_writes=0))
    timer=threading.Timer(600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False)
        fixed=keys[:2];before={k:store.get(k) for k in fixed};dump(out/'BEFORE.json',before)
        if before['cue/search_r1/terminal']!=env:raise ValueError('Original completed terminal differs')
        values={}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures={pool.submit(store.get,k):(i,k) for i,k in enumerate(keys)}
            for future in as_completed(futures,timeout=570):
                i,k=futures[future];v=future.result();dump(out/'records'/f'{i:03d}.json',dict(key=k,value=v));values[k]=v
        after={k:store.get(k) for k in fixed};dump(out/'AFTER.json',after)
        if before!=after or any(values[k]!=before[k] for k in fixed):raise ValueError('Original claim/terminal changed')
        dump(out/'RECORDS.json',values)
        dump(out/'COMPLETED.json',dict(utc=utc(),records_sha256=sha(out/'RECORDS.json'),named_records=len(keys),
            original_receipt_sha256=sha(receipt/'RESULT.json'),provider_sha256=sha(export/'PROVIDER_PRIVATE.json'),remote_writes=0))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    x=sub.add_parser('upload');x.add_argument('--root',required=True);x.add_argument('--spec',required=True)
    x=sub.add_parser('collect');x.add_argument('--receipt',required=True);x.add_argument('--out',required=True)
    x=sub.add_parser('records');x.add_argument('--receipt',required=True);x.add_argument('--export',required=True);x.add_argument('--out',required=True)
    a=p.parse_args()
    if a.action=='upload':upload(a.root,a.spec)
    elif a.action=='collect':collect(a.receipt,a.out)
    else:records(a.receipt,a.export,a.out)
