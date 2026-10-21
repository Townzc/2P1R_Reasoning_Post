"""Proposed one independent replacement for the failed CPU input preparation.

Requires new explicit owner no-retry exception plus exact new CR. Old attempt,
failed directory, logs and original data stay immutable. No existing input or
model output is re-created. Original530 ephemeral prompts were never saved;
this proposed new encoding must not be described as their byte reuse.
"""
import argparse,os,threading,time
from pathlib import Path
from experiments.p011 import c1_admission as shared,long_evaluation,long_gold_input
from scripts.prepare_p011_long_runtime_inputs import consume,write_endpoint
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest,verify
ROOT=Path(__file__).resolve().parents[1]
R=Path('.local/p011_20261020/r1')
P=Path('reports/p011_20261020/long_runtime_repair_v1')
OUT=R/'long_inputs_numeric_gold_r1'
SCOPE='p011-long-numeric-gold-input-replacement-CR'
OWNER_REQUEST='p011-long-numeric-gold-input-replacement-owner-r1'


def admission(binding,review,owner,owner_path):
    shared.fixed_report(review)
    expected={'scope':SCOPE,'source_files':binding['source_files'],
        'input_basis_files':binding['input_basis_files'],
        'owner_decision_sha256':sha(owner_path),'input_preparation_authorized':True,
        'original_failed_attempt_retained':True,'numeric_gold_semantics_unchanged':True,
        'old530_prompts_not_saved_no_false_reuse_claim':True,'one_new_cpu_attempt_only':True}
    if any(review.get(k)!=v for k,v in expected.items()):raise ValueError('Exact new input-only CR required')
    if (owner.get('request_id')!=OWNER_REQUEST or owner.get('decision')!='APPROVED'
            or owner.get('proposal_sha256')!=binding['owner_proposal_sha256']
            or owner.get('original_failure_sha256')!=binding['original_failure_sha256']
            or owner.get('requires_exact_CR') is not True or owner.get('paid_calls_authorized')!=0
            or not owner.get('actual_reply') or not owner.get('observed_utc')):
        raise ValueError('New explicit original-failure exception required')
    shared.exact_source(binding,ROOT)
    for name,value in binding['input_basis_files'].items():
        if sha(ROOT/name)!=value:raise ValueError('Original input/failure evidence changed')


def claim(root,binding,review,owner_path):
    root=Path(root)
    if not (root/R/'LONG_RUNTIME_INPUT_ATTEMPT.json').exists() or not (root/R/'long_inputs_r1/FAILED.json').exists():
        raise ValueError('Original failed parent missing')
    if (root/OUT).exists():raise ValueError('New replacement output already exists; never retry')
    dump(root/R/'LONG_NUMERIC_GOLD_INPUT_ATTEMPT.json',{'started_epoch':time.time(),
        'source_files':binding['source_files'],'review':shared.fixed_report(review),
        'owner_file_sha256':sha(owner_path),'automatic_retry':False})
    out=root/OUT;out.mkdir();return out


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--review',required=True);ap.add_argument('--owner',required=True);args=ap.parse_args()
    binding=read(ROOT/P/'SOURCE_BINDING.json');review=read(args.review);owner=read(args.owner)
    admission(binding,review,owner,args.owner)
    if time.time()+3600>=1792645200:raise TimeoutError('Original full input window unavailable')
    out=claim(ROOT,binding,review,args.owner)
    timer=threading.Timer(3600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        original=read(ROOT/R/'ot3_inputs_nfc_r1/BENCHMARKS.json')
        normalized,projection=long_gold_input.benchmark_projection(original)
        dump(out/'ORIGINAL_GOLD_PROJECTION.json',projection)
        cfg=read(ROOT/'reports/p011_20261020/long_full_path_preflight_v1/INPUT_CONSUMER_BINDING.json')
        tokroot=ROOT/cfg['tokenizer_local_path'];verify(tokroot,cfg['tokenizer_files'])
        from transformers import AutoTokenizer
        tok=AutoTokenizer.from_pretrained(tokroot,local_files_only=True,trust_remote_code=False,use_fast=True)
        if tok.eos_token_id!=151645:raise ValueError('Original native EOS required')
        requests=long_evaluation.request_roster(normalized,tok)
        dump(out/'ENDPOINT_ROSTER.json',requests)
        proofs={}
        for source in ('ot3_inputs_nfc_r1','am_inputs_r1'):
            proofs.update(consume(ROOT/R/source,out,original,requests))
        baseline=out/'baseline';baseline.mkdir();write_endpoint(baseline,requests)
        dump(out/'COMPLETED.json',{'source_files':binding['source_files'],'proofs':proofs,
            'endpoint_count':len(requests),'max_context':max(r['required_context'] for r in requests),
            'endpoint_input_ids_sha256':digest(requests),'gold_projection_sha256':sha(out/'ORIGINAL_GOLD_PROJECTION.json'),
            'model_calls':0,'training_tokenizations':0,'endpoint_prompt_tokenizations':600,
            'old530_ephemeral_prompts_reused':False,'actual_runtime_A1_accepted':False,'completed_epoch':time.time()})
        dump(out/'MANIFEST.json',manifest(out))
    except BaseException as e:
        dump(out/'FAILED.json',{'type':type(e).__name__,'message':str(e),'automatic_retry':False});raise
    finally:timer.cancel()

if __name__=='__main__':main()
