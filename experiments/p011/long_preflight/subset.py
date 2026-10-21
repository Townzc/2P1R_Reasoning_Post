"""Deterministic read-only subsets of accepted native long inputs, no encoding."""
from copy import deepcopy
from experiments.p011 import long_training as full, long_execution
from experiments.p011.long_evaluation import BENCHMARK_COUNTS
from experiments.sft_allocation_midpoint.common import digest

OWNER_SHA='364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f'
ENDPOINTS=32


def select(encoded, requests, context, arm):
    # Validate the complete source endpoint roster before taking a subset.
    long_execution.validate_endpoint(requests,context)
    if arm not in full.ARMS or len(encoded)<2 or len({r['path_id'] for r in encoded})!=len(encoded):
        raise ValueError('Original arm and distinct accepted source answers required')
    ordered=sorted(encoded,key=lambda r:(-r['n_processed'],r['path_id']))
    rows=deepcopy(ordered[:2])
    if min(r['n_processed'] for r in rows)<15000:
        raise ValueError('Owner requested near16k longest sequences; no silent smaller proxy')
    plan={'engineering_preflight':True,'scientific_cell_result':False,'optimizer_updates':2,
          'supervised_tokens':2*sum(r['n_supervised'] for r in rows),
          'processed_tokens':2*sum(r['n_processed'] for r in rows),
          'updates':[[0,1],[0,1]],'row_path_ids':[r['path_id'] for r in rows],'seed':17,
          'selection':'two_longest_n_processed_then_path_id_from_accepted_A8',
          'source_encoded_sha256':digest(encoded),'source_requests_sha256':digest(requests)}
    rates=full.learning_rates(2,arm)
    selected=[]
    for b,n in BENCHMARK_COUNTS.items():
        source=sorted((r for r in requests if r['benchmark']==b and r['mode']=='sample' and r['seed']==0),
                      key=lambda r:(-len(r['prompt_token_ids']),r['id']))
        if len(source)!=n:raise ValueError('Original unique question sample0 roster incomplete')
        chosen=[source[(i*(n-1))//7] for i in range(8)]
        if b=='math500':
            # Keep longest-prompt sample0 and add its original greedy mode.
            greedy={r['problem_id']:r for r in requests if r['benchmark']==b and r['mode']=='greedy'}
            chosen[-1]=greedy[chosen[0]['problem_id']]
        selected.extend(deepcopy(chosen))
    validate(rows,plan,rates,arm)
    validate_requests(selected,context)
    proof={'owner_raw_sha256':OWNER_SHA,'source_encoded_sha256':digest(encoded),
           'source_requests_sha256':digest(requests),'source_context':context,
           'selected_training_sha256':digest(rows),'plan_sha256':digest(plan),
           'selected_requests_sha256':digest(selected),'arm':arm,'tokenizer_calls':0,
           'request_subset_scope':'8 per benchmark; prompt-length quantiles; MATH includes original greedy',
           'formal512_batch_throughput_unmeasured':True,'no_score_or_scientific_result':True}
    return rows,plan,rates,selected,proof


def validate(encoded,plan,rates,arm):
    if (arm not in full.ARMS or len(encoded)!=2 or len({r['path_id'] for r in encoded})!=2
            or plan.get('engineering_preflight') is not True or plan.get('scientific_cell_result') is not False
            or plan.get('optimizer_updates')!=2 or plan.get('updates')!=[[0,1],[0,1]]
            or plan.get('seed')!=17 or plan.get('row_path_ids')!=[r['path_id'] for r in encoded]
            or plan.get('selection')!='two_longest_n_processed_then_path_id_from_accepted_A8'
            or rates!=full.learning_rates(2,arm)):
        raise ValueError('Only exact two-update owner preflight subset allowed')
    for r in encoded:
        ids,labels=r['input_ids'],r['labels'];start,end=r['assistant_start'],r['assistant_end']
        if (type(ids) is not list or type(labels) is not list
                or any(type(x) is not int or not 0<=x<151936 for x in ids)
                or any(type(x) is not int for x in labels)
                or any(type(x) is not int for x in (start,end,r['n_supervised'],r['n_processed']))
                or not 0<start<end<=len(ids)<=16384 or len(ids)<15000
                or len(ids)!=r['n_processed'] or len(labels)!=len(ids)
                or labels!=[-100]*start+ids[start:end]+[-100]*(len(ids)-end)
                or r['n_supervised']!=end-start or ids[end-1]!=151645
                or r['eos_token_id']!=151645 or r['template_final_newline_supervised'] is not False):
            raise ValueError('Original strict full native sequence differs')
    target=2*sum(r['n_supervised'] for r in encoded)
    if plan.get('supervised_tokens')!=target or plan.get('processed_tokens')!=2*sum(r['n_processed'] for r in encoded):
        raise ValueError('Exact subset dose differs')
    return {'B':target,'U':2,'once_pass_tokens':target//2,'q':2,
            'lr_sha256':digest(rates),'encoded_sha256':digest(encoded),'plan_sha256':digest(plan),
            'engineering_preflight':True,'scientific_cell_result':False}


def validate_requests(rows,context):
    fields={'id','problem_id','benchmark','source_row','mode','seed','prompt_token_ids',
            'prompt_text_sha256','raw_prompt_text_sha256','native_NFC_changed','required_context','request_sha256'}
    if len(rows)!=ENDPOINTS or len({r['id'] for r in rows})!=ENDPOINTS:
        raise ValueError('Exactly32 original unique subset requests required')
    counts={b:0 for b in BENCHMARK_COUNTS}
    for r in rows:
        b,i=r['benchmark'],r['source_row'];ids=r['prompt_token_ids']
        if (set(r)!=fields or b not in counts or type(i) is not int or not 0<=i<BENCHMARK_COUNTS[b]
                or r['problem_id']!=f'{b}:{i:04d}' or r['id']!=f"{r['problem_id']}:{r['mode']}:{r['seed']}"
                or r['mode'] not in ('sample','greedy') or r['seed']!=0
                or not ids or any(type(x) is not int or not 0<=x<151936 for x in ids)
                or r['required_context']!=len(ids)+16384 or r['required_context']>context
                or type(r['native_NFC_changed']) is not bool
                or any(not isinstance(r[k],str) or len(r[k])!=64 for k in ('request_sha256','prompt_text_sha256','raw_prompt_text_sha256'))):
            raise ValueError('Foreign, gold-bearing or altered original subset request')
        counts[b]+=1
    if set(counts.values())!={8} or sum(r['mode']=='greedy' for r in rows)!=1:
        raise ValueError('Frozen representative benchmark/mode coverage differs')
    long_execution.engine_settings(context)
