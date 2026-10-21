"""Create-only C1 evidence packing/extraction and original return verification.

No scorer, forward, input encoder, model/checkpoint loader or statistics. These
helpers have no actual runtime admission and never retry partial transfers.
"""
from pathlib import Path
import hashlib
import json
import tarfile
import math

from experiments.sft_allocation_midpoint.common import dump,read,sha,manifest,verify,digest
from experiments.p011.c1_r2 import execution as c1_execution


def safe_name(name):
    p=Path(name)
    if (not name or p.is_absolute() or '..' in p.parts or str(p)!=name
            or not name.endswith('.json')):
        raise ValueError('Only exact relative C1 JSON evidence members permitted')
    return name


def pack(out):
    out=Path(out)
    if ((out/'FAILED.json').exists() or not (out/'ALL_CONFIRMED.json').exists()
            or (out/'COMPACT_MEMBERS.json').exists() or (out/'evidence.tar.gz').exists()):
        raise ValueError('Only one complete original C1 packet; no repack/retry')
    members=manifest(out)
    for name in members:
        safe_name(name)
        if (out/name).is_symlink():raise ValueError('No linked evidence')
    dump(out/'COMPACT_MEMBERS.json',members)
    with tarfile.open(out/'evidence.tar.gz','x:gz') as archive:
        for name in members:archive.add(out/name,arcname=name,recursive=False)
        archive.add(out/'COMPACT_MEMBERS.json',arcname='COMPACT_MEMBERS.json',recursive=False)
    return {'members':members,'members_file_sha256':sha(out/'COMPACT_MEMBERS.json'),
        'tar_sha256':sha(out/'evidence.tar.gz'),'tar_bytes':(out/'evidence.tar.gz').stat().st_size}


def extract(archive,out,artifact):
    """Only original completed packet; retain any partial destination on failure."""
    archive=Path(archive);out=Path(out)
    if sha(archive)!=artifact['tar_sha256'] or archive.stat().st_size!=artifact['tar_bytes']:
        raise ValueError('Original C1 archive bytes differ')
    expected={**artifact['members'],'COMPACT_MEMBERS.json':{
        'sha256':artifact['members_file_sha256'],'bytes':None}}
    for name in expected:safe_name(name)
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers();names=[m.name for m in members]
        if (len(names)!=len(set(names)) or set(names)!=set(expected)
                or any(not m.isfile() for m in members)):
            raise ValueError('Original archive has duplicate/missing/link/unexpected members')
        # Validate names/sizes before any destination is created.
        for m in members:
            safe_name(m.name);size=expected[m.name]['bytes']
            if size is not None and m.size!=size:raise ValueError('Original member size differs')
            if m.name=='COMPACT_MEMBERS.json' and m.size>10_000_000:
                raise ValueError('Unexpected manifest size')
        out.mkdir(parents=False,exist_ok=False)
        for m in members:
            dest=out/m.name;dest.parent.mkdir(parents=True,exist_ok=True)
            source=tar.extractfile(m);h=hashlib.sha256()
            with dest.open('xb') as f:
                for block in iter(lambda:source.read(2**20),b''):f.write(block);h.update(block)
            if h.hexdigest()!=expected[m.name]['sha256']:
                raise ValueError('Original extracted member bytes differ')
    if read(out/'COMPACT_MEMBERS.json')!=artifact['members']:
        raise ValueError('Original member manifest differs from returned receipt')
    return {'files':len(expected),'bytes_verified':True,'whole_helper_retry_allowed':False}


def original_completion(spec,receipt,provider,records,key,claim):
    if (receipt.get('status')!='completed' or records.get(key+'/terminal')!=receipt
            or records.get(key+'/claim')!=claim
            or provider.get('app_id')!=receipt.get('app_id')
            or not isinstance(receipt.get('app_id'),str)
            or not receipt['app_id'].startswith('ap-')
            or str(provider.get('state')).lower()!='stopped'
            or type(provider.get('owned_containers')) is not int
            or provider.get('owned_containers')!=0
            or type(provider.get('observed_epoch')) not in (int,float)
            or not math.isfinite(provider['observed_epoch'])
            or type(receipt.get('finished_epoch')) not in (int,float)
            or not math.isfinite(receipt['finished_epoch'])
            or provider['observed_epoch']<receipt['finished_epoch']
            or receipt.get('spec_sha256')!=digest(spec)
            or receipt.get('claim')!=claim):
        raise ValueError('Original completed receipt/claim and actual STOPPED0 required')
    c1_execution.validate_spec(spec)
    started=receipt['worker_start_epoch'];finished=receipt['finished_epoch']
    if (type(started) not in (int,float) or not math.isfinite(started)
            or not 0<=finished-started<spec['limits']['worker_seconds']
            or finished>=c1_execution.CUTOFF_EPOCH):
        raise ValueError('Original complete C1 hard window exceeded')
    return True


def check_complete(spec,receipt,provider,records,key,claim,payload,tasks,memberships,basis):
    original_completion(spec,receipt,provider,records,key,claim)
    payload=Path(payload);verify(payload,receipt['artifact']['members'])
    if sha(payload/'COMPACT_MEMBERS.json')!=receipt['artifact']['members_file_sha256']:
        raise ValueError('Original packet inventory bytes changed')
    proof=c1_execution.check_body(spec,payload,tasks,memberships,basis,records,key,claim)
    intent=read(payload/'INTENT.json');loaded=read(payload/'MODEL_LOADED.json')
    if (intent['worker_start_epoch']!=receipt['worker_start_epoch']
            or intent['deadline_epoch']!=receipt['worker_start_epoch']+spec['limits']['worker_seconds']
            or loaded.get('model')!=spec['model'] or loaded.get('forward')!=spec['forward']
            or loaded.get('optimizer_created') is not False or loaded.get('adapter_loaded') is not False
            or loaded.get('new_tokenization') is not False):
        raise ValueError('Actual original loader/forward/input/window proof differs')
    return {**proof,'original_provider_STOPPED0':True,'receipt_verified':True,
            'outer_source_review_budget_and_input_binding_still_required':True}
