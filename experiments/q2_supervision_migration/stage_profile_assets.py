"""Stage only pinned public assets. Weights require explicit --include-model.

Never imports a model or executes task code. Each destination is exclusive; a
partial download remains as evidence and requires manual reconciliation.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

ASSETS = Path(__file__).resolve().parent / 'assets'


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def fetch(item, path, deadline):
    path=Path(path)
    if path.exists():
        if path.stat().st_size == item['bytes'] and sha256(path)==item['sha256']:
            return {'file':path.name,'sha256':item['sha256'],'reused_verified':True}
        raise ValueError('existing asset does not match frozen identity')
    transfer=path.parent.parent/'transfer_evidence'
    transfer.mkdir(parents=True,exist_ok=True)
    partial=transfer/(path.name+'.partial')
    with partial.open('xb') as out:
        with urllib.request.urlopen(item['url'],timeout=25) as r:
            size=0
            while True:
                if time.monotonic()>=deadline:raise TimeoutError('asset staging deadline')
                b=r.read(1024*1024)
                if not b:break
                size+=len(b)
                if size>item['bytes']:raise ValueError('asset exceeds recorded size')
                out.write(b)
        out.flush();os.fsync(out.fileno())
    if size != item['bytes'] or sha256(partial)!=item['sha256']:
        raise ValueError('download identity mismatch; partial preserved')
    os.link(partial,path)  # atomic no-clobber publication; retain .partial evidence
    return {'file':path.name,'sha256':item['sha256'],'reused_verified':False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--include-model',action='store_true')
    p.add_argument('--seconds',type=int,default=600)
    a=p.parse_args()
    if not 1<=a.seconds<=900:p.error('staging limit must be 1..900 seconds')
    a.out.mkdir(parents=True,exist_ok=False)
    deadline=time.monotonic()+a.seconds
    rec=[]
    d=json.loads((ASSETS/'data_manifest.json').read_text())
    with urllib.request.urlopen(d['url'],timeout=25) as r:
        compressed=r.read(d['compressed_bytes']+1)
    if len(compressed)!=d['compressed_bytes']:raise ValueError('dataset compressed size')
    raw=gzip.decompress(compressed)
    if len(raw)!=d['uncompressed_bytes'] or hashlib.sha256(raw).hexdigest()!=d['sha256']:
        raise ValueError('dataset identity mismatch')
    with (a.out/'MbppPlus.jsonl').open('xb') as f:f.write(raw)
    rec.append({'file':'MbppPlus.jsonl','sha256':d['sha256'],'bytes':len(raw)})
    sp=(ASSETS/'split.json').read_bytes()
    if hashlib.sha256(sp).hexdigest()!=d['split_sha256']:raise ValueError('split identity')
    with (a.out/'split.json').open('xb') as f:f.write(sp)
    model=json.loads((ASSETS/'model_manifest.json').read_text())
    if a.include_model:
        md=a.out/'model';md.mkdir()
        for row in model['files']:
            if Path(row['path']).name!=row['path']:raise ValueError('unexpected model path')
            rec.append(fetch(row,md/row['path'],deadline))
    with (a.out/'model_manifest.json').open('x') as f:json.dump(model,f,indent=2)
    with (a.out/'staging_receipt.json').open('x') as f:
        json.dump({'files':rec,'model_weights_requested':a.include_model,
                   'new_model_generations':0,'new_program_executions':0},f,indent=2)
    print('Staged pinned assets; no model or candidate program executed.')

if __name__=='__main__':main()
