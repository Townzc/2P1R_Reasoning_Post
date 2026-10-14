"""Independent saved-token/lineage replay; MATH symbolic scoring is later P1."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from analyses.completion_contract import first_stop,completion_score
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs,validate_observed_engine
from experiments.learning_regime_p009.stage0_generation_contract import (
    DATASETS,MODELS,SLOTS,BATCH_SIZE,load_rows,transport_checked,remaining_forecast)
from experiments.learning_regime_p009.stage0_generation_binding import (
    CAMPAIGN,validate_release,dispatch_key,dataset_key,marker,intent as claim_intent)


def audit(args):
    from transformers import AutoTokenizer
    spec=read(args.admission);root=Path(args.root);inputs=Path(args.inputs)
    envelope=read(args.receipt);ledger=read(args.ledger);provider=read(args.provider)
    original=read(root/'intent.json');run=original['run_id'];slot=validate_release(
        spec,original['plan'],run,original['release'])
    if original['spec']!=spec or args.run!=run:raise ValueError('Exact original spec/run differs')
    for name,expected in spec['source_files'].items():
        if sha(name)!=expected:raise ValueError('Reviewed source changed')
    pre='midpoint/'+CAMPAIGN+'/';claim=ledger[pre+'claim/'+run];terminal=ledger[pre+'terminal/'+run]
    if (terminal!=envelope['receipt'] or terminal['status']!='completed'
            or claim['run_id']!=run or terminal['run_id']!=run
            or claim['reserved_cents']!=slot['reserved_cents']
            or terminal['actual_cost_cents']!=slot['reserved_cents']
            or terminal['attempt_id']!=claim['attempt_id']
            or ledger[pre+'attempt/'+run+'/'+claim['attempt_id']]!=claim
            or terminal['claim_sha256']!=digest(claim)
            or terminal['evidence_sha256']!=digest(envelope['artifact_manifest'])
            or ledger[pre+'intent/'+run]!=claim_intent(spec,run)
            or claim['intent_sha256']!=digest(claim_intent(spec,run))
            or claim['plan_sha256']!=digest(original['plan'])):
        raise ValueError('Original winning claim/intent/terminal differs')
    if (abs(original['hard_deadline_epoch']-original['worker_started_epoch']-slot['worker_seconds'])>.001
            or terminal['finished_epoch']>original['hard_deadline_epoch']):
        raise ValueError('Actual entry timer/closing differs')
    expected_marker=marker(spec,run,original['release'])
    if expected_marker['provider_app_id']!=args.app_id:
        raise ValueError('Provider must belong to the original winning dispatch')
    for key in [dispatch_key(run)]+[dataset_key(n) for n in slot['datasets']]:
        if ledger.get(key)!=expected_marker:raise ValueError('Original permanent dispatch fence differs')
    for key,value in spec['required_P0_records'].items():
        if ledger.get(key)!=value:raise ValueError('Original P0 linkage differs')
    apps=spec['P0_app_ids']+[args.app_id]
    if (provider['app_ids']!=apps or provider['state']!='stopped'
            or provider['owned_container_ids']):raise ValueError('Exact provider roster must be STOPPED0')
    validate_stopped_apps(apps,provider['original_app_info'],provider['owned_containers'])
    verify(root,envelope['artifact_manifest']);verify(inputs,spec['inputs'])
    result=read(root/'result.json')
    count=sum(DATASETS[n]['n'] for n in slot['datasets'])
    batches=sum(math.ceil(DATASETS[n]['n']/BATCH_SIZE) for n in slot['datasets'])
    if (result!=envelope['result'] or result['new_outputs']!=count
            or result['dataset_counts']!={n:DATASETS[n]['n'] for n in slot['datasets']}
            or result['batches']!=batches or result['first_measurement_exceptions']!=1
            or result['forecasts']!=batches-1 or result['new_training_updates']!=0
            or len(result['full_batch_intervals_seconds'])!=batches):
        raise ValueError('Original full result/denominator differs')
    durations=result['full_batch_intervals_seconds']
    if any(not math.isfinite(x) or x<=0 for x in durations):
        raise ValueError('All original full intervals must be finite and positive')
    if {p.name for p in (root/'forecasts').glob('*.json')}!={f'{i:03d}.json' for i in range(1,batches)}:
        raise ValueError('Missing/extra forecasts')
    for i in range(1,batches):
        f=read(root/'forecasts'/f'{i:03d}.json')
        if f!=remaining_forecast(run,f['elapsed_worker_seconds'],durations[:i],batches-i) or not f['admitted']:
            raise ValueError('An original full-batch/cost forecast did not pass')
    expected={f'{n}_{o:05d}' for n in slot['datasets'] for o in range(0,DATASETS[n]['n'],BATCH_SIZE)}
    for kind in ('unit','done'):
        if {k.removeprefix(pre+run+'/'+kind+'/') for k in ledger if k.startswith(pre+run+'/'+kind+'/')}!=expected:
            raise ValueError('Missing/extra/unknown attempt')
    for directory in ('intents','completed','timings'):
        if {p.stem for p in (root/directory).glob('*.json')}!=expected:
            raise ValueError('Actual immutable journal set differs')
    env=read(root/'environment.json')
    if env['requested_engine']!=engine_kwargs() or env['model']!=MODELS[slot['model']]:
        raise ValueError('Observed model/common engine identity differs')
    validate_observed_engine(env['actual_engine'])
    tokenizer=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True)
    for name,value in spec['models'][slot['model']]['files'].items():
        if name in ('tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','special_tokens_map.json'):
            if sha(Path(args.tokenizer)/name)!=value['sha256']:raise ValueError('Original tokenizer changed')
    vocab=set(tokenizer.get_vocab().values());special=tuple(tokenizer.all_special_ids)
    gold={}
    if any(n.endswith('gsm_zero') or n.endswith('gsm_four') for n in slot['datasets']):
        path=inputs/'gsm8k_test1319.jsonl'
        if sha(path)!=spec['local_gold_files']['gsm8k_test1319.jsonl']['sha256']:
            raise ValueError('Original GSM gold bytes changed')
        with path.open() as f:gold={x['problem_id']:x for x in map(json.loads,f)}
        if len(gold)!=1319:raise ValueError('Complete GSM gold required')
    summaries={};decoded={};index=0
    for name in slot['datasets']:
        ds=DATASETS[name];rows=load_rows(inputs,name);output=[];stops=Counter();backend=Counter();correct=0
        if {p.name for p in (root/name/'raw').glob('*.json')}!={f'{o:05d}.json' for o in range(0,len(rows),BATCH_SIZE)}:
            raise ValueError('Missing/extra original raw file')
        for offset in range(0,len(rows),BATCH_SIZE):
            part=rows[offset:offset+BATCH_SIZE];unit=f'{name}_{offset:05d}';path=root/name/'raw'/f'{offset:05d}.json'
            raw=read(path);transport_checked(name,part,raw)
            attempted=ledger[pre+run+'/unit/'+unit];done=ledger[pre+run+'/done/'+unit]
            if (attempted!=read(root/'intents'/f'{unit}.json')
                    or done!=read(root/'completed'/f'{unit}.json')
                    or attempted['request_sha256']!=digest(part)
                    or attempted['candidate_ids']!=[r['candidate_id'] for r in part]
                    or attempted['first_measurement_exception']!=(index==0)
                    or attempted['preceding_full_batch_seconds']!=durations[:index]
                    or done['candidate_ids']!=attempted['candidate_ids']
                    or done['request_sha256']!=digest(part) or done['raw_sha256']!=sha(path)
                    or done['count']!=len(raw)):
                raise ValueError('Original request, batch or immutable acknowledgement changed')
            timing=read(root/'timings'/f'{unit}.json')
            if (attempted['new_training_updates']!=0 or attempted['dataset']!=name
                    or attempted['offset']!=offset or attempted['count']!=len(part)
                    or not original['worker_started_epoch']<=attempted['started_epoch']
                        <=done['finished_epoch']<=terminal['finished_epoch']
                    or not 0<timing['through_done_ack_seconds']<=durations[index]
                    or done['native_stop_metadata_preserved'] is not True):
                raise ValueError('Original attempt timing or scope differs')
            for row,item in zip(part,raw):
                ids=item['token_ids']
                if any(t not in vocab for t in ids):raise ValueError('Unknown token is not a scored zero')
                native=next((t for t in ids if t in MODELS[slot['model']]['eos_token_ids']),tokenizer.eos_token_id)
                event=first_stop(ids,lambda x:tokenizer.decode(x,skip_special_tokens=False,
                    clean_up_tokenization_spaces=False),native,ds['max_new_tokens'],special)
                record=dict(id=row['candidate_id'],problem_id=row['problem_id'],attempt=row['attempt'],
                    seed=row['seed'],source_row_sha256=row['source_row_sha256'],raw_file=str(path.relative_to(root)),
                    raw_file_sha256=done['raw_sha256'],token_count=len(ids),stop=event,
                    backend_finish_reason=item['finish_reason'],backend_stop_reason=item['stop_reason'])
                if name.endswith('gsm_zero') or name.endswith('gsm_four'):
                    record['score']=completion_score(gold[row['problem_id']],event)
                    correct+=record['score']['task_answer_correct']
                else:record['math_scoring']='Pending actual P1; no symbolic attempt or eligibility here'
                output.append(record);stops[event['stop_reason']]+=1;backend[item['finish_reason']]+=1
            index+=1
        if len(output)!=ds['n'] or len({x['id'] for x in output})!=ds['n']:
            raise ValueError('Full original denominator required')
        decoded[name]=output
        summaries[name]=dict(total=ds['n'],logical_stops=dict(stops),backend_stops=dict(backend),
            technical_unknown=0,correct=correct if name.endswith(('gsm_zero','gsm_four')) else None,
            math_scoring_pending=not name.endswith(('gsm_zero','gsm_four')))
    dump(args.out,dict(schema='p009_stage0_generation_raw_oracle_v1',passed=True,run_id=run,
        summaries=summaries,decoded=decoded,new_outputs=count,new_training_updates=0,
        old_P0_rescored=False,P1_symbolic_scoring_performed=False,G0_admitted=False,
        spec_sha256=digest(spec),artifact_digest=digest(envelope['artifact_manifest']),
        utc=datetime.now(timezone.utc).isoformat()))
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('admission','root','run','inputs','receipt','ledger','provider','app-id','tokenizer','out'):
        p.add_argument('--'+n,required=True)
    audit(p.parse_args())
