"""Extend the public accounting snapshot using already public immutable receipts.

The private ledger is a read-only reconciliation input, never the output file.
Existing public history and hardware charges must remain an exact prefix.
"""
import argparse
import copy
import json
from pathlib import Path


def reconcile(previous, ledger, run_root=Path('runs')):
    result=copy.deepcopy(previous); root=Path(run_root)
    if ledger['budget_id']!=previous['budget_id'] or ledger['authorized_gpu_seconds']!=7200 or previous['authorized_gpu_seconds']!=7200:
        raise ValueError('Original authorization changed')
    old=previous['jobs']; jobs=ledger['jobs']
    if jobs[:len(old)]!=old or len(jobs)<len(old): raise ValueError('Public accounting is not an exact ledger prefix')
    if len({j['run_id'] for j in jobs})!=len(jobs) or any(j['status']=='reserved' or type(j['charged_seconds']) is not int or j['charged_seconds']<0 for j in jobs):
        raise ValueError('Duplicate, unresolved or invalid ledger entries')
    if previous['charged_gpu_seconds']!=sum(j['charged_seconds'] for j in old) or sum(previous['hardware_charged_seconds'].values())!=previous['charged_gpu_seconds']:
        raise ValueError('Existing accounting totals are inconsistent')
    for i,job in enumerate(jobs):
        public=json.loads((root/job['run_id']/'resource_receipt.json').read_text())
        if public!=job: raise ValueError('Private ledger differs from public immutable receipt')
        if i<len(old): continue
        manifest_path=root/job['run_id']/'run_manifest.json'
        manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        gpu=manifest.get('server',{}).get('gpu','')
        hardware='A800_80GB' if 'A800' in gpu and int(gpu.split(',')[1].strip())>=75000 else 'unclassified'
        result['hardware_charged_seconds'][hardware]=result['hardware_charged_seconds'].get(hardware,0)+public['charged_seconds']
        result['jobs'].append(public)
    used=sum(j['charged_seconds'] for j in result['jobs'])
    result.update(charged_gpu_seconds=used,remaining_gpu_seconds=7200-used,gpu_hours=used/3600)
    return result


def main():
    p=argparse.ArgumentParser(); p.add_argument('--ledger',required=True); args=p.parse_args()
    path=Path('reports/compute_accounting.json'); original=path.read_bytes()
    result=reconcile(json.loads(original),json.loads(Path(args.ledger).read_text()))
    if path.read_bytes()!=original: raise ValueError('Accounting changed during reconciliation')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'jobs':len(result['jobs']),'charged_gpu_seconds':result['charged_gpu_seconds'],'remaining_gpu_seconds':result['remaining_gpu_seconds']}))


if __name__=='__main__': main()
