"""Delegated D2: two OLMo/T72 students and one matching MATH greedy baseline."""
import math
from experiments.p010.common import budget_check,digest

STUDENTS={'e9_s17_n400','e9_s17_n3200'}
BASELINE='e9_base_math'
RUNS=STUDENTS|{BASELINE}
RATE=.001097+4*.0000131+32*.00000222


def limits(run):
    if run not in RUNS:raise ValueError('Only delegated E9 cells')
    return ('I',1200,'2.52',1900) if run==BASELINE else ('T',4500,'6.55',5200)


def evaluation_jobs():
    return [('greedy',17,0.,1.)]


def sampling(job):
    if job not in evaluation_jobs():raise ValueError('Only original greedy endpoint')
    return dict(n=1,temperature=0.,top_p=1.,top_k=-1,repetition_penalty=1,
        max_tokens=1024,seed=17,stop=None,stop_token_ids=[100257],ignore_eos=False,
        detokenize=True,skip_special_tokens=False,include_stop_str_in_output=True)


def forecast(elapsed,train_left,eval_left,train_seconds,eval_seconds,prior,*,baseline=False):
    if (type(train_left) is not int or not 0<=train_left<=64
            or type(eval_left) is not int or not 0<=eval_left<=2
            or not math.isfinite(elapsed) or elapsed<0
            or not train_seconds or not eval_seconds
            or any(not math.isfinite(x) or x<=0 for x in train_seconds+eval_seconds)
            or (baseline and train_left!=0)):
        raise ValueError('Complete original all-batch timing required')
    category,hard,reserve,_=limits(BASELINE if baseline else 'e9_s17_n400')
    future=1.2*(max(train_seconds)*train_left+max(eval_seconds)*eval_left+600)
    total=elapsed+future
    if total>hard-30:raise TimeoutError('Full original E9 window does not fit')
    budget=budget_check(category,prior,reserve,(total+700)*RATE)
    return dict(elapsed_seconds=elapsed,train_blocks_left=train_left,eval_batches_left=eval_left,
        train_max=max(train_seconds),eval_max=max(eval_seconds),training_observations=len(train_seconds),
        endpoint_observations=len(eval_seconds),remaining_seconds=future,allowance_seconds=600,
        margin=1.2,forecast_total_seconds=total,calibrated_bound=False,
        different_model_task_timing_transfer_not_guaranteed=True,baseline=baseline,budget=budget)


def verify_prompt_texts(endpoint,text_rows,tokenizer):
    """Exact A1 prompt hash plus actual model-side text/token equality, no gold."""
    if (len(endpoint)!=500 or len(text_rows)!=500
            or len({r['problem_id'] for r in endpoint})!=500
            or tokenizer.eos_token_id!=100257):
        raise ValueError('Original OLMo500 endpoint required')
    for row,text in zip(endpoint,text_rows):
        if (set(text)!={'problem_id','prompt_text'}
                or row['problem_id']!=text['problem_id']
                or digest(text)!=row['source_row_sha256']
                or tokenizer(text['prompt_text'],add_special_tokens=False)['input_ids']!=row['input_ids']
                or not row['input_ids'] or len(row['input_ids'])+1024>2048
                or 100257 in row['input_ids']):
            raise ValueError('Exact gold-free prompt text/token binding differs')
    return dict(rows=500,endpoint_sha256=digest(endpoint),text_rows_sha256=digest(text_rows),
        model_eos=100257,actual_model_tokenization_checked=True,gold_used=False)
