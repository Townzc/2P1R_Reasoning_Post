"""Bounded read-only collection of new E4 endpoint children; no replay or writes."""
import argparse,json,os,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from experiments.p010.common import read,dump,sha,utc
from experiments.p010.e4_endpoint_evidence import record_keys


def collect(receipt,out):
    from scripts.p010_transfer import collect as original_collect
    receipt=Path(receipt);out=Path(out);sent=read(receipt/'SUBMITTED.json');run=sent['run'];record_keys(run)
    intent=out.with_name(out.name+'_COLLECTION_INTENT.json')
    dump(intent,dict(utc=utc(),run=run,original_receipt_sha256=sha(receipt/'RESULT.json'),local_cap_seconds=1200,automatic_retry=False))
    timer=threading.Timer(1200,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:original_collect(receipt,'/p010-20261019/e4_endpoint_only/'+run,out)
    except BaseException as exc:
        dump(out.with_name(out.name+'_COLLECTION_FAILED.json'),dict(type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


def records(receipt,export,out):
    import modal
    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    receipt=Path(receipt);export=Path(export);out=Path(out);env=read(receipt/'RESULT.json');sent=read(receipt/'SUBMITTED.json')
    proof=read(export/'COMPLETED.json');provider=read(export/'PROVIDER_PRIVATE.json');run=sent['run'];keys=record_keys(run)
    if env['status']!='completed' or proof['original_result_sha256']!=sha(receipt/'RESULT.json') or proof['provider_stopped'] is not True:
        raise ValueError('Actual original completed/stopped collection required')
    validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
    out.mkdir(parents=True,exist_ok=False);dump(out/'INTENT.json',dict(utc=utc(),run=run,keys=keys,local_seconds=600,new_model_calls=0,remote_writes=0))
    timer=threading.Timer(600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False);child='e4_endpoint_only/'+run;parent='e4/'+run
        fixed=[child+'/claim',child+'/terminal',parent+'/claim',parent+'/terminal',parent+'/endpoint_only_successor']
        before={k:store.get(k) for k in fixed};dump(out/'BEFORE.json',before)
        if before[child+'/terminal']!=env:raise ValueError('Original completed terminal differs')
        values={}
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending={pool.submit(store.get,k):(i,k) for i,k in enumerate(keys)}
            for future in as_completed(pending,timeout=570):
                i,k=pending[future];value=future.result();dump(out/'records'/f'{i:03d}.json',dict(key=k,value=value));values[k]=value
        after={k:store.get(k) for k in fixed};dump(out/'AFTER.json',after)
        if before!=after or any(values[k]!=before[k] for k in fixed):raise ValueError('Original parent or child fence changed')
        dump(out/'RECORDS.json',values);dump(out/'COMPLETED.json',dict(utc=utc(),run=run,records_sha256=sha(out/'RECORDS.json'),
            original_receipt_sha256=sha(receipt/'RESULT.json'),provider_sha256=sha(export/'PROVIDER_PRIVATE.json'),named_records=len(keys),new_model_calls=0,remote_writes=0))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    c=sub.add_parser('collect');c.add_argument('--receipt',required=True);c.add_argument('--out',required=True)
    c=sub.add_parser('records');c.add_argument('--receipt',required=True);c.add_argument('--export',required=True);c.add_argument('--out',required=True)
    a=p.parse_args()
    if a.action=='collect':collect(a.receipt,a.out)
    else:records(a.receipt,a.export,a.out)
