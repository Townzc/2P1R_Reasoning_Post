"""Record package versions and hardware without hostnames, credentials or paths."""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import subprocess
import torch

p=argparse.ArgumentParser()
p.add_argument('--out',required=True)
a=p.parse_args()
names={d.metadata['Name'] for d in metadata.distributions()}
report={'python':platform.python_version(),'os':platform.platform(),'torch':torch.__version__,
 'cuda_runtime':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),
 'gpu_total_mib':torch.cuda.get_device_properties(0).total_memory/1024**2,
 'bf16_supported':torch.cuda.is_bf16_supported(),
 'driver':subprocess.check_output(['nvidia-smi','--query-gpu=driver_version','--format=csv,noheader'],text=True).strip(),
 'environment':'venv --system-site-packages overlay; image PyTorch reused',
 'packages':{name:metadata.version(name) for name in sorted(names,key=str.lower)}}
with Path(a.out).open('x') as f: json.dump(report,f,indent=2); f.write('\n')
