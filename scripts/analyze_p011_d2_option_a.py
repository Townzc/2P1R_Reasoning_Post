"""First D2-minus-D1 MATH-only paired contrasts under direct option(a)."""
import time
from pathlib import Path
from experiments.p011 import long_owner_path as path,long_d2_scope as scope,long_evaluation
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from scripts.p011_d2_option_a_io import bound_source
ROOT=Path(__file__).resolve().parents[1]


def main():
    spec,binding=bound_source(ROOT)
    d1='long_D1_S-F15_s17_owner_r1';original=ROOT/path.LOCAL/'long_owner_closeout_r1'
    leftfile=original/'score'/d1/'COMPLETED.json';rightfile=ROOT/scope.LOCAL/'score/COMPLETED.json'
    lp=read(original/'audit'/d1/'COMPLETE_PROOF.json');rp=read(ROOT/scope.LOCAL/'audit/COMPLETE_PROOF.json')
    left,right=[read(f)['read_only_saved_score_proof'] for f in (leftfile,rightfile)]
    if (not all(v['passed'] is True for v in (lp,rp,left,right))
            or lp['job_sha256']!=digest(spec['jobs'][d1]) or rp['job_sha256']!=digest(spec['jobs'][scope.JOB])
            or rp['source_binding_sha256']!=sha(ROOT/scope.PACKET/'SOURCE_BINDING.json')
            or left['outputs']!=3300 or right['outputs']!=2980):
        raise ValueError('Both exact saved original score/oracle scopes required')
    if time.time()+60>=path.CUTOFF:raise TimeoutError('Owner05UTC analysis deadline')
    out=ROOT/scope.LOCAL/'analysis';out.mkdir(parents=True,exist_ok=False)
    bindings=dict(left_score_sha256=sha(leftfile),right_score_sha256=sha(rightfile),source_binding=binding)
    dump(out/'ATTEMPT.json',dict(bindings=bindings,started_epoch=time.time(),bootstrap_retries=0))
    try:
        sampled=long_evaluation.paired_question_interval(*[v['endpoints']['math500_sample']['question_correct'] for v in (left,right)])
        greedy=scope.greedy_interval(*[v['endpoints']['math500_greedy']['question_correct'] for v in (left,right)])
        if time.time()>=path.CUTOFF:raise TimeoutError('Owner05UTC cutoff exceeded')
        dump(out/'COMPLETED.json',dict(contrast='D2_minus_D1',primary=sampled,greedy=greedy,bindings=bindings,
            aime_descriptive_only={k:right['endpoints'][k] for k in ('aime24_sample','aime25_sample')},
            amc23=dict(status='incomplete',saved=92,missing=228,accuracy=None,comparison=None),
            missing_as_zero=False,original_worker_failure_retained=True,disclosure=scope.DISCLOSURE,
            single_training_seed=17,question_intervals_not_training_seed_population=True,
            actual_A3_accepted=False,completed_epoch=time.time()))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,message=str(exc),no_retry=True));raise

if __name__=='__main__':main()
