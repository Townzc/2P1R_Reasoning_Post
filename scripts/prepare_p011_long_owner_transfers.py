"""Transfer only previously unuploaded cells; bind prior successful byte receipts."""
import concurrent.futures
from pathlib import Path
import time
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from experiments.p011 import long_owner_path as path
from scripts.p011_long_current_io import transfer,reused_assets
ROOT=Path(__file__).resolve().parents[1]

def prepare(name,spec,volume):
    job=spec['jobs'][name];out=ROOT/path.LOCAL/'long_io_r1/upload'/name
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'ATTEMPT.json',dict(job_sha256=digest(job),started_epoch=time.time(),new_encoding=False))
    try:
        prior={'A7':'long_A7_S-F15_s17_r1','baseline':'long_baseline_S-L15_s17_r1',
               'D1':'long_D1_S-F15_s17_r1','D2':'long_D2_S-F15_s17_r1'}.get(job['cell'])
        asset=reused_assets(ROOT,job)
        if prior:
            old=ROOT/path.LOCAL/'long_io_r1/upload'/prior
            receipt=read(old/'COMPLETED.json')
            if receipt.get('all_remote_file_bytes_read_back') is not True:raise ValueError('Prior upload incomplete')
            for n,want in job['input_files'].items():
                got=read(old/'inputs'/(n+'.json'))
                if any(got[k]!=v for k,v in want.items()):raise ValueError('Prior original input bytes differ')
            proof=dict(original_completed_file=str((old/'COMPLETED.json').relative_to(ROOT)),original_completed_sha256=sha(old/'COMPLETED.json'),
                input_files=job['input_files'],old_remote_bytes_reread=False,old_bytes_uploaded=False)
            dump(out/'PRIOR_INPUT_REUSE.json',proof)
        else:
            source=ROOT/path.LOCAL/path.LOCAL_INPUT_DIRECTORY/job['input_directory']
            transfer(volume,source,path.INPUTS.removeprefix('/evidence')+'/'+job['input_directory'],job['input_files'],out/'inputs')
        dump(out/'COMPLETED.json',dict(job_sha256=digest(job),all_remote_file_bytes_read_back=True,
            asset_readback_file_sha256=asset,completed_epoch=time.time(),model_calls=0,
            prior_input_receipt_reused=prior,original_input_bytes_unchanged=True))
        return name
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,message=str(exc),partial_retained=True));raise

def main():
    import modal
    spec=path.validate(read(ROOT/path.SPEC));path.published(ROOT,spec)
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for name in pool.map(lambda n:prepare(n,spec,volume),spec['initial_jobs']):print('INPUT_READY',name,flush=True)

if __name__=='__main__':main()
