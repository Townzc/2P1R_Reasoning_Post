"""CPU packing for immutable run evidence, with checked extraction and no overwrite.

Scientific journals/checkpoints remain unchanged. One bundle avoids thousands
of remote metadata round trips. Terminal binary states are transferred separately.
"""
import gzip
import hashlib
import json
from pathlib import Path,PurePosixPath
import tarfile
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest


def safe_name(name):
    p=PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or str(p)!=name or '\\' in name:
        raise ValueError('Unsafe/noncanonical bundle name')
    return name


def pack(root):
    root=Path(root);excluded={'compact_evidence.tar.gz','compact_manifest.json','bundle_receipt.json','artifact_manifest.json'}
    files={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ValueError('No symlink evidence')
        if not path.is_file():continue
        name=safe_name(path.relative_to(root).as_posix())
        if name in excluded or path.suffix=='.pt':continue
        files[name]=dict(bytes=path.stat().st_size,sha256=sha(path))
    target=root/'compact_evidence.tar.gz'
    # Fixed gzip timestamp and normalized tar metadata make equal contents stable.
    with target.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',compresslevel=3,mtime=0,filename='') as gz,tarfile.open(fileobj=gz,mode='w|',format=tarfile.PAX_FORMAT) as tar:
        for name,record in files.items():
            info=tarfile.TarInfo(name);info.size=record['bytes'];info.mode=0o644;info.mtime=0
            with (root/name).open('rb') as source:tar.addfile(info,source)
    dump(root/'compact_manifest.json',files)
    receipt=dict(file=target.name,sha256=sha(target),bytes=target.stat().st_size,
        content_manifest_sha256=sha(root/'compact_manifest.json'),content_files=len(files),
        uncompressed_bytes=sum(r['bytes'] for r in files.values()),checkpoint_binaries_separate=True)
    dump(root/'bundle_receipt.json',receipt);return receipt


def unpack(bundle,manifest_path,receipt_path,out):
    bundle=Path(bundle);files=read(manifest_path);receipt=read(receipt_path)
    if sha(bundle)!=receipt['sha256'] or bundle.stat().st_size!=receipt['bytes'] or sha(manifest_path)!=receipt['content_manifest_sha256']:
        raise ValueError('Bundle/manifest SHA differs')
    if receipt['content_files']!=len(files) or receipt['uncompressed_bytes']!=sum(r['bytes'] for r in files.values()):
        raise ValueError('Content bound differs')
    for name in files:safe_name(name)
    out=Path(out);out.mkdir(parents=True,exist_ok=False);seen=set()
    with tarfile.open(bundle,'r|gz') as tar:
        for entry in tar:
            name=safe_name(entry.name)
            if not entry.isfile() or name in seen or name not in files or entry.size!=files[name]['bytes']:
                raise ValueError('Nonfile,duplicate,foreign or oversized member')
            source=tar.extractfile(entry);target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
            h=hashlib.sha256();total=0
            with target.open('xb') as f:
                for block in iter(lambda:source.read(2**20),b''):
                    total+=len(block)
                    if total>entry.size:raise ValueError('Member exceeds admitted size')
                    h.update(block);f.write(block)
            if total!=entry.size or h.hexdigest()!=files[name]['sha256']:raise ValueError('Member hash differs')
            seen.add(name)
    if seen!=set(files):raise ValueError('Missing evidence member')
    return dict(files_verified=len(seen),bytes_verified=receipt['uncompressed_bytes'])
