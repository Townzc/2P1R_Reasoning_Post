"""New owner-approved 02:05 UTC analyses; existing P011 artifacts stay immutable."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os

OWNER_SHA = '81ac2e124cc995fe11462fb02bf8866b6f04ee944a0857430384bbb7294f1729'


def utc():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def create(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def admit(spec_path, review_path, scope):
    spec, review = read(spec_path), read(review_path)
    if (spec['owner_report_sha256'] != OWNER_SHA or review['scope'] != scope
            or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or review['spec_sha256'] != sha(spec_path)
            or review['source_files'] != spec['source_files']
            or review['owner_report_sha256'] != OWNER_SHA
            or sha(review['local_report_path']) != review['report_sha256']
            or any(review.get(k) is not True for k in spec['required_source_review_flags'])):
        raise ValueError('Exact new-path Claude CR and owner decision binding required')
    for path, wanted in spec['source_files'].items():
        if sha(path) != wanted:
            raise ValueError('New reviewed source binding changed: ' + path)
    return spec


def checked_metadata(binding):
    path = Path(binding['path'])
    if sha(path) != binding['sha256']:
        raise ValueError('Bound original metadata changed: ' + str(path))
    return read(path)
