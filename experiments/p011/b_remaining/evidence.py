"""Full6400 raw and journal oracle, retaining the original failed provenance."""
from pathlib import Path
import math
from experiments.p011.b_generation_execution import validate_queue
from experiments.p011.b_remaining.execution import prefix_names,check_raw
from experiments.sft_allocation_midpoint.common import read,sha,digest,verify

def check_body(pack,out,key,claim,records,prefix_files,validate_transport,replay_forecast):
    out=Path(out);rows=pack['rows'];roster=validate_queue(pack['ordered400'],pack['prompts'],rows)
    names={'INTENT.json','COMPLETED.json'}|{'original_prefix/'+x for x in prefix_names()}|{
        'prefix_transport/'+n+'.json' for n in ('INTENT','TRANSPORT','ACK')}|{
        f'batches/{i:03d}/{n}.json' for i in range(5,25) for n in ('FORECAST','INTENT','RAW','TRANSPORT','ACK')}
    if {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}!=names or any(p.is_symlink() for p in out.rglob('*')):
        raise ValueError('Complete exact continuation file roster required')
    verify(out/'original_prefix',prefix_files)
    expected=dict(claim=claim,roster_sha256=roster,reused_raw=1280,reused_confirmed_transport=1024,
        new_requests=5120,first_new_batch=5,last_new_batch=24,prefix_files=prefix_files,original_parent_status='failed',new_symbolic_scores=0)
    if read(out/'INTENT.json')!=expected or records[key+'/generation']!=expected or records[key+'/claim']!=claim:
        raise ValueError('Exact continuation identity required')
    result=read(out/'COMPLETED.json');cycles=result['cycles']
    if len(cycles)!=20 or result!={**dict(new_outputs=5120,reused_raw=1280,reused_confirmed_transport=1024,
        newly_transported_prefix_rows=256,complete_new_batches=20,total_outputs=6400,cycles=cycles,
        roster_sha256=roster,original_parent_status='failed',old_outputs_regenerated=0,new_symbolic_scores=0,
        selection_performed=False,training_admitted=False,final_summary_write_excluded_from_cycles=True)}:
        raise ValueError('Complete original continuation result required')
    seen=set();raw_all=[];decoded_all=[];times=[]
    for i in range(25):
        folder=out/('original_prefix/batches' if i<5 else 'batches')/f'{i:03d}'
        raw=read(folder/'RAW.json');part=rows[i*256:(i+1)*256];check_raw(raw,part)
        decoded=read(out/'prefix_transport/TRANSPORT.json' if i==4 else folder/'TRANSPORT.json')
        if len(decoded)!=256:raise ValueError('All256 transports required')
        intent=dict(first=i*256,requests=[x['request'] for x in part],sampling=[x['sampling'] for x in part],roster_sha256=roster)
        if read(folder/'INTENT.json')!=intent:raise ValueError('Saved batch membership differs')
        for x,d in zip(raw,decoded):
            if x['candidate_id'] in seen:raise ValueError('Duplicate original output')
            validate_transport(x,d);seen.add(x['candidate_id'])
        if i==4:
            prefix=dict(raw_sha256=sha(folder/'RAW.json'),count=256)
            ack=dict(**prefix,transport_sha256=sha(out/'prefix_transport/TRANSPORT.json'))
            if (read(out/'prefix_transport/INTENT.json')!=prefix or records[key+'/prefix_transport/004']!=prefix
                    or read(out/'prefix_transport/ACK.json')!=ack or records[key+'/prefix_transport_done/004']!=ack):
                raise ValueError('Original unconfirmed256 transport proof differs')
        else:
            ack=dict(count=256,first=i*256,raw_file_sha256=sha(folder/'RAW.json'),transport_file_sha256=sha(folder/'TRANSPORT.json'))
            if read(folder/'ACK.json')!=ack:raise ValueError('Saved raw/transport byte acknowledgment differs')
        if i>=5:
            c=cycles[i-5];s=c['seconds']
            if (type(s) not in (float,int) or not math.isfinite(s) or s<=0
                    or c!=dict(batch=i,seconds=s,three_commits_and_remote_ack_included=True)
                    or records[key+f'/batch/{i:03d}']!=intent or records[key+f'/batch_done/{i:03d}']!=ack
                    or read(folder/'FORECAST.json')!=replay_forecast(25-i,times)):
                raise ValueError('Complete new timing/fence/forecast differs')
            times.append(s)
        raw_all+=raw;decoded_all+=decoded
    if len(seen)!=6400:raise ValueError('Full6400 original IDs required')
    return dict(verified_total_raw=6400,original_failed_raw_reused=1280,original_confirmed_transports_reused=1024,
        new_outputs=5120,first_prefix_transport=256,original_parent_remains_failed=True,
        raw_metadata_and_saved_transport_bound_without_second_decode=True,new_symbolic_scores=0),raw_all,decoded_all
