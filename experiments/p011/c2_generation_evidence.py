"""Complete new-only C2 window oracle; no model, tokenizer or scorer entry.

The eventual full-path CR must bind original reuse, concrete inputs, timing,
budget, provider, source and common absolute result window. This leaf is not
permission to process the original corpus or perform any production work.
"""
from pathlib import Path
import math
from experiments.p011.short_generation import request
from experiments.sft_allocation_midpoint.common import read, sha, digest


def checked_plan(plan):
    rows=plan.get('new_requests');parents=plan.get('window_parents')
    if (not isinstance(rows,list) or not 1<=len(rows)<=2800
            or not isinstance(parents,list) or not 1<=len(parents)<=700
            or len(parents)!=len(set(parents))
            or not plan.get('immutable_order_sha256')
            or plan.get('new_T72_generation_allowed') is not False
            or plan.get('training_admitted') is not False):
        raise ValueError('Complete original finite C2 plan required')
    seen=set();sequence=[]
    for row in rows:
        r=row['request'];pid=r['problem_id'];attempt=r['attempt'];ids=r['prompt_token_ids']
        if (pid not in parents or type(attempt) is not int or not 1<=attempt<=4
                or r['candidate_id'] in seen or row!=request(pid,attempt,ids,.8)
                or not ids or len(ids)+1024>2048
                or any(type(i) is not int or not 0<=i<151936 for i in ids)):
            raise ValueError('Only original missing attempts1..4 at T.8 allowed')
        seen.add(r['candidate_id']);sequence.append((parents.index(pid),attempt))
    if sequence!=sorted(sequence) or {r['request']['problem_id'] for r in rows}!=set(parents):
        raise ValueError('Immutable original window order and all parents required')
    return rows


def check_body(plan,out,key,claim,records,verify_transport,replay_forecast):
    rows=checked_plan(plan);out=Path(out);batches=(len(rows)+255)//256
    names={'INTENT.json','COMPLETED.json'}|{
        f'batches/{i:03d}/{name}.json' for i in range(batches)
        for name in ('FORECAST','INTENT','RAW','TRANSPORT','ACK')}
    if ({p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}!=names
            or any(p.is_symlink() for p in out.rglob('*'))
            or records.get(key+'/claim')!=claim):
        raise ValueError('Exact completed files and original claim required')
    intent={'plan_sha256':digest(plan),'new_requests':len(rows),'old_outputs_regenerated':0}
    if read(out/'INTENT.json')!=intent or records.get(key+'/window')!=intent:
        raise ValueError('Original complete window intent differs')
    units={key+f'/{kind}/{i:03d}' for i in range(batches) for kind in ('batch','batch_done')}
    if {k for k in records if k.startswith(key+'/batch/') or k.startswith(key+'/batch_done/')}!=units:
        raise ValueError('Every original batch attempt and acknowledgment required')
    result=read(out/'COMPLETED.json');cycles=result.get('cycles')
    if not isinstance(cycles,list) or len(cycles)!=batches:
        raise ValueError('Complete whole-cycle observations required')
    expected={'new_outputs':len(rows),'cycles':cycles,'old_outputs_regenerated':0,
        'old_outputs_rescored':0,'new_symbolic_scores':0,'selection_performed':False,
        'training_admitted':False,'finalization_excluded_from_cycles':True}
    if result!=expected:raise ValueError('Original completed result scope differs')
    durations=[];rawfiles=[];seen=set()
    for i,cycle in enumerate(cycles):
        duration=cycle.get('seconds')
        if (type(duration) not in (int,float) or not math.isfinite(duration) or duration<=0
                or cycle!={'batch':i,'seconds':duration,'three_commits_and_remote_ack_included':True}):
            raise ValueError('Positive complete-cycle duration required')
        part=rows[256*i:256*(i+1)];reqs=[x['request'] for x in part];params=[x['sampling'] for x in part]
        folder=out/'batches'/f'{i:03d}'
        batch={'first':256*i,'requests':reqs,'sampling':params,'plan_sha256':digest(plan)}
        if read(folder/'INTENT.json')!=batch or records[key+f'/batch/{i:03d}']!=batch:
            raise ValueError('Original batch identities differ')
        if read(folder/'FORECAST.json')!=replay_forecast(batches-i,list(durations)):
            raise ValueError('Saved whole-cycle forecast differs')
        raw=read(folder/'RAW.json');transport=read(folder/'TRANSPORT.json')
        if len(raw)!=len(part) or len(transport)!=len(part):
            raise ValueError('Complete full or tail batch required')
        for x,r,p,t in zip(raw,reqs,params,transport):
            cid=r['candidate_id']
            if (cid in seen or x.get('candidate_id')!=cid or x.get('problem_id')!=r['problem_id']
                    or x.get('source_row_sha256') is not None or x.get('sampling')!=p
                    or x.get('prompt_token_ids')!=r['prompt_token_ids']
                    or type(x.get('output_count')) is not int or x['output_count']!=1
                    or set(x)!={'candidate_id','problem_id','source_row_sha256','sampling',
                        'prompt_token_ids','output_count','token_ids','backend_text','finish_reason','stop_reason'}):
                raise ValueError('Foreign, duplicate or incomplete new raw response')
            if verify_transport(x)!=t:raise ValueError('Original new token/stop transport differs')
            seen.add(cid)
        ack={'count':len(part),'first':256*i,'raw_file_sha256':sha(folder/'RAW.json'),
             'transport_file_sha256':sha(folder/'TRANSPORT.json')}
        if read(folder/'ACK.json')!=ack or records[key+f'/batch_done/{i:03d}']!=ack:
            raise ValueError('Original raw hashes or immutable acknowledgment differ')
        rawfiles.append(ack['raw_file_sha256']);durations.append(duration)
    return {'verified_new_outputs':len(seen),'verified_batches':batches,'plan_sha256':digest(plan),
        'ordered_raw_files_sha256':digest(rawfiles),'old_outputs_read_or_rescored':0,
        'new_symbolic_comparisons':0,'selection_performed':False,'training_admitted':False,
        'outer_source_input_receipt_provider_and_window_still_required':True}
