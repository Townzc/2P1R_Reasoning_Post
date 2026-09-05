"""Download a public base checkpoint at the exact recorded revision; no training."""
import argparse
import json
from pathlib import Path
from huggingface_hub import snapshot_download

p = argparse.ArgumentParser()
p.add_argument('--role', choices=['debug', 'main', 'second'], default='debug')
p.add_argument('--lock', default='configs/models.lock.json')
a = p.parse_args()
model = json.loads(Path(a.lock).read_text())[a.role]
path = snapshot_download(model['repo_id'], revision=model['revision'], max_workers=2,
                         allow_patterns=['*.json', '*.safetensors', '*.txt', '*.model', 'LICENSE', 'README.md'])
print(json.dumps({'repo_id': model['repo_id'], 'revision': model['revision'], 'cache_snapshot': path}))
