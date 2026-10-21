"""Once-only original-byte subset construction, only after exact input/source CR."""
from pathlib import Path
import argparse,os,threading,time
from experiments.p011 import c1_admission as shared
from experiments.p011.long_preflight import subset
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest
ROOT=Path(__file__).resolve().parents[1]
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020/long_preflight_source_v1')
SOURCE=R/'long_inputs_numeric_gold_r1';OUT=R/'long_preflight_inputs_r1'
SCOPE='p011-long-three-arm-engineering-preflight-source-CR'


def build(root,binding,review):
    root=Path(root);shared.fixed_report(review);shared.exact_source(binding,root)
    expected={'scope':SCOPE,'source_files':binding['source_files'],
              'input_basis_files':binding['input_basis_files'],'owner_decision_sha256':subset.OWNER_SHA,
              'input_preparation_authorized':True,'original_completed_long_inputs_accepted':True,
              'engineering_subset_only':True}
    if any(review.get(k)!=v for k,v in expected.items()):raise ValueError('Exact engineering subset source/input permission required')
    for n,v in binding['input_basis_files'].items():
        if sha(root/n)!=v:raise ValueError('Original completed input basis changed')
    if not (root/SOURCE/'COMPLETED.json').is_file() or (root/SOURCE/'FAILED.json').exists():raise ValueError('Original completed new input required')
    out=root/OUT
    if out.exists() or time.time()+3600>=1792645200:raise ValueError('Original subset already attempted or window unavailable')
    dump(root/R/'LONG_PREFLIGHT_INPUT_ATTEMPT.json',{'started_epoch':time.time(),
        'review':shared.fixed_report(review),'binding':binding,'automatic_retry':False})
    out.mkdir();timer=threading.Timer(3600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        encoded=read(root/SOURCE/'A8/encoded.json')
        gpu=read(root/SOURCE/'baseline/ENDPOINT_GPU.json');local=read(root/SOURCE/'baseline/ENDPOINT_LOCAL.json')
        by_id={r['id']:r for r in local}
        if len(by_id)!=3300 or len(gpu)!=3300:raise ValueError('All original3300 local/gpu endpoints required')
        context=max(r['required_context'] for r in gpu);proofs={}
        for arm in subset.full.ARMS:
            rows,plan,rates,requests,proof=subset.select(encoded,gpu,context,arm)
            chosen=[by_id[r['id']] for r in requests]
            if any(r['request_sha256']!=digest(o) for r,o in zip(requests,chosen)):raise ValueError('Original gold-free projection differs')
            job=out/arm;job.mkdir()
            for n,v in [('encoded.json',rows),('plan.json',plan),('rates_'+arm+'.json',rates),
                        ('ENDPOINT_GPU.json',requests),('ENDPOINT_LOCAL.json',chosen),('SUBSET_PROOF.json',proof)]:dump(job/n,v)
            proofs[arm]={'local_input_files':manifest(job),'context':context,'B':plan['supervised_tokens'],'U':2,'endpoint_count':32,'input_plan_sha256':digest(plan)}
        dump(out/'COMPLETED.json',{'proofs':proofs,'owner_decision_sha256':subset.OWNER_SHA,
            'tokenizations':0,'model_calls':0,'scientific_cell_results':0,'source_files':binding['source_files'],
            'input_basis_files':binding['input_basis_files'],'completed_epoch':time.time(),'actual_A1_accepted':False})
        dump(out/'MANIFEST.json',manifest(out));return out
    except BaseException as e:
        dump(out/'FAILED.json',{'type':type(e).__name__,'message':str(e),'automatic_retry':False});raise
    finally:timer.cancel()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review',required=True);a=p.parse_args()
    build(ROOT,read(ROOT/P/'SOURCE_BINDING.json'),read(a.review))

if __name__=='__main__':main()
