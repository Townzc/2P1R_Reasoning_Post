"""Once-only original question-level primary contrast, never student selection."""
import argparse,time
from pathlib import Path
from experiments.p011 import long_conditional_path as path,long_evaluation
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
ROOT=Path(__file__).resolve().parents[1]


def allowed(left,right):
    # Original smoke vs same-size baseline or frozen A/D axis, same selected arm.
    if left['kind']=='baseline':
        return right['kind']=='student' and right['cell']=='A7' and (left['arm']=='S-L3')==(right['arm']=='S-L3')
    if left['arm']!=right['arm'] or left['kind']!='student' or right['kind']!='student':return False
    pair=(left['cell'],right['cell'])
    return (pair[0]=='A1' and pair[1] in ('A2','A3','A4','A5','A6','A7')) or pair in (('A5','A7'),('A8','A7'),('D1','D2'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--left',required=True);parser.add_argument('--right',required=True);parser.add_argument('--review',required=True);a=parser.parse_args()
    spec=path.validate(read(ROOT/path.SPEC));path.published(ROOT,spec);review=path.reviewed(spec,ROOT/path.SPEC,read(a.review));left=spec['jobs'][a.left];right=spec['jobs'][a.right]
    if not allowed(left,right):raise ValueError('Not an original same-arm contrast')
    saved=[];bindings={};deadline=path.CUTOFF
    for name,job in ((a.left,left),(a.right,right)):
        folder=ROOT/path.LOCAL/'long_io_r1/score'/name
        value=read(folder/'COMPLETED.json');proof=read(ROOT/path.LOCAL/'long_io_r1/audit'/name/'COMPLETE_PROOF.json')
        receipt=read(ROOT/path.LOCAL/'dispatch'/name/'RESULT.json')
        deadline=min(deadline,receipt['worker_start_epoch']+job['limits']['worker_seconds']+job['limits']['closeout_seconds'])
        if (proof['job_sha256']!=digest(job) or proof['source_files']!=spec['source_files']
                or value['read_only_saved_score_proof']['passed'] is not True):raise ValueError('Complete exact score/oracle absent')
        saved.append(value['read_only_saved_score_proof']);bindings[name]={'score_sha256':sha(folder/'COMPLETED.json'),'oracle_sha256':sha(ROOT/path.LOCAL/'long_io_r1/audit'/name/'COMPLETE_PROOF.json')}
    if time.time()+60>deadline:raise TimeoutError('Original full result window lacks analysis allowance')
    out=ROOT/path.LOCAL/'long_analysis_r1'/(a.left+'__'+a.right);out.mkdir(parents=True,exist_ok=False)
    dump(out/'ATTEMPT.json',dict(bindings=bindings,review=review,original_absolute_deadline=deadline,bootstrap_retries=0))
    try:
        result=long_evaluation.paired_question_interval(*[v['endpoints']['math500_sample']['question_correct'] for v in saved])
        secondary={label:{'left_correct':saved[0]['endpoints'][label]['correct'],'right_correct':saved[1]['endpoints'][label]['correct'],'total':saved[0]['endpoints'][label]['total'],'difference_pp':100*(saved[1]['endpoints'][label]['mean_pass_at_one']-saved[0]['endpoints'][label]['mean_pass_at_one']),'descriptive_only':True} for label in saved[0]['endpoints'] if label!='math500_sample'}
        if time.time()>=deadline:raise TimeoutError('Original analysis deadline exceeded')
        dump(out/'COMPLETED.json',dict(primary=result,secondary=secondary,bindings=bindings,actual_A3_accepted=False,student_selection_performed=False,interpretation_written=False))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,message=str(exc),no_retry=True));raise
if __name__=='__main__':main()
