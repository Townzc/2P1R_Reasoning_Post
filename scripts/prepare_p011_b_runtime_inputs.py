"""One-use B input preparation after the shared full-source CR; no model call."""
import argparse
import os
from pathlib import Path
import threading
import time
from experiments.p011 import b_input_path as inputs, b_path, b_student_evidence
from experiments.sft_allocation_midpoint.common import read, dump, sha, manifest, digest

ROOT=Path(__file__).resolve().parents[1]
PACKET=Path('reports/p011_20261020/b_full_path_preflight_v1')
ENDPOINT='.local/p010_20261019/r1/student_inputs_r2/MATH_ENDPOINT.json'
GOLD='.local/p009_20261014/r1/source_assets_r1/math500/test.jsonl'


def prepare_student(root,binding,review):
    root=Path(root);inputs.source_authority(root,binding,review)
    if sha(root/GOLD)!=b_student_evidence.GOLD_SHA256:
        raise ValueError('Original frozen gold differs')
    for name in (ENDPOINT,GOLD):
        if sha(root/name)!=binding['student_endpoint_files'][name]:
            raise ValueError('Original full endpoint source bytes differ')
    generation='B_generation_t10_400x16_r1'
    io=root/inputs.LOCAL/'b_io_r1';score=io/'score'/generation
    proof=read(io/'audit'/generation/'COMPLETE_PROOF.json');done=read(score/'COMPLETED.json')
    rows=read(score/'RECORDS.json');selection=read(score/'SELECTION.json')
    if (proof.get('passed') is not True or proof['endpoint']['technical_unknown']!=0
            or done['read_only_saved_score_proof']['passed'] is not True
            or done['records_sha256']!=digest(rows) or done['selection_sha256']!=digest(selection)):
        raise ValueError('Complete new6400 raw/score evidence required')
    evidence={str(p.relative_to(root)):sha(p) for p in (
        io/'audit'/generation/'COMPLETE_PROOF.json',score/'COMPLETED.json',score/'RECORDS.json',score/'SELECTION.json')}
    binding={**binding,'complete_new_raw_and_score_proof':True,'new_raw_outputs':6400,
        'technical_unknown':0,'records_sha256':digest(rows),'selection_sha256':digest(selection),
        'actual_result_evidence_files':evidence}
    out=root/inputs.LOCAL/'b_runtime_student_inputs_r1'
    fence=root/inputs.LOCAL/'B_RUNTIME_STUDENT_INPUT_ATTEMPT.json'
    if out.exists() or fence.exists():raise ValueError('B runtime input attempt already exists')
    # The original student encoding has its own permanent first-use fence. This
    # enclosing fence also retains any failure after encoding/before byte copies.
    dump(fence,dict(epoch=time.time(),binding=binding,automatic_retry=False));out.mkdir()
    try:
        from transformers import AutoTokenizer
        model=read(root/'reports/p011_20261020/c1_runtime_v1/MODEL_ASSET_BINDING.json')
        assets=root/binding['base_tokenizer_local_path']
        for name in ('tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','config.json'):
            if sha(assets/name)!=model['files'][name]['sha256']:raise ValueError('Original tokenizer source differs')
        tok=AutoTokenizer.from_pretrained(assets,local_files_only=True,trust_remote_code=False,use_fast=True)
        prepared=inputs.student_inputs(root,read(root/inputs.LOCAL/'b_generation_inputs_r1/PACK.json'),rows,selection,tok,binding,review)
        for run in ('B1','B2','B3'):
            dest=out/run;dest.mkdir()
            for name in ('rows.json','encoded.json','plan.json','config.json'):
                (dest/name).write_bytes((prepared/run/name).read_bytes())
            (dest/'MATH_ENDPOINT.json').write_bytes((root/ENDPOINT).read_bytes())
            (dest/'GOLD.jsonl').write_bytes((root/GOLD).read_bytes())
        dump(out/'COMPLETED.json',dict(original_endpoint_byte_copies=True,
            original_P010_encodings_repeated=0,new_generation_calls=0,actual_A1_accepted=False))
        dump(out/'MANIFEST.json',manifest(out))
        return out
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),automatic_retry=False))
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['generation','student']);p.add_argument('--review',required=True)
    args=p.parse_args();binding=read(ROOT/PACKET/'SOURCE_BINDING.json');review=read(args.review)
    inputs.source_authority(ROOT,binding,review)
    # Full local constructor cap only, no paid measurement or model permission.
    seconds=min(3600,b_path.CUTOFF-time.time())
    if seconds<=0:raise TimeoutError('Original cutoff expired')
    timer=threading.Timer(seconds,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        if args.mode=='generation':inputs.generate_inputs(ROOT,binding,review)
        else:prepare_student(ROOT,binding,review)
    finally:timer.cancel()


if __name__=='__main__':main()
