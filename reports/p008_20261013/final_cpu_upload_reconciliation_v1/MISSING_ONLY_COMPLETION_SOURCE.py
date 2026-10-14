"""One bounded completion of exactly reconciled missing CPU input files.

Does not repeat the original batch uploader. One file per commit, force=False;
persist each intent and readback. Any unknown/partial stops without retry.
No model or CPU function call. Original upload failure remains intact.
"""
from pathlib import Path
import datetime
import hashlib
import json
import signal
import subprocess
import time
import modal
from modal.exception import NotFoundError
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest

R = Path(__file__).resolve().parent
P = R / 'student_completion_r1/final_audit_t8_cap_r1'
OUT = P / 'upload_missing_completion_r1'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def list_files(volume, path):
    try:
        entries = list(volume.iterdir(path, recursive=True))
    except NotFoundError:
        return {}
    return {x.path.lstrip('/'):dict(bytes=x.size, type=int(x.type))
            for x in entries if int(x.type) == 1}


def run():
    if OUT.exists() or (P/'UPLOAD_VERIFIED.json').exists() or (P/'runs/audit').exists():
        raise ValueError('Existing repair/verification/dispatch; no whole repair replay')
    interruption = read(P/'UPLOAD_TRANSPORT_INTERRUPT.json')
    proc = subprocess.run(['ps','-p',str(interruption['pid']),'-o','command='],capture_output=True,text=True)
    if proc.returncode == 0 and 'upload_final_audit_t8_cap.py' in proc.stdout:
        raise ValueError('Original uploader has not stopped')
    prior = read(P/'upload_reconciliation_r1/REMOTE_LISTING.json')
    intent = read(P/'UPLOAD_INTENT.json')
    binding = read(P/'binding.json')
    if prior['unexpected'] or set(prior['missing']) != set(intent['files']) or prior['present']:
        raise ValueError('This bounded repair only covers the actually observed empty destination')
    inputs = P/binding['config']['input_directory']
    expected = intent['files']
    for name, record in expected.items():
        f = inputs/name
        if f.is_symlink() or f.stat().st_size != record['bytes'] or sha(f) != record['sha256']:
            raise ValueError('Original immutable input bytes changed')
    head = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    remote_head = subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],text=True).split()[0]
    if head != remote_head:
        raise ValueError('Original publication must remain synchronized')
    volume = modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    claims = modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    prefix = 'midpoint/'+binding['plan']['campaign_id']+'/'
    if any(claims.get(prefix+k+'/audit') is not None for k in ('claim','intent','terminal')):
        raise ValueError('CPU already attempted; no input mutation allowed')
    remote_path = intent['remote']
    before = list_files(volume,remote_path)
    if before:
        raise ValueError('Destination changed after stopped-uploader reconciliation')
    if time.time()+4000 > binding['plan']['deadline_epoch']:
        raise ValueError('Original full CPU window unavailable')
    OUT.mkdir()
    dump(OUT/'READ_WRITE_INTENT.json',dict(utc=utc(),original_upload_intent_sha256=sha(P/'UPLOAD_INTENT.json'),
        reconciliation_sha256=sha(P/'upload_reconciliation_r1/REMOTE_LISTING.json'),
        files=expected,remote=remote_path,max_seconds=600,force=False,
        parallel_upload_files=1,models_called=0,CPU_called=0,
        rule='Missing-only once per file; preserve unknown/partial, no retry'))
    def timeout(signum, frame):
        raise TimeoutError('Bounded missing-file completion exceeded600local seconds')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(600)
    actual = {}
    try:
        for i,(name,record) in enumerate(sorted(expected.items())):
            key = hashlib.sha256(name.encode()).hexdigest()
            dump(OUT/'file_intents'/f'{key}.json',dict(utc=utc(),name=name,expected=record,remote=remote_path+'/'+name))
            with volume.batch_upload(force=False) as batch:
                batch.put_file(inputs/name,remote_path+'/'+name)
            h=hashlib.sha256();size=0
            for chunk in volume.read_file(remote_path+'/'+name):
                h.update(chunk);size+=len(chunk)
            got=dict(bytes=size,sha256=h.hexdigest())
            if got!=record:
                raise ValueError('Newly committed original input readback mismatch')
            dump(OUT/'file_verified'/f'{key}.json',dict(utc=utc(),name=name,actual=got,passed=True))
            actual[name]=got
            print(json.dumps(dict(completed=i+1,total=len(expected),name=name,bytes=size)),flush=True)
        after=list_files(volume,remote_path)
        wanted={remote_path.lstrip('/')+'/'+name:record['bytes'] for name,record in expected.items()}
        if set(after)!=set(wanted) or any(after[n]['bytes']!=wanted[n] for n in wanted):
            raise ValueError('After-listing contains missing/foreign input files')
        dump(OUT/'REMOTE_AFTER.json',dict(utc=utc(),files=after))
        proof=dict(passed=True,utc=utc(),binding_sha256=digest(binding),
            input_manifest_sha256=digest(binding['input_manifest']),files=actual,remote=remote_path,
            model_calls=0,cpu_calls=0,route='missing_only_serial_completion_after_stopped_failed_batch',
            original_upload_intent_sha256=sha(P/'UPLOAD_INTENT.json'),
            original_failure_sha256=sha(P/'UPLOAD_TRANSPORT_INTERRUPT.json'),
            completion_intent_sha256=sha(OUT/'READ_WRITE_INTENT.json'),
            completed_file_readbacks=len(actual),remote_overwrites=0)
        dump(OUT/'COMPLETED.json',proof)
        dump(P/'UPLOAD_VERIFIED.json',proof)
        print(json.dumps(dict(passed=True,files=len(actual),CPU_called=False)),flush=True)
    except BaseException as exc:
        dump(OUT/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),
            verified_files=actual,rule='Preserve partial intents/readbacks; do not repeat helper'))
        raise
    finally:
        signal.alarm(0)


if __name__=='__main__':
    run()
