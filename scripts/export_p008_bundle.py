"""Readonly P008 compact bundle + full state export. Never executes a model.

Bounded transfers use the existing range fetch; a partial failure is preserved
and requires explicit reconciliation, never an automatic full re-export.
"""
import argparse,json,re,subprocess,sys
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_allocation_p008.evidence_bundle import unpack


def export(args):
    import modal
    if not all(re.fullmatch(r'[A-Za-z0-9_.-]+',v) for v in (args.campaign,args.run)):raise ValueError('Unsafe remote path')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    env=read(args.receipt);files=env['artifact_manifest'];terminal=env['receipt']
    if terminal['status']!='completed' or digest(files)!=terminal['evidence_sha256']:
        raise ValueError('Completed immutable envelope required')
    v=modal.Volume.from_name(args.volume,create_if_missing=False);remote=f'/{args.campaign}/{args.run}'
    # Fetch metadata then the single compact object and terminal state binaries.
    transfer=out/'transfer';transfer.mkdir();needed=['compact_manifest.json','bundle_receipt.json','compact_evidence.tar.gz']
    needed += [n for n in files if n.endswith('/state.pt')]
    for name in needed:
        if name not in files:raise ValueError('Envelope lacks admitted transfer object')
        dst=transfer/name;dst.parent.mkdir(parents=True,exist_ok=True)
        from experiments.sft_allocation_p008.evidence_bundle import safe_name
        safe_name(name);record=files[name]
        if record['bytes']>=32*1024*1024:
            subprocess.run([sys.executable,'-m','scripts.midpoint_range_transfer','--volume',args.volume,
               '--remote',remote+'/'+name,'--target',str(dst),'--spec-json',json.dumps(record)],check=True,timeout=270)
        else:
            with dst.open('xb') as f:
                for block in v.read_file(remote+'/'+name):f.write(block)
        if dst.stat().st_size!=record['bytes'] or sha(dst)!=record['sha256']:raise ValueError('Transfer hash differs')
    evidence=out/'evidence'
    unpack(transfer/'compact_evidence.tar.gz',transfer/'compact_manifest.json',transfer/'bundle_receipt.json',evidence)
    # Hard link separately verified files; no overwriting immutable evidence.
    for name in needed:
        dst=evidence/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.hardlink_to(transfer/name)
    dump(evidence/'artifact_manifest.json',files);verify(evidence,files)
    result=dict(passed=True,files_verified=len(files),artifact_digest=digest(files),remote=remote,new_model_calls=0)
    dump(out/'EXPORT_VERIFIED.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('campaign','run','receipt','out'):p.add_argument('--'+k,required=True)
    p.add_argument('--volume',default='sft-allocation-midpoint-v1')
    a=p.parse_args();print(json.dumps(export(a)))
