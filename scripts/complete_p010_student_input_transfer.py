"""One bounded missing-only completion of the saved zero-write upload failure.

The original helper, log and intent are retained; matching remote bytes are read
back and reused, never overwritten. No model, claim or source is changed.
"""
import argparse
import hashlib
import os
from pathlib import Path
import threading

from experiments.p010.common import read, dump, sha, verify, utc


def complete(root, spec_file):
    import modal
    from modal.exception import NotFoundError
    root = Path(root); spec = read(spec_file)
    previous = root/'student_input_upload_r1'
    intent = read(previous/'INTENT.json')
    log = root/'student_input_upload_r1.log'
    if (intent['spec_sha256'] != sha(spec_file) or intent['files'] != spec['input_files']
            or (previous/'COMPLETED.json').exists() or list((previous/'files').glob('**/*.json'))
            or 'FileNotFoundError' not in log.read_text()
            or '/p010-20261019/student_inputs/MATH_ENDPOINT.json' not in log.read_text()):
        raise ValueError('Only the preserved first-read zero-write failure is covered')
    verify(root/'student_inputs_r1', spec['input_files'])
    out = root/'student_input_transfer_completion_r1'; out.mkdir(exist_ok=False)
    dump(out/'INTENT.json', dict(utc=utc(), original_intent_sha256=sha(previous/'INTENT.json'),
        original_failure_log_sha256=sha(log), spec_sha256=sha(spec_file),
        local_hard_seconds=900, missing_only=True, overwrite=False, model_calls=0))
    timer = threading.Timer(900, lambda: os._exit(124)); timer.daemon = True; timer.start()
    try:
        volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        observed = {}
        for name, expected in spec['input_files'].items():
            remote = '/p010-20261019/student_inputs/'+name
            try:
                data = b''.join(volume.read_file(remote))
            except (FileNotFoundError, NotFoundError):
                data = None
            # Write-ahead intent is per file, before any new upload.
            dump(out/'files'/(name+'.intent.json'), dict(remote=remote, expected=expected,
                previously_exists=data is not None, utc=utc()))
            if data is None:
                with volume.batch_upload(force=False) as batch:
                    batch.put_file(root/'student_inputs_r1'/name, remote)
                data = b''.join(volume.read_file(remote))
                reused = False
            else:
                reused = True
            actual = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            if actual != expected:
                raise ValueError('Readback differs; no overwrite/retry: '+name)
            observed[name] = dict(**actual, reused_existing=reused)
            dump(out/'files'/(name+'.done.json'), observed[name])
        result = dict(utc=utc(), files=observed, original_failure_retained=True,
            original_intent_sha256=sha(previous/'INTENT.json'),
            new_model_calls=0, overwritten_files=0, automatic_retry=False)
        dump(out/'COMPLETED.json', result)
        return result
    except BaseException as exc:
        dump(out/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
            valid_parts_retained=True, whole_helper_retry=False))
        raise
    finally:
        timer.cancel()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True); parser.add_argument('--spec', required=True)
    args = parser.parse_args(); result = complete(args.root, args.spec)
    print(dict(files=len(result['files']), new_model_calls=0, overwritten_files=0))
