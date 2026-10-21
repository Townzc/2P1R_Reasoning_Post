"""Copy the confirmed failed prefix; generate only original batches005–024 once."""
from pathlib import Path
import time,shutil
from experiments.p011.b_generation_execution import validate_queue
from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify

def prefix_names():
    return {f'batches/{i:03d}/{n}.json' for i in range(5)
            for n in (('RAW','INTENT','FORECAST','TRANSPORT','ACK') if i<4 else ('RAW','INTENT','FORECAST'))}

def copy_prefix(source,out,files,rows):
    source,out=Path(source),Path(out)
    if set(files)!=prefix_names():raise ValueError('Exact23 failed-prefix files required')
    verify(source,files)
    for name in sorted(files):
        target=out/'original_prefix'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as dst,(source/name).open('rb') as src:shutil.copyfileobj(src,dst)
        if sha(target)!=files[name]['sha256']:raise ValueError('Failed prefix copy differs')
    for i in range(5):
        part=rows[i*256:(i+1)*256];folder=out/'original_prefix/batches'/f'{i:03d}'
        raw=read(folder/'RAW.json');old_intent=read(folder/'INTENT.json')
        if (old_intent['first']!=i*256 or old_intent['requests']!=[x['request'] for x in part]
                or old_intent['sampling']!=[x['sampling'] for x in part]):
            raise ValueError('Original failed-prefix request membership differs')
        check_raw(raw,part)
        if i<4:
            ack=read(folder/'ACK.json');decoded=read(folder/'TRANSPORT.json')
            if (len(decoded)!=256 or ack['raw_file_sha256']!=sha(folder/'RAW.json')
                    or ack['transport_file_sha256']!=sha(folder/'TRANSPORT.json')
                    or any(d['raw_record_sha256']!=digest(x) for x,d in zip(raw,decoded))):
                raise ValueError('Original confirmed transport/ack bytes differ')

def check_raw(raw,part):
    if len(raw)!=len(part):raise ValueError('Incomplete raw output retained')
    for item,row in zip(raw,part):
        req=row['request']
        if (item['candidate_id']!=req['candidate_id'] or item['problem_id']!=req['problem_id']
                or item['prompt_token_ids']!=req['prompt_token_ids'] or item['sampling']!=row['sampling']
                or item['source_row_sha256'] is not None or type(item['output_count']) is not int
                or item['output_count']!=1):raise ValueError('Original raw/request identity differs')

def generate(pack,out,key,claim,store,commit,llm,constructor,transport,forecast,check,
             prefix_source,prefix_files,clock=time.monotonic):
    roster=validate_queue(pack['ordered400'],pack['prompts'],pack['rows']);rows=pack['rows'];out=Path(out)
    check()
    if out.exists() or store.get(key+'/claim')!=claim:raise ValueError('Original continuation claim/output differs')
    parameters=[constructor(**r['sampling']) for r in rows[1280:]]
    intent=dict(claim=claim,roster_sha256=roster,reused_raw=1280,reused_confirmed_transport=1024,
        new_requests=5120,first_new_batch=5,last_new_batch=24,prefix_files=prefix_files,
        original_parent_status='failed',new_symbolic_scores=0)
    if not store.put(key+'/generation',intent,skip_if_exists=True):raise ValueError('Continuation already attempted')
    out.mkdir();dump(out/'INTENT.json',intent);commit();cycles=[];generated=0
    try:
        copy_prefix(prefix_source,out,prefix_files,rows);commit();check()
        # Exactly one first transport of original unconfirmed batch004. The
        # already confirmed first1024 transports are copied, never decoded again.
        raw4=read(out/'original_prefix/batches/004/RAW.json')
        unit=key+'/prefix_transport/004'
        original=dict(raw_sha256=sha(out/'original_prefix/batches/004/RAW.json'),count=256)
        if not store.put(unit,original,skip_if_exists=True):raise ValueError('Unconfirmed prefix transport already attempted')
        dump(out/'prefix_transport/INTENT.json',original);commit()
        decoded4=[transport(x) for x in raw4];dump(out/'prefix_transport/TRANSPORT.json',decoded4)
        ack4=dict(**original,transport_sha256=sha(out/'prefix_transport/TRANSPORT.json'))
        dump(out/'prefix_transport/ACK.json',ack4);commit()
        if not store.put(key+'/prefix_transport_done/004',ack4,skip_if_exists=True):raise ValueError('Duplicate prefix transport ack')
        for number in range(5,25):
            tick=clock();check()
            if store.get(key+'/claim')!=claim:raise ValueError('Continuation claim changed')
            first=number*256;part=rows[first:first+256]
            projection=forecast(25-number,[x['seconds'] for x in cycles])
            batch=dict(first=first,requests=[x['request'] for x in part],sampling=[x['sampling'] for x in part],roster_sha256=roster)
            if not store.put(key+f'/batch/{number:03d}',batch,skip_if_exists=True):raise ValueError('Original remaining batch already attempted')
            directory=out/'batches'/f'{number:03d}';dump(directory/'FORECAST.json',projection);dump(directory/'INTENT.json',batch);commit()
            output=llm.generate([{'prompt_token_ids':r['prompt_token_ids']} for r in batch['requests']],
                parameters[(number-5)*256:(number-4)*256],use_tqdm=False)
            raw=returned_records(batch['requests'],batch['sampling'],output);dump(directory/'RAW.json',raw);commit();check()
            check_raw(raw,part);decoded=[transport(x) for x in raw];dump(directory/'TRANSPORT.json',decoded)
            ack=dict(count=256,first=first,raw_file_sha256=sha(directory/'RAW.json'),transport_file_sha256=sha(directory/'TRANSPORT.json'))
            dump(directory/'ACK.json',ack);commit()
            if not store.put(key+f'/batch_done/{number:03d}',ack,skip_if_exists=True):raise ValueError('Duplicate remaining batch ack')
            elapsed=clock()-tick
            if elapsed<=0:raise ValueError('Positive complete cycle required')
            cycles.append(dict(batch=number,seconds=elapsed,three_commits_and_remote_ack_included=True));generated+=256
        check();result=dict(new_outputs=generated,reused_raw=1280,reused_confirmed_transport=1024,
            newly_transported_prefix_rows=256,complete_new_batches=20,total_outputs=6400,cycles=cycles,
            roster_sha256=roster,original_parent_status='failed',old_outputs_regenerated=0,
            new_symbolic_scores=0,selection_performed=False,training_admitted=False,
            final_summary_write_excluded_from_cycles=True)
        dump(out/'COMPLETED.json',result);commit();check();return result
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),confirmed_new_outputs=generated,
            cycles=cycles,automatic_retry=False,original_failed_parent_unchanged=True));commit();raise
