"""Once-only A/D runtime input consumer after shared full-path source CR.

Reuses accepted training encodings/plans. First native endpoint prompt encoding
only; no model, new filtering, answer encoding or production training occurs.
"""
import argparse
import os
from pathlib import Path
import threading
import time
from experiments.p011 import c1_admission as shared,long_training,long_evaluation,long_execution
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest,verify

ROOT=Path(__file__).resolve().parents[1]
R=Path('.local/p011_20261020/r1')
OUT=R/'long_inputs_r1'
P=Path('reports/p011_20261020/long_full_path_preflight_v1')


def source_review(binding,accepted):
    shared.fixed_report(accepted)
    if (accepted.get('scope')!='p011-long-A-D-complete-path-CR'
            or accepted.get('source_files')!=binding['source_files']
            or accepted.get('input_basis_files')!=binding['input_basis_files']
            or accepted.get('input_preparation_authorized') is not True):
        raise ValueError('Exact full-path source CR required before any input use')
    shared.exact_source(binding,ROOT)
    for n,s in binding['input_basis_files'].items():
        if sha(ROOT/n)!=s:raise ValueError('Original input basis/acceptance changed')


def consume(source,out,benchmarks,requests):
    """No resampling/re-encoding: select original dictionaries by frozen path IDs."""
    source=Path(source);inventory=read(source/'MANIFEST.json')['files']
    needed=['ENCODED.jsonl','BENCHMARKS.json',*[p.name for p in source.glob('*_PLAN.json')]]
    verify(source,{n:inventory[n] for n in needed})
    if read(source/'BENCHMARKS.json')!=benchmarks:raise ValueError('Same original benchmark roster required')
    import json
    rows={}
    with (source/'ENCODED.jsonl').open() as f:
        for line in f:
            row=json.loads(line)
            if row['path_id'] in rows:raise ValueError('Duplicate saved path')
            rows[row['path_id']]=row
    proofs={}
    for path in sorted(source.glob('*_PLAN.json')):
        cell=path.name.removesuffix('_PLAN.json');plan=read(path);dest=out/cell
        dest.mkdir(exist_ok=False);encoded=[rows[n] for n in plan['row_path_ids']]
        # The whole original plan file is byte-copied. Encoded dictionaries are
        # losslessly selected/re-serialized; this is not a second encoding.
        (dest/'plan.json').write_bytes(path.read_bytes());dump(dest/'encoded.json',encoded)
        for arm in long_training.ARMS:
            rates=long_training.learning_rates(plan['optimizer_updates'],arm)
            proof=long_training.validate_plan(encoded,plan,rates,arm)
            dump(dest/('rates_'+arm+'.json'),rates);proofs[cell+'/'+arm]=proof
        write_endpoint(dest,requests)
        dump(dest/'ORIGINAL_ROWS.json',{'source_encoded_sha256':inventory['ENCODED.jsonl']['sha256'],
            'plan_file_sha256':sha(path),'ordered_path_ids':plan['row_path_ids'],
            'original_row_values_sha256':digest(encoded),'training_tokenizations':0})
    return proofs


def write_endpoint(dest,requests):
    dump(dest/'ENDPOINT_LOCAL.json',requests)
    gpu=[{**{k:v for k,v in row.items() if k!='gold'},'request_sha256':digest(row)} for row in requests]
    long_execution.validate_endpoint(gpu,max(r['required_context'] for r in requests))
    dump(dest/'ENDPOINT_GPU.json',gpu)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--review',required=True);args=parser.parse_args()
    binding=read(ROOT/P/'SOURCE_BINDING.json');review=read(args.review);source_review(binding,review)
    if time.time()+3600>=1792645200:raise TimeoutError('Original deadline lacks full construction window')
    dump(ROOT/R/'LONG_RUNTIME_INPUT_ATTEMPT.json',{'source_files':binding['source_files'],'review':shared.fixed_report(review),'automatic_retry':False,'started_epoch':time.time()})
    out=ROOT/OUT;out.mkdir(exist_ok=False)
    timer=threading.Timer(3600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        config=read(ROOT/P/'INPUT_CONSUMER_BINDING.json');tokroot=ROOT/config['tokenizer_local_path'];verify(tokroot,config['tokenizer_files'])
        from transformers import AutoTokenizer
        tok=AutoTokenizer.from_pretrained(tokroot,local_files_only=True,trust_remote_code=False,use_fast=True)
        if tok.eos_token_id!=151645:raise ValueError('Pinned native EOS required')
        benchmarks=read(ROOT/R/'ot3_inputs_nfc_r1/BENCHMARKS.json')
        requests=long_evaluation.request_roster(benchmarks,tok)
        proofs={}
        for source in ('ot3_inputs_nfc_r1','am_inputs_r1'):
            proofs.update(consume(ROOT/R/source,out,benchmarks,requests))
        baseline=out/'baseline';baseline.mkdir();write_endpoint(baseline,requests)
        dump(out/'COMPLETED.json',dict(source_files=binding['source_files'],proofs=proofs,
            endpoint_count=len(requests),max_context=max(r['required_context'] for r in requests),
            endpoint_input_ids_sha256=digest(requests),model_calls=0,training_tokenizations=0,
            endpoint_prompt_tokenizations=600,actual_runtime_A1_accepted=False,completed_epoch=time.time()))
        dump(out/'MANIFEST.json',manifest(out))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,message=str(exc),automatic_retry=False));raise
    finally:timer.cancel()

if __name__=='__main__':main()
