"""Verify a cached snapshot against file identities fetched from the official HF API.

LFS weights use SHA-256; ordinary Git files use Git blob SHA-1. Remote mirrors
supply bytes only, never the trusted expected digest. Also checks file sizes.
"""
import argparse
import hashlib
import json
from pathlib import Path
from huggingface_hub import snapshot_download

p=argparse.ArgumentParser()
p.add_argument('--role', choices=['debug','main'], required=True)
p.add_argument('--out', required=True)
a=p.parse_args()
lock=json.loads(Path('configs/models.lock.json').read_text())[a.role]
root=Path(snapshot_download(lock['repo_id'],revision=lock['revision'],local_files_only=True))
verified=[]
for file in lock['files']:
    path=root/file['rfilename']
    size=path.stat().st_size
    if size != file['size']: raise ValueError(f'Size mismatch: {path.name}')
    if file.get('lfs'):
        hasher=hashlib.sha256(); expected=file['lfs']['sha256']; algorithm='sha256'
    else:
        hasher=hashlib.sha1(f'blob {size}\0'.encode()); expected=file['blobId']; algorithm='git-blob-sha1'
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''): hasher.update(chunk)
    actual=hasher.hexdigest()
    if actual != expected: raise ValueError(f'Digest mismatch: {path.name}')
    verified.append({'file':path.name,'bytes':size,'algorithm':algorithm,'digest':actual})
report={'repo_id':lock['repo_id'],'revision':lock['revision'],'all_files_verified':True,
        'expected_digest_source':'official huggingface.co API at the pinned revision','files':verified}
with Path(a.out).open('x') as f: json.dump(report,f,indent=2); f.write('\n')
print(json.dumps({'all_files_verified':True,'files':len(verified)}))
