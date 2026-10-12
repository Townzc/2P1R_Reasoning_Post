"""Read-only local export and SHA verification of a completed finite Modal run.

Leaves all remote files intact. Transfers compact evidence and selected complete
checkpoint states; never starts a Function or reconstructs permission from logs.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from experiments.sft_allocation_midpoint.common import dump,sha


def export(campaign,run,out,steps,bounded_large_files=False):
    import modal
    if not all(re.fullmatch(r'[A-Za-z0-9_.-]+',s) for s in (campaign,run)):
        raise ValueError('Unsafe run path')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    prefix=f'/{campaign}/{run}/'
    raw=b''.join(volume.read_file(prefix+'artifact_manifest.json'))
    records=json.loads(raw)
    with (out/'artifact_manifest.json').open('xb') as f:f.write(raw)
    selected={n:r for n,r in records.items() if not n.endswith('.pt') or n.split('/')[0] in {f'checkpoint_{s:04d}' for s in steps}}
    def fetch(pair):
        name,record=pair
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe artifact path')
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True)
        if bounded_large_files and record['bytes'] >= 32*1024*1024:
            # Isolate the SDK async client from this process's synchronous transfer loop.
            subprocess.run([sys.executable,'-m','scripts.midpoint_range_transfer',
                '--volume','sft-allocation-midpoint-v1','--remote',prefix+name,
                '--target',str(p),'--spec-json',json.dumps(record)],check=True,timeout=270)
        else:
            with p.open('xb') as f:
                for block in volume.read_file(prefix+name):f.write(block)
        if p.stat().st_size!=record['bytes'] or sha(p)!=record['sha256']:
            raise ValueError('Local bytes differ: '+name)
        return name
    with ThreadPoolExecutor(max_workers=6) as pool:verified=list(pool.map(fetch,selected.items()))
    receipt=dict(schema='independent_local_export_v1',campaign=campaign,run=run,
                 manifest_sha256=hashlib.sha256(raw).hexdigest(),files_verified=len(verified),
                 bytes=sum(r['bytes'] for r in selected.values()),full_checkpoint_steps=steps,
                 remote_files_unchanged=True,finished_epoch=time.time())
    dump(out/'LOCAL_VERIFICATION.json',receipt);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--campaign',required=True);p.add_argument('--run',required=True)
    p.add_argument('--out',required=True);p.add_argument('--checkpoint-steps',default='256')
    p.add_argument('--bounded-large-files',action='store_true')
    a=p.parse_args();print(json.dumps(export(a.campaign,a.run,a.out,[int(s) for s in a.checkpoint_steps.split(',') if s],a.bounded_large_files)))
