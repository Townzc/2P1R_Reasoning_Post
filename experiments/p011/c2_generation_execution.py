"""Prepared fixed C2 window journal; no dispatch, loader, scoring or admission.

Original full-path CR/A1/A2, current C budget (including failed C1), shared max4
ledger, exact source/input binding and complete measured timing are mandatory.
C1 self-calibration exception does not authorize this path.
"""
from pathlib import Path
import time
from experiments.p011.short_generation import request
from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
from experiments.sft_allocation_midpoint.common import dump,digest,sha


def generate_window(plan,out,key,claim,store,commit,llm,parameter_constructor,
                    transport,forecast,check,clock=time.monotonic):
    rows=plan['new_requests']
    if not rows or len(rows)>2800 or not plan.get('immutable_order_sha256'):
        raise ValueError('Complete admitted finite C2 window required')
    seen=set()
    for row in rows:
        r=row['request'];pid=r['problem_id'];a=r['attempt'];ids=r['prompt_token_ids']
        if (type(a) is not int or not 1<=a<=4 or pid not in plan['window_parents']
                or r['candidate_id'] in seen or row!=request(pid,a,ids,.8)):
            raise ValueError('Exact original C2 requests1..4/T.8 required')
        seen.add(r['candidate_id'])
    out=Path(out);check()
    if out.exists():raise ValueError('Existing/partial window cannot be replayed')
    if store.get(key+'/claim')!=claim:raise ValueError('Original C2 outer claim changed')
    params=[parameter_constructor(**x['sampling']) for x in rows]
    intent={'plan_sha256':digest(plan),'new_requests':len(rows),'old_outputs_regenerated':0}
    if not store.put(key+'/window',intent,skip_if_exists=True):
        raise ValueError('C2 window marker already exists; no retry')
    out.mkdir();cycles=[];count=0
    try:
        dump(out/'INTENT.json',intent);commit()
        total=(len(rows)+255)//256
        for first in range(0,len(rows),256):
            start=clock();check();number=first//256;part=rows[first:first+256]
            if store.get(key+'/claim')!=claim:raise ValueError('C2 claim changed')
            projection=forecast(total-number,[v['seconds'] for v in cycles])
            requests=[x['request'] for x in part];sampling=[x['sampling'] for x in part]
            b={'first':first,'requests':requests,'sampling':sampling,'plan_sha256':digest(plan)}
            if not store.put(key+f'/batch/{number:03d}',b,skip_if_exists=True):
                raise ValueError('C2 batch already attempted')
            directory=out/'batches'/f'{number:03d}'
            dump(directory/'FORECAST.json',projection);dump(directory/'INTENT.json',b);commit()
            outputs=llm.generate([{'prompt_token_ids':r['prompt_token_ids']} for r in requests],
                                 params[first:first+256],use_tqdm=False)
            raw=returned_records(requests,sampling,outputs);dump(directory/'RAW.json',raw);commit();check()
            if len(raw)!=len(part) or any(x['candidate_id']!=r['candidate_id']
                    or x['prompt_token_ids']!=r['prompt_token_ids'] or x['sampling']!=p
                    or x['output_count']!=1 for x,r,p in zip(raw,requests,sampling)):
                raise ValueError('C2 raw shape/identity differs; partial bytes retained')
            verified=[transport(x) for x in raw];dump(directory/'TRANSPORT.json',verified)
            ack={'count':len(raw),'first':first,'raw_file_sha256':sha(directory/'RAW.json'),
                 'transport_file_sha256':sha(directory/'TRANSPORT.json')}
            dump(directory/'ACK.json',ack);commit()
            if not store.put(key+f'/batch_done/{number:03d}',ack,skip_if_exists=True):
                raise ValueError('Duplicate C2 complete-batch acknowledgment')
            elapsed=clock()-start
            if elapsed<=0:raise ValueError('Positive complete cycle required')
            cycles.append({'batch':number,'seconds':elapsed,'three_commits_and_remote_ack_included':True})
            count+=len(raw)
        check();result={'new_outputs':count,'cycles':cycles,'old_outputs_regenerated':0,
            'old_outputs_rescored':0,'new_symbolic_scores':0,'selection_performed':False,
            'training_admitted':False,'finalization_excluded_from_cycles':True}
        dump(out/'COMPLETED.json',result);commit();check();return result
    except BaseException as exc:
        dump(out/'FAILED.json',{'type':type(exc).__name__,'error':str(exc),'cycles':cycles,
            'confirmed_outputs':count,'automatic_retry':False,'partial_raw_retained':True});commit();raise
