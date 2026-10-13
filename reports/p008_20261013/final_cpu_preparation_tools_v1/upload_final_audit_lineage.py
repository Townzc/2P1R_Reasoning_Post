"""PREPARED ONLY: once-only CPU input upload after actual code/numeric review."""
import hashlib
import json
import subprocess
from pathlib import Path
from prepare_final_audit_lineage import (
    R, ROOT, OUT, PUBLIC, CONFIG, code_review, remote_preflight, utc)
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify,manifest
from experiments.sft_allocation_p008.audit_lineage_binding import validate,validate_all_labels


def upload():
    import modal
    if (OUT/'UPLOAD_INTENT.json').exists() or (OUT/'UPLOAD_VERIFIED.json').exists():
        raise ValueError('Prior upload/partial; reconcile rather than rerun')
    review,source=code_review(); binding=read(OUT/'binding.json');spec=read(PUBLIC/'ADMISSION.json')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if head!=remote:raise ValueError('Ordinary publication required')
    for path in list(source)+[str((PUBLIC/'ADMISSION.json').relative_to(ROOT))]:
        if subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)!=(ROOT/path).read_bytes():
            raise ValueError('Unpublished source/spec')
    roster=validate(binding,spec,dict(source_files=source,spec_sha256=digest(spec)))
    inputs=OUT/CONFIG['input_directory'];verify(inputs,binding['input_manifest']['files'])
    if read(inputs/'manifest.json')!=binding['input_manifest']:raise ValueError('Manifest changed')
    labels={n:read(inputs/(n+'.json')) for n in roster};validate_all_labels(binding,labels)
    provider=remote_preflight(binding['plan'],binding['student_completion_owner'],binding['original_plan'],labels,
        {n:x['app_id'] for n,x in binding['labels'].items()},True)
    remote_path='/'+binding['plan']['campaign_id']+'/'+CONFIG['input_directory']
    files=manifest(inputs)
    dump(OUT/'UPLOAD_INTENT.json',dict(utc=utc(),binding_sha256=digest(binding),remote=remote_path,
        files=files,provider=provider,rule='No overwrite or whole-upload retry after partial failure'))
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    with volume.batch_upload(force=False) as batch:
        for name in sorted(files):batch.put_file(inputs/name,remote_path+'/'+name)
    actual={}
    for name,expected in files.items():
        h=hashlib.sha256();size=0
        for chunk in volume.read_file(remote_path+'/'+name):h.update(chunk);size+=len(chunk)
        actual[name]=dict(bytes=size,sha256=h.hexdigest())
        if actual[name]!=expected:raise ValueError('CPU input readback mismatch; preserve uploaded evidence')
    proof=dict(passed=True,utc=utc(),binding_sha256=digest(binding),input_manifest_sha256=digest(binding['input_manifest']),
        files=actual,remote=remote_path,model_calls=0,cpu_calls=0)
    dump(OUT/'UPLOAD_VERIFIED.json',proof)
    print(json.dumps(dict(passed=True,files=len(files),uploaded_bytes=sum(x['bytes'] for x in actual.values()),cpu_called=False)))


if __name__=='__main__':upload()
