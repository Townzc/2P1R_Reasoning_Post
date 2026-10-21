"""One new common-support input construction after complete shared C2 source CR."""
import argparse
import json
import os
from pathlib import Path
import threading
import time
from experiments.p011 import c2_input_path as inputs,c2_student_inputs as build,c2_path
from experiments.p011.c2_student_evidence import GOLD_SHA256
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest
ROOT=Path(__file__).resolve().parents[1]
PACKET=Path('reports/p011_20261020/c2_full_path_preflight_v1')
ENDPOINT='.local/p010_20261019/r1/student_inputs_r2/MATH_ENDPOINT.json'
GOLD='.local/p009_20261014/r1/source_assets_r1/math500/test.jsonl'
PAIRS={
 't15_s1':'.local/p011_20261020/r1/c1_inputs_r1/t15_n3200',
 't72_s1':'.local/p011_20261020/r1/c1_inputs_r1/t72_n3200',
 't72_e1d':'.local/p010_20261019/r1/t72_datasets_r1/e1d_n3200_k1',
 't15_k4':'.local/p010_20261019/r1/t15_datasets_r1/n400_k4',
 't15_k8':'.local/p010_20261019/r1/t15_datasets_r1/n400_k8',
 't72_k4':'.local/p010_20261019/r1/t72_datasets_r1/n400_k4',
 't72_k8':'.local/p010_20261019/r1/t72_datasets_r1/n400_k8',
}


def prepare(root,binding,review):
    root=Path(root);inputs.authority(root,binding,review)
    expected={folder+'/'+name+'.json' for folder in PAIRS.values() for name in ('rows','encoded')}
    if (set(binding['original_encoded_pair_files'])!=expected
            or review.get('original_encoded_pair_files')!=binding['original_encoded_pair_files']
            or review.get('old_selected_encoding_reuse_accepted') is not True
            or review.get('student_endpoint_files')!=binding['student_endpoint_files']
            or set(binding['student_endpoint_files'])!={ENDPOINT,GOLD}):
        raise ValueError('Exact original encoded reuse and endpoint source CR required')
    for table in ('original_encoded_pair_files','student_endpoint_files','tokenizer_files'):
        for name,value in binding[table].items():
            p=Path(name)
            if p.is_absolute() or '..' in p.parts or sha(root/p)!=value:
                raise ValueError('Original encoded or endpoint/tokenizer source differs')
    if sha(root/GOLD)!=GOLD_SHA256:raise ValueError('Original frozen500 gold required')
    generation=root/inputs.LOCAL/'c2_generation_inputs_r1';pack=read(generation/'PACK.json')
    read(generation/'COMPLETED.json');left=dict(pack['t15_records']);evidence={}
    if pack['plan']['new_requests']:
        job='C2_generation_t08_missing_r1';io=root/inputs.LOCAL/'c2_io_r1'
        audit=io/'audit'/job/'COMPLETE_PROOF.json';folder=io/'score'/job
        proof=read(audit);done=read(folder/'COMPLETED.json');new=read(folder/'RECORDS.json')
        if (proof.get('passed') is not True or proof['endpoint']['technical_unknown']!=0
                or proof['endpoint']['outputs']!=len(pack['plan']['new_requests'])
                or done['read_only_saved_score_proof']['passed'] is not True
                or done['records_sha256']!=digest(new)
                or set(new)!={r['request']['candidate_id'] for r in pack['plan']['new_requests']}
                or set(new)&set(left)):
            raise ValueError('Complete new-only raw/saved Boolean evidence required')
        specfile=root/c2_path.SPEC_FILES['generation'];spec=c2_path.validate(read(specfile))
        if (proof['source_files']!=spec['source_files']
                or proof['job_sha256']!=digest(spec['jobs'][job])):
            raise ValueError('Actual complete generation source/job differs')
        left.update(new)
        evidence={str(p.relative_to(root)):sha(p) for p in (audit,folder/'COMPLETED.json',folder/'RECORDS.json')}
    source=read(root/inputs.FILES['source']);source={r['problem_id']:r for r in source}
    selection,rows=build.selected_rows(pack['ordered_e1d'],pack['t72_records'],left,pack['s1_ids'],source)
    out=root/inputs.LOCAL/'c2_student_inputs_r1';runtime=root/inputs.LOCAL/'c2_runtime_student_inputs_r1'
    fence=root/inputs.LOCAL/'C2_STUDENT_INPUT_ATTEMPT.json'
    if any(p.exists() for p in (out,runtime,fence)):raise ValueError('C2 input attempt exists; no repeat')
    exact={**binding,'complete_original_and_new_saved_verdicts':True,
        'selection_sha256':digest(selection),'actual_new_result_evidence_files':evidence,
        'generation_input_manifest_sha256':sha(generation/'MANIFEST.json')}
    dump(fence,dict(epoch=time.time(),binding=exact,review_sha256=digest(review),automatic_retry=False))
    try:
        pairs=[(name,read(root/folder/'rows.json'),read(root/folder/'encoded.json')) for name,folder in PAIRS.items()]
        catalog,provenance=build.original_catalog(pairs)
        from transformers import AutoTokenizer
        tok=AutoTokenizer.from_pretrained(root/binding['base_tokenizer_local_path'],local_files_only=True,trust_remote_code=False,use_fast=True)
        def check():
            if time.time()>=inputs.CUTOFF:raise TimeoutError('Original P011 cutoff')
        prepared=build.construct(out,rows,selection,catalog,provenance,tok,exact,check)
        runtime.mkdir()
        for run in ('C2a','C2b'):
            dest=runtime/run;dest.mkdir()
            for name in ('rows.json','encoded.json','plan.json','config.json'):
                (dest/name).write_bytes((prepared/run/name).read_bytes())
            (dest/'MATH_ENDPOINT.json').write_bytes((root/ENDPOINT).read_bytes())
            (dest/'GOLD.jsonl').write_bytes((root/GOLD).read_bytes())
        dump(runtime/'COMPLETED.json',dict(original_endpoint_byte_copies=True,
            actual_A1_accepted=False,new_model_calls=0,original_scores_repeated=0))
        dump(runtime/'MANIFEST.json',manifest(runtime));return runtime
    except BaseException as exc:
        dump(root/inputs.LOCAL/'C2_STUDENT_INPUT_FAILED.json',dict(type=type(exc).__name__,
            error=str(exc),partial_retained=True,automatic_retry=False));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review',required=True);args=p.parse_args()
    binding=read(ROOT/PACKET/'SOURCE_BINDING.json');review=read(args.review)
    seconds=min(3600,inputs.CUTOFF-time.time())
    if seconds<=0:raise TimeoutError('Original cutoff')
    timer=threading.Timer(seconds,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:prepare(ROOT,binding,review)
    finally:timer.cancel()

if __name__=='__main__':main()
