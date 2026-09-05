"""Safely synchronize a published Git bundle after pulling run artifacts home.

Refuses local edits, active/reserved jobs, and unequal untracked files that the
new commit would overwrite. Run only after local publication is verified.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess

p=argparse.ArgumentParser()
p.add_argument('--bundle',required=True)
p.add_argument('--commit',required=True)
a=p.parse_args()
if len(a.commit)!=40 or any(c not in '0123456789abcdef' for c in a.commit):
    p.error('Exact expected published commit required')
def git(*args,**kw): return subprocess.check_output(['git',*args],**kw)
Path('.local').mkdir(exist_ok=True)
with Path('.local/resource_ledger.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    ledger=Path('.local/resource_ledger.json')
    if ledger.exists() and any(j['status']=='reserved' for j in json.loads(ledger.read_text())['jobs']):
        raise RuntimeError('Reconcile unresolved run before synchronizing')
    if git('status','--porcelain','--untracked-files=no').strip():
        raise RuntimeError('Tracked local changes must be reviewed first')
    git('fetch',str(Path(a.bundle).resolve()),'main')
    if git('rev-parse','FETCH_HEAD',text=True).strip()!=a.commit:
        raise RuntimeError('Bundle main differs from expected published commit')
    subprocess.run(['git','merge-base','--is-ancestor','HEAD',a.commit],check=True)
    tracked=set(git('ls-files','-z').decode().split('\0'))
    tracked.discard('')
    incoming=git('ls-tree','-rz',a.commit).split(b'\0')
    incoming_names=set()
    for entry in incoming:
        if not entry: continue
        meta,name=entry.split(b'\t',1)
        mode,kind,sha=meta.decode().split()
        name=name.decode()
        incoming_names.add(name)
        path=Path(name)
        if name in tracked or not (path.exists() or path.is_symlink()): continue
        if mode!='100644' or kind!='blob' or not path.is_file() or path.is_symlink():
            raise RuntimeError(f'Unsupported existing incoming path: {name}')
        digest=hashlib.sha1(f'blob {path.stat().st_size}\0'.encode()+path.read_bytes()).hexdigest()
        if digest!=sha: raise RuntimeError(f'Untracked file differs from published blob: {name}')
    removed=tracked-incoming_names
    if any(Path(name).is_dir() and not Path(name).is_symlink() for name in removed):
        raise RuntimeError('Directory/submodule deletion needs explicit handling')
    # Every overwritten existing file is either clean tracked content or has
    # just been checked identical to the published incoming blob.
    git('reset','--mixed',a.commit)
    for name in removed:
        Path(name).unlink(missing_ok=True)  # Previously tracked and verified clean.
    git('restore','--source=HEAD','--worktree','.')
    git('diff','--exit-code')
    print(json.dumps({'synchronized_commit':a.commit,'existing_artifacts_verified':True}))
