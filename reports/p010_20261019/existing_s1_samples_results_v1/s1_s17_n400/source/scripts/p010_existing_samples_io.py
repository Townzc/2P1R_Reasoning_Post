"""Bounded read-only collection of original S1 new samples, never old states."""
import argparse,os,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from experiments.p010.common import read,dump,sha,utc
from experiments.p010.existing_samples_evidence import record_keys


def collect(receipt,out):
    from scripts.p010_transfer import collect as original_collect
    receipt,out=Path(receipt),Path(out);run=read(receipt/'SUBMITTED.json')['run'];record_keys(run)
    dump(out.with_name(out.name+'_COLLECTION_INTENT.json'),dict(utc=utc(),run=run,
        original_receipt_sha256=sha(receipt/'RESULT.json'),local_seconds=1200,automatic_retry=False))
    timer=threading.Timer(1200,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:original_collect(receipt,'/p010-20261019/existing_s1_samples/'+run,out)
    except BaseException as exc:
        dump(out.with_name(out.name+'_COLLECTION_FAILED.json'),dict(type=type(exc).__name__,error=str(exc),
            partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


def records(receipt,export,spec,out):
    import modal
    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    receipt,export,out=map(Path,[receipt,export,out]);spec=read(spec)
    env=read(receipt/'RESULT.json');sent=read(receipt/'SUBMITTED.json');run=sent['run'];keys=record_keys(run)
    proof=read(export/'COMPLETED.json');provider=read(export/'PROVIDER_PRIVATE.json');parent=spec['parents'][run]
    if (env['status']!='completed' or proof['original_result_sha256']!=sha(receipt/'RESULT.json')
            or proof['provider_stopped'] is not True):raise ValueError('Complete/stopped original result required')
    validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),run=run,keys=keys,local_seconds=600,new_model_calls=0,remote_writes=0))
    timer=threading.Timer(600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False)
        original=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
        fixed=['existing_s1_samples/'+run+'/'+kind for kind in ('claim','terminal')]
        before={k:store.get(k) for k in fixed};old_before=original.get(parent['terminal_key'])
        dump(out/'BEFORE.json',dict(new=before,original_terminal=old_before))
        if before[fixed[1]]!=env or old_before!=parent['terminal']:raise ValueError('Original terminal changed')
        values={}
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending={pool.submit(store.get,key):(i,key) for i,key in enumerate(keys)}
            for future in as_completed(pending,timeout=570):
                i,key=pending[future];value=future.result();values[key]=value
                dump(out/'records'/f'{i:03d}.json',dict(key=key,value=value))
        after={k:store.get(k) for k in fixed};old_after=original.get(parent['terminal_key'])
        dump(out/'AFTER.json',dict(new=after,original_terminal=old_after))
        if before!=after or old_before!=old_after or any(values[k]!=before[k] for k in fixed):
            raise ValueError('Original parent/new sample proof changed during collection')
        dump(out/'RECORDS.json',values)
        dump(out/'COMPLETED.json',dict(utc=utc(),run=run,records_sha256=sha(out/'RECORDS.json'),
            original_receipt_sha256=sha(receipt/'RESULT.json'),provider_sha256=sha(export/'PROVIDER_PRIVATE.json'),
            original_terminal=old_after,named_records=len(keys),new_model_calls=0,remote_writes=0))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    for name in ('collect','records'):
        parser=sub.add_parser(name)
        parser.add_argument('--receipt',required=True);parser.add_argument('--out',required=True)
        if name=='records':parser.add_argument('--export',required=True);parser.add_argument('--spec',required=True)
    args=p.parse_args()
    if args.action=='collect':collect(args.receipt,args.out)
    else:records(args.receipt,args.export,args.spec,args.out)
