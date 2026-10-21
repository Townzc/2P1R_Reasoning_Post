"""New A/D terminal-state writer using mmap; original checkpoint module unchanged."""
from pathlib import Path
import os
from experiments.sft_allocation_midpoint import checkpoint
from experiments.sft_allocation_midpoint.common import dump,sha,digest


def save(root, state, commit=lambda: None):
    import torch
    path=Path(root)/f"checkpoint_{state['step']:04d}"
    path.mkdir(parents=True,exist_ok=False)
    file=path/'state.pt'
    with file.open('xb') as f:
        torch.save(state,f);f.flush();os.fsync(f.fileno())
    # This is an OS-backed mapping, not a second deserialized tensor copy.
    # same() compares one tensor at a time with torch.equal, with no clone.
    restored=torch.load(file,map_location='cpu',weights_only=True,mmap=True)
    if not checkpoint.same(state,restored):
        raise ValueError('Full serialization changed training state')
    del restored
    record=dict(schema=state['schema'],file='state.pt',bytes=file.stat().st_size,
        sha256=sha(file),identity_sha256=digest(state['identity']),step=state['step'],
        supervised_tokens=state['supervised_tokens'],processed_tokens=state['processed_tokens'])
    dump(path/'manifest.json',record);commit();return record
