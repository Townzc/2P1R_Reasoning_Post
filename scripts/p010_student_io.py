"""Create-only P010 student input transfer, hash-readback, no model calls."""
import argparse
import hashlib
from pathlib import Path
from experiments.p010.common import read, dump, verify, sha, utc


def upload(root, spec_file):
    import modal
    from modal.exception import NotFoundError
    root = Path(root)
    spec = read(spec_file)
    inputs = root/'student_inputs_r1'
    out = root/'student_input_upload_r1'
    verify(inputs, spec['input_files'])
    out.mkdir(exist_ok=False)
    dump(out/'INTENT.json', dict(spec_sha256=sha(spec_file), files=spec['input_files'], utc=utc()))
    volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
    files = {}
    for name, expected in spec['input_files'].items():
        remote = '/p010-20261019/student_inputs/'+name
        try:
            prior = b''.join(volume.read_file(remote))
        except NotFoundError:
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--spec', required=True)
    args = parser.parse_args()
    upload(args.root, args.spec)
