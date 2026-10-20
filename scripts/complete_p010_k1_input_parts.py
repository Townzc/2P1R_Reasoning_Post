"""One bounded completion of unconfirmed input files after an ended upload.

Not a model retry. Original confirmed hash readbacks are reused as immutable
proofs; unconfirmed names are read first and uploaded only when actually absent.
Original intent, partial proofs and termination evidence remain untouched.
"""
import argparse
import hashlib
import os
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from experiments.p010.common import read, dump, sha, verify, utc


def confirmed_parts(previous, spec):
    values={}
    for p in sorted((previous/'files').rglob('*.json')):
        name=str(p.relative_to(previous/'files'))[:-5]
        if name not in spec['input_files']: raise ValueError('Unexpected original partial proof')
        value=read(p); actual={k:value[k] for k in ('bytes','sha256')}
        if actual!=spec['input_files'][name] or type(value.get('reused_original')) is not bool:
            raise ValueError('Original confirmed partial readback differs')
        values[name]=dict(**actual,reused_confirmed_readback=True,
            original_partial_proof_sha256=sha(p),remote_uploaded_again=False)
    return values


def finish_missing(volume,inputs,out,expected,confirmed,missing_exceptions):
    results=dict(confirmed)
    for name,value in confirmed.items(): dump(out/'confirmed_reuse'/(name+'.json'),value)
    def transfer(name):
        remote='/p010-20261019/student_inputs/'+name
        dump(out/'files'/(name+'.intent.json'),dict(utc=utc(),name=name,remote=remote,
            expected=expected[name],overwrite=False,automatic_retry=False))
        h=hashlib.sha256();n=0;missing=False
        try:
            for block in volume.read_file(remote): h.update(block);n+=len(block)
        except missing_exceptions: missing=True
        if missing:
            # No overwrite; unknown transient errors propagate instead of upload.
            with volume.batch_upload(force=False) as batch: batch.put_file(inputs/name,remote)
            h=hashlib.sha256();n=0
            for block in volume.read_file(remote):h.update(block);n+=len(block)
        actual=dict(bytes=n,sha256=h.hexdigest())
        if actual!=expected[name]: raise ValueError('Unconfirmed remote bytes differ; no overwrite: '+name)
        value=dict(**actual,reused_confirmed_readback=False,remote_uploaded_again=False,
            existing_remote_reused=not missing,previously_unconfirmed=True)
        dump(out/'files'/(name+'.done.json'),value)
        return name,value
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(transfer,name) for name in expected if name not in confirmed]
        for f in as_completed(futures):
            name,value=f.result();results[name]=value
    return results


def complete(root,spec_file,failure_file):
    import modal
    from modal.exception import NotFoundError
    root=Path(root);spec=read(spec_file);previous=root/'student_input_upload_r2'
    failure=read(failure_file);intent=read(previous/'INTENT.json')
    if (failure.get('original_cli_session')!=51950 or failure.get('exit_code')!=124
            or failure.get('original_process_confirmed_absent') is not True
            or failure.get('new_scientific_calls')!=0
            or failure.get('original_intent_sha256')!=sha(previous/'INTENT.json')
            or intent['spec_sha256']!=sha(spec_file) or intent['files']!=spec['input_files']
            or (previous/'COMPLETED.json').exists()):
        raise ValueError('Only original ended1200-second upload with preserved evidence is covered')
    pid=failure['original_pid']
    try:os.kill(pid,0)
    except ProcessLookupError:pass
    else:raise ValueError('Original upload PID still exists or was reused; do not overlap')
    verify(root/'student_inputs_r2',spec['input_files'])
    confirmed=confirmed_parts(previous,spec)
    out=root/'student_input_parts_completion_r1';out.mkdir(exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),original_intent_sha256=sha(previous/'INTENT.json'),
        failure_file_sha256=sha(failure_file),spec_sha256=sha(spec_file),
        original_confirmed_files=len(confirmed),unconfirmed_files=len(spec['input_files'])-len(confirmed),
        local_hard_seconds=3600,maximum_readers=2,missing_only=True,overwrite=False,
        whole_original_helper_repeated=False,new_model_calls=0))
    timer=threading.Timer(3600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
        files=finish_missing(volume,root/'student_inputs_r2',out,spec['input_files'],confirmed,
            (FileNotFoundError,NotFoundError))
        result=dict(utc=utc(),files=files,spec_sha256=sha(spec_file),
            original_intent_sha256=sha(previous/'INTENT.json'),original_failure_retained=True,
            new_model_calls=0,overwritten_files=0,whole_helper_retry=False)
        dump(out/'COMPLETED.json',result);return result
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),
            valid_parts_preserved=True,whole_helper_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('root','spec','failure'):p.add_argument('--'+key,required=True)
    a=p.parse_args();v=complete(a.root,a.spec,a.failure)
    print(dict(complete_files=len(v['files']),new_model_calls=0,overwritten_files=0))
