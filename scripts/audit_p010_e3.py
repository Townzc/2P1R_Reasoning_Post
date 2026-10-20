"""Complete original E3 provenance/raw oracle; saved T0.8 is never decoded again."""
import argparse,datetime,json,os,threading
from collections import Counter
from pathlib import Path
from experiments.p010.common import read,dump,sha,digest,verify,utc
from experiments.p010.e3_contract import KEY,HARD_SECONDS,TEMPERATURES,check_rosters,forecast


def record_keys():
    return [KEY+'/'+k for k in ('dispatch','claim','terminal')]+[
        KEY+'/'+kind+'/'+label+f'/{first:04d}' for label,_ in TEMPERATURES
        for first in range(0,1600,256) for kind in ('batch','done')]


def records(a):
    import modal
    receipt,export,out=map(Path,(a.receipt,a.export,a.out))
    if read(receipt/'RESULT.json')['status']!='completed' or read(export/'COMPLETED.json')['provider_stopped'] is not True:
        raise ValueError('Original complete result and STOPPED0 collection required')
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),named_keys=record_keys(),local_seconds=1200,no_retry=True))
    timer=threading.Timer(1200,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False);values={}
        for i,key in enumerate(record_keys()):
            value=store.get(key)
            if value is None:raise ValueError('Missing exact original key '+key)
            values[key]=value;dump(out/'confirmed'/f'{i:03d}.json',dict(key=key,value=value))
        dump(out/'RECORDS.json',values)
        dump(out/'COMPLETED.json',dict(utc=utc(),records_sha256=sha(out/'RECORDS.json'),
            receipt_sha256=sha(receipt/'RESULT.json'),provider_sha256=sha(export/'PROVIDER_PRIVATE.json')))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(utc=utc(),error=str(exc),partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


def audit(a):
    from transformers import AutoTokenizer
    from experiments.p010.teacher_transport import completion
    from experiments.p010.tier3_dispatch import fixed_review,validate_a4
    from experiments.p010.e3_contract import validate_d4
    from experiments.learning_regime_p009.high_throughput_v1 import validate_observed_engine
    from experiments.learning_regime_p009.math_scoring import last_box
    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    spec=read(a.spec);receipt,export,inputs,out=map(Path,(a.receipt,a.export,a.inputs,a.out))
    env,sent,local=[read(receipt/n) for n in ('RESULT.json','SUBMITTED.json','INTENT.json')]
    root=export/'evidence';worker=read(root/'INTENT.json');col=read(export/'COMPLETED.json')
    provider=read(export/'PROVIDER_PRIVATE.json');rec=read(Path(a.records)/'COMPLETED.json');ledger=read(Path(a.records)/'RECORDS.json')
    if (env['status']!='completed' or sent['run']!='temperature_supply_r1'
            or col['original_result_sha256']!=sha(receipt/'RESULT.json') or col['artifact']!=env['artifact']
            or provider['app_id']!=sent['app_id'] or col['provider_stopped'] is not True
            or rec['receipt_sha256']!=sha(receipt/'RESULT.json')
            or rec['provider_sha256']!=sha(export/'PROVIDER_PRIVATE.json')
            or rec['records_sha256']!=sha(Path(a.records)/'RECORDS.json')
            or set(ledger)!=set(record_keys()) or ledger[KEY+'/dispatch']!=local
            or ledger[KEY+'/claim']!=worker['claim'] or ledger[KEY+'/terminal']!=env
            or worker['execution']!=local['execution'] or worker['claim']['epoch']!=worker['worker_start_epoch']
            or worker['claim']['execution']!=local['execution'] or worker['source_files']!=spec['source_files']
            or worker['input_files']!=spec['input_files'] or worker['model']!=spec['model']
            or worker['reviews']!=local['reviews'] or worker['budget']!=local['budget']
            or abs(worker['hard_deadline_epoch']-worker['worker_start_epoch']-HARD_SECONDS)>.001
            or datetime.datetime.fromisoformat(env['finished_utc']).timestamp()>worker['hard_deadline_epoch']
            or not 0<env['seconds_including_pack']<=HARD_SECONDS
            or env['result']!=read(root/'RESULT.json')):
        raise ValueError('Exact original result/source/lifetime/claim/ledger binding differs')
    validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
    review=read(a.runtime_review);clean=fixed_review(review);owner=read(a.owner_d4);validate_d4(owner)
    if (clean!=worker['reviews']['A2'] or review['scope']!=spec['runtime_A2_scope']
            or review['spec_sha256']!=sha(a.spec) or review['source_files']!=spec['source_files']
            or review.get('input_A1_accepted') is not True or review.get('D1_hourly_coverage_scope_accepted') is not True
            or review['settlement_proposal_sha256']!=spec['settlement_proposal_sha256']
            or sha(a.owner_d4)!=spec['owner_D4_file_sha256']
            or sha(owner['local_evidence_file'])!=owner['evidence_sha256']):
        raise ValueError('Exact actual A1/A2 and original D4 required')
    validate_a4(worker['reviews']['A4']['report'],worker['reviews']['actual_results_A3'])
    for name,h in {**spec['source_files'],**spec['verification_source_files']}.items():
        if sha(name)!=h:raise ValueError('Frozen source changed '+name)
    verify(inputs,spec['input_files']);verify(root,env['artifact']['compact_members'])
    if (sha(export/'evidence.tar.gz')!=env['artifact']['tar_sha256']
            or read(root/'COMPACT_MEMBERS.json')!=env['artifact']['compact_members']
            or any(n.endswith(('.pt','.safetensors')) for n in env['artifact']['all_files'])):
        raise ValueError('Original compact archive or no-training condition differs')
    for name,h in spec['local_tokenizer_files'].items():
        if sha(Path(a.tokenizer)/name)!=h:raise ValueError('Original tokenizer bytes differ')
    if sha(inputs/'GOLD_SOURCE.json')!=spec['gold_source_sha256']:
        raise ValueError('Original200 full solutions differ')
    gold={x['problem_id']:x for x in read(inputs/'GOLD_SOURCE.json')}
    tokenizer=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True)
    mapped=set(tokenizer.get_vocab().values());special=set(tokenizer.all_special_ids)
    groups={label:read(inputs/(label+'_requests.json')) for label,_ in TEMPERATURES}
    check_rosters(read(inputs/'ROSTER.json'),groups)
    engine=read(root/'ENGINE.json');validate_observed_engine(engine['actual'])
    if engine['requested']['tensor_parallel_size']!=4 or engine['model']!=spec['model']:
        raise ValueError('Original TP4 model configuration differs')
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),spec_sha256=sha(a.spec),new_raw_rows=3200,old_T08_decode=False,
        no_state_loading=True,no_symbolic_scoring=True,local_seconds=7200))
    timer=threading.Timer(7200,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        observed=spec['timing']['original_full_batch_seconds'];setup=spec['timing']['observed_pre_first_batch_seconds']
        charged=worker['budget']['D1_charged_G_usd'];before=read(root/'BEFORE_MODEL_FORECAST.json')
        if before!=forecast(before['elapsed_seconds'],0,[],observed,setup,model_loaded=False,charged_G=charged):
            raise ValueError('Original before-model forecast differs')
        decoded=[];scoring=[];times=[];stops=Counter();expected_names=set()
        for label,temperature in TEMPERATURES:
            rows=groups[label]
            for first in range(0,1600,256):
                name=label+f'/{first:04d}.json';unit=name[:-5];expected_names.add(name)
                part=rows[first:first+256];raw=read(root/'raw'/name);transport=read(root/'transport'/name)
                intent=read(root/'intents'/name);ack=read(root/'acks'/name);f=read(root/'forecasts'/name)
                if (intent!=ledger[KEY+'/batch/'+unit] or intent['rows']!=part
                        or intent['sampling']!=[x['sampling'] for x in part] or intent['temperature_label']!=label
                        or ack!=ledger[KEY+'/done/'+unit] or ack['raw_sha256']!=sha(root/'raw'/name)
                        or ack['transport_sha256']!=sha(root/'transport'/name) or ack['count']!=len(part)
                        or ack['generated_total']!=len(decoded)+len(part) or len(raw)!=len(part) or len(transport)!=len(part)
                        or f!=forecast(f['elapsed_seconds'],len(times),times,observed,setup,model_loaded=True,charged_G=charged)):
                    raise ValueError('Original complete batch/forecast/ack differs')
                for req,x,t in zip(part,raw,transport):
                    if (x['candidate_id']!=req['candidate_id'] or x['prompt_token_ids']!=req['prompt_token_ids']
                            or x['sampling']!=req['sampling'] or x['output_count']!=1):
                        raise ValueError('Original output identity/parameters differ')
                    logical,meta=completion(x,tokenizer,mapped,spec['model']['vocab_size'],special)
                    if t!=dict(candidate_id=x['candidate_id'],logical=logical,transport=meta,raw_record_sha256=digest(x)):
                        raise ValueError('Independent complete token/stop replay differs')
                    d=dict(candidate_id=x['candidate_id'],temperature_label=label,temperature=temperature,
                        problem_id=req['problem_id'],attempt=req['attempt'],answer_text=logical['answer_segment'],
                        stop=logical,transport=meta,physical_returned_tokens=len(x['token_ids']),
                        raw_record_sha256=digest(x),raw_file='raw/'+name)
                    original=gold[req['problem_id']];answer=last_box(original['solution'])['answer']
                    if not answer:raise ValueError('Original eligible200 gold must remain supported')
                    scoring.append(dict(id=x['candidate_id'],evaluation=label,problem_id=req['problem_id'],attempt=req['attempt'],
                        gold=answer,answer_segment=logical['answer_segment'],stop_reason=logical['stop_reason'],
                        original_gold_row_sha256=digest(original),original_decoded_record_sha256=digest(d)))
                    decoded.append(d);stops[logical['stop_reason']]+=1
                times.append(ack['seconds'])
        for folder in ('raw','transport','intents','acks','forecasts'):
            if {p.relative_to(root/folder).as_posix() for p in (root/folder).rglob('*.json')}!=expected_names:
                raise ValueError('Missing or additional original batch files')
        if len(decoded)!=3200 or env['result']['batch_seconds']!=times or env['result']['counts']!={'t06':1600,'t10':1600}:
            raise ValueError('Original full3200 result differs')
        dump(out/'DECODED_ROWS.json',decoded);dump(out/'SCORING_ROWS.json',scoring)
        dump(out/'COMPLETED.json',dict(utc=utc(),passed=True,outputs_decoded=3200,technical_unknown=0,
            source_files=spec['source_files'],verification_source_files=spec['verification_source_files'],
            spec_sha256=sha(a.spec),original_receipt_sha256=sha(receipt/'RESULT.json'),
            original_artifact_digest=digest(env['artifact']['all_files']),reviews=worker['reviews'],
            decoded_rows_sha256=sha(out/'DECODED_ROWS.json'),scoring_rows_sha256=sha(out/'SCORING_ROWS.json'),
            gold_source_sha256=sha(inputs/'GOLD_SOURCE.json'),scorer_sha256=sha('experiments/learning_regime_p009/math_scoring.py'),
            stops=dict(stops),symbolic_scoring_performed=False,old_T08_decodes=0,new_training_updates=0,
            old_binary_loads=0,independent_A3_pending=True))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('records')
    for n in ('receipt','export','out'):q.add_argument('--'+n,required=True)
    q=sub.add_parser('audit')
    for n in ('spec','receipt','export','records','inputs','tokenizer','runtime-review','owner-d4','out'):q.add_argument('--'+n,required=True)
    a=p.parse_args();records(a) if a.action=='records' else audit(a)
