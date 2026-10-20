"""P010 §2.5 original S1 four new sample evaluations; no greedy or training."""
import math
from experiments.p010.common import digest,budget_check

RUNS=('s1_s17_n400','s1_s17_n3200')
HARD_SECONDS=1200
RESERVE_USD='2.52'
RATE=.001097+4*.0000131+32*.00000222


def parent_checked(run,checkpoint,merge,oracle,acceptance):
    if run not in RUNS:
        raise ValueError('Only the two already completed original S1 models')
    if (checkpoint['step']!=1024 or checkpoint['supervised_tokens']!=2097148
            or checkpoint['schema']!='complete_lora_v1'
            or merge['checkpoint']!=checkpoint or merge['merge_dtype']!='float32'
            or merge['saved_dtype']!='bfloat16' or merge['final_checkpoint_only'] is not True
            or merge['optimizer_updates_after_terminal_save']!=0
            or oracle.get('passed') is not True or oracle['run_id']!=run
            or oracle['updates_verified']!=1024 or oracle['targets_verified']!=2097148
            or oracle['state_sha256']!=checkpoint['sha256']
            or acceptance.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or run not in acceptance['first_pair_run_ids']):
        raise ValueError('Original completed final checkpoint and actual A4 required')
    return dict(run_id=run,checkpoint=checkpoint,merged_files=merge['merged_files'],
        original_oracle=oracle,original_A4_report_sha256=acceptance['report_sha256'],
        original_greedy_reused=True,new_training_updates=0,new_sample_outputs=2000)


def rows_checked(endpoint):
    if (not isinstance(endpoint,list) or len(endpoint)!=500
            or len({r['problem_id'] for r in endpoint})!=500
            or any(set(r)-{'problem_id','candidate_id','input_ids','source_row_sha256'} for r in endpoint)):
        raise ValueError('Exact500 gold-free original MATH prompts required')
    out=[]
    for seed in range(4):
        for i,row in enumerate(endpoint):
            ids=row['input_ids']
            if (not ids or len(ids)+1024>2048
                    or any(type(x) is not int or not 0<=x<151936 for x in ids)):
                raise ValueError('Original complete prompt cannot be truncated')
            out.append(dict(candidate_id=f'sample{seed}/math/{i:03d}',
                problem_id=row['problem_id'],input_ids=ids,source_row_sha256=digest(row),
                sampling_seed=seed))
    return out


def sampling(seed):
    if type(seed) is not int or seed not in range(4):raise ValueError('Only original seeds0–3')
    return dict(n=1,temperature=.6,top_p=.95,top_k=-1,repetition_penalty=1,
        max_tokens=1024,seed=seed,stop=None,stop_token_ids=[151643],ignore_eos=False,
        detokenize=True,skip_special_tokens=False,include_stop_str_in_output=True)


def forecast(elapsed,completed,actual_times,observed,prior):
    if (not math.isfinite(elapsed) or elapsed<0 or type(completed) is not int
            or not 0<=completed<8 or len(actual_times)!=completed or not observed
            or any(not math.isfinite(x) or x<=0 for x in list(actual_times)+list(observed))):
        raise ValueError('Complete original measured intervals required')
    maximum=max(list(actual_times)+list(observed))
    # Restoring/merging the saved adapter is inference setup, not retraining.
    # This600s allowance is uncalibrated; the whole entry timer remains binding.
    remaining=1.2*(maximum*(8-completed)+600)
    total=elapsed+remaining
    if total>HARD_SECONDS-30:raise TimeoutError('Original sample-only remainder does not fit')
    return dict(elapsed_seconds=elapsed,completed_batches=completed,full_batches=8,
        original_observations=list(observed),actual_completed_seconds=list(actual_times),
        maximum_seconds=maximum,remaining_seconds=remaining,total_seconds=total,
        setup_allowance_seconds=600,margin=1.2,calibrated_bound=False,
        first_paid_measurement_exceptions=0,
        budget=budget_check('T',prior,RESERVE_USD,(total+700)*RATE))
