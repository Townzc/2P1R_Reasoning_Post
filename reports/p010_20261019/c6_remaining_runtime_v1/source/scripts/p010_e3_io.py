"""Create-only P010 student input transfer, hash-readback, no model calls."""
import argparse
import hashlib
import os
import threading
from pathlib import Path
from experiments.p010.common import read, dump, verify, sha, utc


def upload(root, spec_file):
    import modal
    from modal.exception import NotFoundError
    root = Path(root)
    spec = read(spec_file)
    inputs = root/'e3_inputs_r1'
    out = root/'e3_input_upload_r1'
    verify(inputs, spec['input_files'])
    out.mkdir(exist_ok=False)
    dump(out/'INTENT.json', dict(spec_sha256=sha(spec_file), files=spec['input_files'], utc=utc()))
    timer=threading.Timer(3600,lambda:os._exit(124))
    timer.daemon=True
    timer.start()
    try:
        return transfer(inputs,out,spec)
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),
            partial_valid_files_preserved=True,whole_helper_retry_allowed=False))
        raise
    finally:
        timer.cancel()


def transfer(inputs,out,spec):
    import modal
    from modal.exception import NotFoundError
    volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
    files = {}
    for name, expected in spec['input_files'].items():
        remote = '/p010-20261019/e3_inputs/'+name
        try:
            prior = b''.join(volume.read_file(remote))
        except (NotFoundError, FileNotFoundError):
            prior = None
        if prior is not None:
            actual = dict(bytes=len(prior), sha256=hashlib.sha256(prior).hexdigest())
            if actual != expected:
                raise ValueError('Existing remote bytes differ; no overwrite: '+name)
            files[name] = dict(**actual, reused_original=True)
        else:
            with volume.batch_upload(force=False) as batch:
                batch.put_file(inputs/name, remote)
            h = hashlib.sha256()
            count = 0
            for block in volume.read_file(remote):
                h.update(block)
                count += len(block)
            actual = dict(bytes=count, sha256=h.hexdigest())
            if actual != expected:
                raise ValueError('Actual uploaded bytes differ: '+name)
            files[name] = dict(**actual, reused_original=False)
        dump(out/'files'/(name+'.json'), files[name])
    dump(out/'COMPLETED.json', dict(files=files, utc=utc(), new_model_calls=0))


def collect_once(receipt,remote,out):
    from scripts.p010_transfer import collect
    if Path(out).exists():raise FileExistsError('No whole-collector retry')
    timer=threading.Timer(3600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        return collect(receipt,remote,out)
    except BaseException as exc:
        if Path(out).exists() and not (Path(out)/'FAILED.json').exists():
            dump(Path(out)/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False))
        raise
    finally:timer.cancel()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='action',required=True)
    q=sub.add_parser('upload');q.add_argument('--root',required=True);q.add_argument('--spec',required=True)
    q=sub.add_parser('collect')
    for name in ('receipt','remote','out'):q.add_argument('--'+name,required=True)
    args = parser.parse_args()
    if args.action=='upload':upload(args.root, args.spec)
    else:collect_once(args.receipt,args.remote,args.out)
