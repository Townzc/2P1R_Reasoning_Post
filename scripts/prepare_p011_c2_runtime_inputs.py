"""One original-output C2 input projection after exact full-path source review."""
import argparse
import os
from pathlib import Path
import threading
import time
from experiments.p011 import c2_input_path as inputs
from experiments.sft_allocation_midpoint.common import read
ROOT=Path(__file__).resolve().parents[1]
BINDING='reports/p011_20261020/c2_full_path_preflight_v1/SOURCE_BINDING.json'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review',required=True);args=p.parse_args()
    binding=read(ROOT/BINDING);review=read(args.review)
    inputs.authority(ROOT,binding,review)
    seconds=min(3600,inputs.CUTOFF-time.time())
    if seconds<=0:raise TimeoutError('Original P011 cutoff')
    timer=threading.Timer(seconds,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:inputs.prepare(ROOT,binding,review)
    finally:timer.cancel()


if __name__=='__main__':main()
