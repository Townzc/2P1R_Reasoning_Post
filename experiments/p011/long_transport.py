"""Bounded create-only full binary evidence archive, no reload or scoring."""
from pathlib import Path
import hashlib
import tarfile
from experiments.sft_allocation_midpoint.common import dump,read,sha,manifest,verify


def safe(name):
    p=Path(name)
    if not name or p.is_absolute() or '..' in p.parts or str(p)!=name:raise ValueError('Unsafe member')
    return p


def pack(root,maximum):
    root=Path(root)
    if not (root/'RESULT.json').is_file() or (root/'FAILURE.json').exists():raise ValueError('Only complete payload may pack')
    if (root/'EVIDENCE_MEMBERS.json').exists() or (root/'evidence.tar').exists():raise ValueError('Archive cannot repeat')
    for p in root.rglob('*'):
        if p.is_symlink():raise ValueError('No symlink evidence')
    members=manifest(root)
    if sum(v['bytes'] for v in members.values())>maximum:raise ValueError('Declared maximum exceeded')
    dump(root/'EVIDENCE_MEMBERS.json',members)
    # Uncompressed: no lossy projection, all full state/export/raw members.
    with tarfile.open(root/'evidence.tar','x') as tar:
        for name in [*members,'EVIDENCE_MEMBERS.json']:
            safe(name);tar.add(root/name,arcname=name,recursive=False)
    return dict(members=members,manifest_sha256=sha(root/'EVIDENCE_MEMBERS.json'),
        tar_sha256=sha(root/'evidence.tar'),tar_bytes=(root/'evidence.tar').stat().st_size,
        original_binary_state_preserved=True)


def extract(archive,out,proof,maximum):
    archive=Path(archive);out=Path(out)
    expected={**proof['members'],'EVIDENCE_MEMBERS.json':dict(sha256=proof['manifest_sha256'],bytes=None)}
    if sum(v['bytes'] for v in proof['members'].values())>maximum:raise ValueError('Declared bound exceeded')
    if archive.stat().st_size!=proof['tar_bytes'] or sha(archive)!=proof['tar_sha256']:raise ValueError('Original archive mismatch')
    with tarfile.open(archive,'r:') as tar:
        items=tar.getmembers();names=[m.name for m in items]
        if len(names)!=len(set(names)) or set(names)!=set(expected):raise ValueError('Duplicate/missing/extra member')
        for m in items:
            safe(m.name)
            if not m.isfile() or (expected[m.name]['bytes'] is not None and m.size!=expected[m.name]['bytes']):raise ValueError('Link/size mismatch')
            if m.name=='EVIDENCE_MEMBERS.json' and m.size>20_000_000:raise ValueError('Unexpected manifest size')
        out.mkdir(parents=False,exist_ok=False)
        for m in items:
            p=out/m.name;p.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
            with p.open('xb') as dest,tar.extractfile(m) as src:
                for b in iter(lambda:src.read(2**20),b''):dest.write(b);h.update(b)
            if h.hexdigest()!=expected[m.name]['sha256']:raise ValueError('Partial extraction SHA mismatch')
    if read(out/'EVIDENCE_MEMBERS.json')!=proof['members']:raise ValueError('Manifest mismatch')
    return {'original_bytes_verified':True,'members':len(expected),'model_loads':0}
