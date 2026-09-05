"""Verify a separately transferred model checkpoint without disclosing host paths."""
import argparse
import hashlib
import json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--manifest',required=True)
p.add_argument('--directory',required=True)
p.add_argument('--out',required=True)
a=p.parse_args()
manifest=json.loads(Path(a.manifest).read_text())
verified=[]
for name,expected in manifest['files'].items():
    if Path(name).name!=name or name in ('.','..'): raise ValueError('Unsafe artifact filename')
    path=Path(a.directory)/name
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''): digest.update(chunk)
    actual=digest.hexdigest()
    if actual!=expected: raise ValueError(f'Artifact digest mismatch: {name}')
    verified.append({'file':name,'bytes':path.stat().st_size,'sha256':actual})
report={'all_files_verified':True,'kind':manifest['kind'],'files':verified}
with Path(a.out).open('x') as f: json.dump(report,f,indent=2); f.write('\n')
print(json.dumps({'all_files_verified':True,'files':len(verified)}))
