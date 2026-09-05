#!/usr/bin/env bash
set -euo pipefail
# The first run reuses an image with torch 2.8.0+cu128 / Python 3.12.
# Set BASE_PYTHON and RUNTIME_ROOT for a new server; no host details are in Git.
: "${BASE_PYTHON:=python3}"
: "${RUNTIME_ROOT:=$PWD/.local/runtime}"
"$BASE_PYTHON" -c 'import sys,torch; assert sys.version_info[:2]==(3,12); assert torch.__version__=="2.8.0+cu128"; assert torch.cuda.is_available()'
"$BASE_PYTHON" -m venv --system-site-packages "$RUNTIME_ROOT/train"
"$RUNTIME_ROOT/train/bin/python" -m pip install --index-url https://pypi.org/simple -r requirements.txt
"$RUNTIME_ROOT/train/bin/python" -m pip check
"$RUNTIME_ROOT/train/bin/python" -m unittest discover -s tests -v
printf 'Runtime ready. Set HF_HOME on a persistent data disk before downloading models.\n'
