"""Source checks and bounded process lifetime shared only by new P010 jobs."""
from pathlib import Path
import os
import threading
import time
from experiments.p010.common import dump,read,sha,manifest,verify,utc


def source_check(spec,base='/workspace'):
    for name,expected in spec['source_files'].items():
        if sha(Path(base)/name)!=expected:raise ValueError('Executed source differs: '+name)


def hard_timer(seconds):
    def expire():
        import psutil
        for child in psutil.Process().children(recursive=True):
            try:child.kill()
            except psutil.Error:pass
        os._exit(124)
    timer=threading.Timer(seconds,expire);timer.daemon=True;timer.start();return timer


def compact(root):
    """JSON/text proof; required binaries remain separately hashed on Volume."""
    import tarfile
    root=Path(root);files=manifest(root)
    members={k:v for k,v in files.items() if not k.endswith(('.pt','.safetensors')) and not k.startswith('merged/')}
    dump(root/'COMPACT_MEMBERS.json',members)
    with tarfile.open(root/'evidence.tar.gz','x:gz') as t:
        for name in members:t.add(root/name,arcname=name,recursive=False)
        t.add(root/'COMPACT_MEMBERS.json',arcname='COMPACT_MEMBERS.json',recursive=False)
    return dict(all_files=files,compact_members=members,tar_sha256=sha(root/'evidence.tar.gz'),tar_bytes=(root/'evidence.tar.gz').stat().st_size)
