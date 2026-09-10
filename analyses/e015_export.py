"""Bounded local checkpoint export; transport/authentication belong to the caller.

``copy_checkpoint`` creates a new destination with exactly the model files in
``checkpoint_final/`` and a separate ``transfer_receipt.json``. A remote opener
receives (plain filename, whole-transfer seconds remaining) and returns a binary
context manager. It must apply a channel/read timeout no greater than
``min(20, remaining_seconds)`` and must not suppress deadline exceptions.
Connection setup done before calling this helper is outside its deadline; any
setup in the opener, context entry/exit, streaming and verification is inside.

The POSIX main-thread alarm also interrupts a blocking read. No retry, credential
discovery, remote connection or rental shutdown is performed here. On failure,
verified files and unfinished .part files remain, together with a partial receipt;
the helper raises and never reports those files as a completed backup. Failure
receipt cleanup runs after disabling the alarm, so preservation can add a small
amount of local time beyond the transfer deadline.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import threading
import time


CHUNK_BYTES = 8 * 1024 * 1024
PROGRESS_BYTES = 64 * 1024 * 1024
CHECKPOINT_FILENAMES = frozenset({
    'added_tokens.json', 'chat_template.jinja', 'config.json',
    'generation_config.json', 'merges.txt', 'model-00001-of-00002.safetensors',
    'model-00002-of-00002.safetensors', 'model.safetensors.index.json',
    'special_tokens_map.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json',
})


def _plain_filename(name):
    return (isinstance(name, str) and name not in ('', '.', '..')
            and Path(name).name == name and not any(c in name for c in ('/', '\\', '\x00')))


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _validate_manifest(manifest, allowed_filenames):
    if not isinstance(manifest, dict) or manifest.get('kind') != 'weights_only_not_optimizer_rng_resume':
        raise ValueError('Expected a weights-only checkpoint manifest')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError('Checkpoint manifest must contain file entries')
    if not all(_plain_filename(name) for name in files):
        raise ValueError('Checkpoint entries must be plain filenames')
    allowed = set(allowed_filenames)
    if not allowed or not all(_plain_filename(name) for name in allowed) or set(files) != allowed:
        raise ValueError('Checkpoint filename allowlist differs')
    for item in files.values():
        if (not isinstance(item, dict) or set(item) != {'bytes', 'sha256'}
                or type(item['bytes']) is not int or item['bytes'] <= 0 or not _digest(item['sha256'])):
            raise ValueError('Each checkpoint entry needs a positive integer size and lowercase SHA256')
    return {name: dict(files[name]) for name in sorted(files)}


def _remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise TimeoutError('Whole checkpoint transfer deadline exceeded')
    return seconds


@contextmanager
def _wall_deadline(max_seconds):
    if (isinstance(max_seconds, bool) or not isinstance(max_seconds, (int, float))
            or not math.isfinite(max_seconds) or max_seconds <= 0):
        raise ValueError('Transfer duration must be a positive finite number')
    if (threading.current_thread() is not threading.main_thread()
            or not all(hasattr(signal, name) for name in ('SIGALRM', 'ITIMER_REAL', 'setitimer', 'getitimer'))):
        raise RuntimeError('A POSIX main-thread alarm is required for a blocking-read deadline')
    if any(signal.getitimer(signal.ITIMER_REAL)):
        raise RuntimeError('Refusing to replace an existing active real-time alarm')
    previous_handler = signal.getsignal(signal.SIGALRM)
    started = time.monotonic()

    def expired(signum, frame):
        raise TimeoutError('Whole checkpoint transfer deadline exceeded')

    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, max_seconds)
        yield started, started + max_seconds
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _save_receipt(destination, receipt):
    temporary = destination / '.transfer_receipt.json.tmp'
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(destination / 'transfer_receipt.json')


def copy_checkpoint(open_remote, manifest, destination, max_seconds=1320, *,
                    progress=None, manifest_sha256=None, allowed_filenames=CHECKPOINT_FILENAMES):
    """Verify a streamed copy into a never-used directory, or raise with partials.

    ``manifest_sha256`` is optional caller-supplied source-file provenance; this
    helper cannot verify the original JSON byte digest from a parsed dictionary.
    The separate canonical manifest digest binds this receipt to its exact file
    entries. ``progress(event)`` receives concise per-file/64-MiB/20-second events
    and is subject to the same deadline. The returned receipt exists only after
    every file has passed byte-count and SHA256 checks.

    Publishing a verified .part uses an atomic hard link followed by unlink;
    unlike overwrite-permitting POSIX rename, this cannot replace another file.
    """
    destination = Path(destination)
    created = False
    receipt = None
    started = time.monotonic()
    try:
        with _wall_deadline(max_seconds) as (started, deadline):
            files = _validate_manifest(manifest, allowed_filenames)
            if manifest_sha256 is not None and not _digest(manifest_sha256):
                raise ValueError('Caller-supplied manifest SHA256 is malformed')
            if not callable(open_remote) or (progress is not None and not callable(progress)):
                raise ValueError('Transfer opener and optional progress handler must be callable')
            destination.mkdir()  # Atomic refusal of files, directories and dangling symlinks.
            created = True
            folder = destination / 'checkpoint_final'
            folder.mkdir()
            receipt = {
                'schema': 'e015_checkpoint_export_v1', 'status': 'in_progress',
                'kind': manifest['kind'], 'all_files_verified': False, 'full_backup_verified': False,
                'checkpoint_directory': 'checkpoint_final', 'expected_file_count': len(files),
                'expected_bytes': sum(item['bytes'] for item in files.values()),
                'bytes_written': 0, 'verified_files': {}, 'partial_files': {},
                'max_seconds': max_seconds, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
                'elapsed_seconds': 0.0, 'rental_billing_status': 'not_checked',
                'canonical_file_entries_sha256': hashlib.sha256(json.dumps(
                    files, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                'source_manifest_sha256': manifest_sha256,
                'source_manifest_hash_provenance': 'caller_supplied_not_verified_from_original_json_bytes',
                'deadline_scope': 'Includes opener, context entry/exit, streaming and verification; '
                                  'excludes connection setup before this call and failure receipt cleanup.',
            }
            _save_receipt(destination, receipt)

            def notify(event, name, byte_count):
                if progress is not None:
                    progress({'event': event, 'filename': name, 'file_bytes': byte_count,
                              'expected_file_bytes': files[name]['bytes'],
                              'verified_file_count': len(receipt['verified_files']),
                              'elapsed_seconds': time.monotonic() - started})
                _remaining(deadline)

            for name, expected in files.items():
                partial = folder / (name + '.part')
                final = folder / name
                count = 0
                digest = hashlib.sha256()
                receipt['partial_files'][name + '.part'] = {'bytes': 0, 'sha256_of_partial_bytes': digest.hexdigest()}
                notify('file_started', name, 0)
                last_bytes, last_notice = 0, time.monotonic()
                with partial.open('xb') as output:
                    # Every opener invocation, including transport setup, is guarded.
                    with open_remote(name, _remaining(deadline)) as source:
                        while True:
                            _remaining(deadline)
                            chunk = source.read(CHUNK_BYTES)
                            _remaining(deadline)
                            if not isinstance(chunk, bytes) or len(chunk) > CHUNK_BYTES:
                                raise ValueError('Remote stream must return bounded binary bytes')
                            if not chunk:
                                break
                            output.write(chunk)
                            count += len(chunk)
                            receipt['bytes_written'] += len(chunk)
                            digest.update(chunk)
                            receipt['partial_files'][name + '.part'] = {
                                'bytes': count, 'sha256_of_partial_bytes': digest.hexdigest()}
                            if count > expected['bytes']:
                                raise ValueError('Checkpoint file exceeds its manifest size: ' + name)
                            now = time.monotonic()
                            if count - last_bytes >= PROGRESS_BYTES or now - last_notice >= 20:
                                notify('file_progress', name, count)
                                last_bytes, last_notice = count, now
                    output.flush()
                    os.fsync(output.fileno())
                _remaining(deadline)
                if count != expected['bytes'] or digest.hexdigest() != expected['sha256']:
                    raise ValueError('Checkpoint size/SHA256 verification failed: ' + name)
                os.link(partial, final)  # Atomic no-overwrite publication after verification.
                partial.unlink()
                del receipt['partial_files'][name + '.part']
                receipt['verified_files'][name] = dict(expected)
                receipt['elapsed_seconds'] = time.monotonic() - started
                _save_receipt(destination, receipt)
                notify('file_verified', name, count)
            _remaining(deadline)
            if {path.name for path in folder.iterdir()} != set(files):
                raise ValueError('Copied checkpoint inventory is not exactly the manifest')
            receipt.update(status='completed', all_files_verified=True, full_backup_verified=True,
                           elapsed_seconds=time.monotonic() - started,
                           finished_at_utc=datetime.now(timezone.utc).isoformat())
            _save_receipt(destination, receipt)
            _remaining(deadline)
        return receipt
    except BaseException as exc:
        if created and receipt is not None:
            receipt.update(status='partial_not_full_backup', all_files_verified=False,
                           full_backup_verified=False, failure_type=type(exc).__name__,
                           failure=str(exc), elapsed_seconds=time.monotonic() - started,
                           finished_at_utc=datetime.now(timezone.utc).isoformat())
            try:
                _save_receipt(destination, receipt)
            except Exception as cleanup_error:
                if hasattr(exc, 'add_note'):
                    exc.add_note('Partial receipt could not be saved: ' + str(cleanup_error))
        raise
