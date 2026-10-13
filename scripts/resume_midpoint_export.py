"""One reconciled read-only export continuation; never starts cloud compute.

Verified existing files and verified old range blocks are reused. Mismatched
files are rejected, not overwritten. The original failed attempt is retained.
"""
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from scripts.midpoint_range_transfer import ranges,assemble


def inventory(root,selected):
    good,missing=[],[]
    for name,spec in selected.items():
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Unsafe artifact path')
        p=Path(root)/name
        if not p.exists():missing.append(name)
        elif p.is_file() and p.stat().st_size==spec['bytes'] and sha(p)==spec['sha256']:
            good.append(name)
        else:raise ValueError('Existing artifact differs; preserve and reconcile: '+name)
    return good,missing


def reusable_ranges(old,remote,spec):
    old=Path(old);receipt=read(old/'transport_receipt.json')
    if receipt['remote']!=remote or receipt['expected']!=spec or receipt['read_only'] is not True or receipt['scientific_calls']!=0:
        raise ValueError('Prior range receipt identity differs')
    entries={r['start']:r for r in receipt['ranges']}
    if len(entries)!=len(receipt['ranges']):raise ValueError('Duplicate prior range')
    result=[]
    for start,length in ranges(spec['bytes']):
        p=old/f'{start:012d}.bin'
        if not p.exists():continue
        record=entries.get(start)
        if not record or record['length']!=length or record['status']!='verified_response' or p.stat().st_size!=length or sha(p)!=record['sha256']:
            raise ValueError('Existing range not independently reusable')
        result.append((start,length))
    return result


def repair_state(volume_name,remote,target,spec,tag):
    import aiohttp
    from modal.volume import _Volume,_raise_on_block_response_error,_read_block_body
    from modal_proto import api_pb2
    target=Path(target);old=target.with_name(target.name+'.parts')
    if target.exists():raise FileExistsError(target)
    verified=reusable_ranges(old,remote,spec)
    new=target.with_name(target.name+'.parts_'+tag);new.mkdir(exist_ok=False)
    for start,length in verified:
        source=old/f'{start:012d}.bin';dest=new/source.name
        with source.open('rb') as src,dest.open('xb') as dst:shutil.copyfileobj(src,dst)
        if sha(source)!=sha(dest):raise ValueError('Reused range copy differs')
    reused=set(verified);missing=[x for x in ranges(spec['bytes']) if x not in reused]
    records=[]
    async def fetch():
        volume=_Volume.from_name(volume_name,create_if_missing=False);await volume.hydrate()
        timeout=aiohttp.ClientTimeout(total=60,connect=10,sock_read=45)
        async with aiohttp.ClientSession(timeout=timeout) as client:
            for start,length in missing:
                record=dict(start=start,length=length,status='attempted');records.append(record)
                response=await asyncio.wait_for(volume.client._stub.VolumeGetFile2(api_pb2.VolumeGetFile2Request(volume_id=volume.object_id,path=remote,start=start,len=length,client_pads_blocks=True)),20)
                if response.start!=start or response.len!=length or len(response.get_urls)!=1:
                    raise ValueError('Provider range boundary differs')
                async with client.get(response.get_urls[0]) as resp:
                    await _raise_on_block_response_error(resp);body=await _read_block_body(resp,length)
                if len(body)>length:raise ValueError('Oversized provider range')
                p=new/f'{start:012d}.bin'
                with p.open('xb') as f:f.write(body.ljust(length,b'\0'))
                record.update(status='verified_response',sha256=sha(p))
    receipt=dict(remote=remote,expected=spec,prior_receipt_sha256=sha(old/'transport_receipt.json'),reused_ranges=verified,new_ranges=records,read_only=True,scientific_calls=0,automatic_retries=0,started_epoch=time.time(),complete=False)
    try:
        asyncio.run(asyncio.wait_for(fetch(),180));assemble(new,target,spec);receipt['complete']=True
    except BaseException as error:
        receipt['error_type']=type(error).__name__;raise
    finally:
        receipt['finished_epoch']=time.time();dump(new/'transport_receipt.json',receipt)


def resume(args):
    import modal
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+',x) for x in (args.campaign,args.run,args.tag)):
        raise ValueError('Unsafe identity')
    root=Path(args.out);envelope=read(args.receipt);ledger=read(args.ledger)
    if (root/'LOCAL_VERIFICATION.json').exists():raise FileExistsError('Already verified')
    prefix=f'/{args.campaign}/{args.run}/';key=f'midpoint/{args.campaign}/terminal/{args.run}'
    records=read(root/'artifact_manifest.json');terminal=envelope['receipt']
    if terminal['status']!='completed' or terminal!=ledger[key] or records!=envelope['artifact_manifest'] or digest(records)!=terminal['evidence_sha256']:
        raise ValueError('Completed immutable evidence binding differs')
    selected={n:s for n,s in records.items() if not n.endswith('.pt') or n.startswith('checkpoint_0256/')}
    good,missing=inventory(root,selected)
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    if json.loads(b''.join(volume.read_file(prefix+'artifact_manifest.json')))!=records:
        raise ValueError('Remote manifest changed')
    dump(root/('RECOVERY_INTENT_'+args.tag+'.json'),dict(started_epoch=time.time(),source_sha256=sha(Path(__file__)),verified_existing=good,missing=missing,original_manifest_sha256=sha(root/'artifact_manifest.json'),remote_writes=0,model_calls=0,automatic_retries=0))
    for name in [n for n in missing if selected[n]['bytes']>=32*1024*1024]:
        # Keep the raw asynchronous SDK client isolated from the synchronous
        # Modal client used for manifest/compact reads in this process.
        payload=dict(volume_name='sft-allocation-midpoint-v1',remote=prefix+name,
                     target=str(root/name),spec=selected[name],tag=args.tag)
        subprocess.run([sys.executable,'-m','scripts.resume_midpoint_export',
                        '--repair-state-json',json.dumps(payload)],check=True,timeout=210)
    def fetch(name):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:
            for block in volume.read_file(prefix+name):f.write(block)
        if p.stat().st_size!=selected[name]['bytes'] or sha(p)!=selected[name]['sha256']:
            raise ValueError('Downloaded artifact differs: '+name)
    small=[n for n in missing if selected[n]['bytes']<32*1024*1024]
    with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(fetch,small))
    verified,missing_after=inventory(root,selected)
    assert not missing_after and len(verified)==len(selected)
    if json.loads(b''.join(volume.read_file(prefix+'artifact_manifest.json')))!=records:
        raise ValueError('Remote manifest changed during export')
    receipt=dict(schema='independent_local_export_v1',campaign=args.campaign,run=args.run,manifest_sha256=sha(root/'artifact_manifest.json'),files_verified=len(verified),bytes=sum(s['bytes'] for s in selected.values()),full_checkpoint_steps=[256],remote_files_unchanged=True,finished_epoch=time.time(),recovery_tag=args.tag,reused_files=len(good),new_files=len(missing),model_calls=0)
    dump(root/'LOCAL_VERIFICATION.json',receipt);print(json.dumps(receipt))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repair-state-json')
    for arg in ('campaign','run','out','receipt','ledger','tag'):parser.add_argument('--'+arg)
    args=parser.parse_args()
    if args.repair_state_json:
        repair_state(**json.loads(args.repair_state_json))
    else:
        if not all(getattr(args,k) for k in ('campaign','run','out','receipt','ledger','tag')):
            parser.error('All export identity and evidence arguments are required')
        resume(args)
