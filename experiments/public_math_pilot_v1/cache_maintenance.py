"""Release clean page cache for this phase's committed checkpoint files only.

POSIX_FADV_DONTNEED changes cache residency, never file contents or scientific
state. This separate CPU process leaves the frozen trainer and its RAM gate intact.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

PHASE='public_math_pilot_v1'
ARMS=('SFT','DFT','TrimSFT','QDW_v0')
SLOT=re.compile(r'slot_[0-9]{6}_[0-9a-f]{32}\Z')
GIB=2**30


def read(path):return json.loads(Path(path).read_text())


def component_paths(output,volume):
    """Follow committed ancestry; reject unowned or symlinked component paths."""
    output=Path(output);volume=Path(volume).resolve();seen=set();paths=[]
    for arm in ARMS:
        control=output/'checkpoints'/arm
        pointer=control/'latest.json'
        if not pointer.exists():continue
        latest=read(pointer);checkpoint_id=latest['checkpoint_id'];first=True;chain=set()
        owner=read(control/'checkpoint_owner.json')
        if owner.get('phase')!=PHASE or owner.get('arm')!=arm:
            raise ValueError('Foreign control owner')
        if read(volume/PHASE/arm/'checkpoint_owner.json')!=owner:
            raise ValueError('Foreign storage owner')
        while checkpoint_id:
            if not SLOT.fullmatch(checkpoint_id) or checkpoint_id in chain:
                raise ValueError('Invalid checkpoint ancestry')
            chain.add(checkpoint_id)
            manifest_path=control/'commits'/(checkpoint_id+'.json')
            raw=manifest_path.read_bytes();manifest=json.loads(raw)
            if (manifest_path.is_symlink() or manifest['identity']!=owner
                    or manifest['checkpoint_id']!=checkpoint_id
                    or (first and hashlib.sha256(raw).hexdigest()!=latest['manifest_sha256'])):
                raise ValueError('Committed manifest identity differs')
            first=False
            for record in manifest['files'].values():
                relative=Path(record['path']);parts=relative.parts
                if (record['volume']!=0 or relative.is_absolute() or len(parts)!=5
                        or parts[:3]!=(PHASE,arm,'slots') or parts[3]!=checkpoint_id
                        or parts[4] not in ('model.pt','training.pt')):
                    raise ValueError('Component outside owned checkpoint scope')
                path=volume
                for part in parts:
                    path/=part
                    if path.is_symlink():raise ValueError('Symlinked checkpoint path')
                if path in seen or not path.exists():continue
                seen.add(path)
                if path.stat().st_size!=record['bytes']:
                    raise ValueError('Committed component size differs')
                paths.append((path,record['bytes']))
            checkpoint_id=manifest['metadata']['parent_checkpoint_id']
    return paths


def evict_clean_cache(output,volume,advise=None):
    if advise is None:
        advise=lambda fd:os.posix_fadvise(fd,0,0,os.POSIX_FADV_DONTNEED)
    files=0;count=0
    for path,size in component_paths(output,volume):
        try:fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
        except FileNotFoundError:continue  # A verified superseded file was pruned.
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size!=size:
                raise ValueError('Committed component changed during cache advice')
            advise(fd);files+=1;count+=size
        finally:os.close(fd)
    return dict(advised_files=files,advised_file_bytes=count,files_deleted=0,files_modified=0)


def memory_snapshot():
    root=Path('/sys/fs/cgroup');limit=(root/'memory.max').read_text().strip()
    if limit=='max':raise ValueError('Expected finite cgroup memory limit')
    used=int((root/'memory.current').read_text())
    stats=dict(line.split() for line in (root/'memory.stat').read_text().splitlines())
    return dict(limit_bytes=int(limit),current_bytes=used,headroom_bytes=int(limit)-used,
        file_cache_bytes=int(stats['file']),anonymous_bytes=int(stats['anon']),
        dirty_bytes=int(stats['file_dirty']),writeback_bytes=int(stats['file_writeback']))


def run(args):
    if not hasattr(os,'posix_fadvise'):raise RuntimeError('POSIX file-cache advice unavailable')
    with Path(args.journal).open('x',buffering=1) as journal:
        while time.time()<args.deadline_unix:
            before=memory_snapshot()
            if before['headroom_bytes']<72*GIB and before['file_cache_bytes']>8*GIB:
                change=evict_clean_cache(args.output,args.volume_root)
                event=dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),before=before,
                    after=memory_snapshot(),**change)
                journal.write(json.dumps(event,sort_keys=True)+'\n');os.fsync(journal.fileno())
                print(json.dumps(event,sort_keys=True),flush=True)
            if (Path(args.output)/'TRAINING_COMPLETE.json').exists():return
            time.sleep(5)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('output','volume-root','journal'):p.add_argument('--'+name,required=True)
    p.add_argument('--deadline-unix',type=float,required=True)
    run(p.parse_args())
