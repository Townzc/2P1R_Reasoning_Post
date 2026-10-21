"""First transfer for one unused optional cell; no original transfer repeats."""
import argparse
from pathlib import Path
from experiments.p011 import long_owner_optional_path as path
from experiments.sft_allocation_midpoint.common import read
from scripts.prepare_p011_long_owner_transfers import prepare
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--job',required=True);a=p.parse_args()
    spec=path.validate(read(ROOT/path.SPEC));path.published(ROOT,spec)
    if spec['jobs'][a.job]['cell'] not in ('A4','A3','A2','A8'):raise ValueError('Only previously unuploaded optional cells')
    import modal
    print(prepare(a.job,spec,modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)))
if __name__=='__main__':main()
