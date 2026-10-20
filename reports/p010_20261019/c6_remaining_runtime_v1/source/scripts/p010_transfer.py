"""Bounded input transfer and stopped-worker evidence retrieval; no model calls."""
import argparse
import hashlib
from pathlib import Path
from experiments.p010.common import dump,read,verify,utc,sha


def upload(root):
    import modal
    from modal.exception import NotFoundError
    root=Path(root);dest=root/'input_upload_r1';dest.mkdir(exist_ok=False)
    specs=[read('reports/p010_20261019/'+k+'_runtime_v1/SPEC.json') for k in ('teacher','e4')]
    files={}
    for spec in specs:
        for name,item in spec['input_files'].items():
            if name in files and files[name]!=item:raise ValueError('Conflicting input manifests')
            files[name]=item
    verify(root/'inputs',files)
    vol=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    remote='/p010-20261019/inputs'
    try:list(vol.iterdir(remote))
    except NotFoundError:pass
    else:raise ValueError('Remote input directory already exists; no whole-helper retry')
    dump(dest/'INTENT.json',dict(files=files,remote=remote,utc=utc()))
    observed={}
    for name,expected in files.items():
        with vol.batch_upload(force=False) as b:b.put_file(root/'inputs'/name,remote+'/'+name)
        h=hashlib.sha256();count=0
        for block in vol.read_file(remote+'/'+name):h.update(block);count+=len(block)
        item=dict(bytes=count,sha256=h.hexdigest())
        if item!=expected:raise ValueError('Input readback differs: '+name)
        observed[name]=item;dump(dest/'receipts'/(name+'.json'),item)
        print('Verified '+name,flush=True)
    dump(dest/'COMPLETED.json',dict(files=observed,utc=utc(),new_model_calls=0))


def collect(receipt,remote,out):
    import modal,json,subprocess,tarfile
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    receipt=Path(receipt);out=Path(out)
    result=read(receipt/'RESULT.json');sent=read(receipt/'SUBMITTED.json')
    if result['status']!='completed':raise ValueError('Original complete result required')
    cli='.local/midpoint_20261011/venv/bin/modal'
    containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
    owned=[c for c in containers if c.get('app_id')==sent['app_id']]
    info=read_stopped_apps(cli,[sent['app_id']],owned)
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'PROVIDER_PRIVATE.json',dict(app_id=sent['app_id'],original_info=info,owned=owned,utc=utc()))
    vol=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    with (out/'evidence.tar.gz').open('xb') as f:
        for block in vol.read_file(remote+'/evidence.tar.gz'):f.write(block)
    if sha(out/'evidence.tar.gz')!=result['artifact']['tar_sha256']:raise ValueError('Compact archive differs')
    with tarfile.open(out/'evidence.tar.gz') as t:
        expected=set(result['artifact']['compact_members'])|{'COMPACT_MEMBERS.json'}
        if {m.name for m in t.getmembers()}!=expected:raise ValueError('Archive member roster differs')
        for m in t.getmembers():
            if not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts:raise ValueError('Unsafe archive member')
            data=t.extractfile(m).read();target=out/'evidence'/m.name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(data)
    verify(out/'evidence',result['artifact']['compact_members'])
    # Original final state remains independently downloadable without replay.
    binaries={k:v for k,v in result['artifact']['all_files'].items() if k.endswith('.pt')}
    for name,expected in binaries.items():
        p=out/'evidence'/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:
            for block in vol.read_file(remote+'/'+name):f.write(block)
        verify(out/'evidence',{name:expected})
    dump(out/'COMPLETED.json',dict(utc=utc(),artifact=result['artifact'],original_result_sha256=sha(receipt/'RESULT.json'),provider_stopped=True,new_generations=0))

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='action',required=True)
    u=s.add_parser('upload');u.add_argument('--root',required=True)
    c=s.add_parser('collect');c.add_argument('--receipt',required=True);c.add_argument('--remote',required=True);c.add_argument('--out',required=True)
    a=p.parse_args()
    if a.action=='upload':upload(a.root)
    else:collect(a.receipt,a.remote,a.out)
