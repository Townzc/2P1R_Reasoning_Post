"""Complete new C6 group provenance/raw audit; never re-score reused endpoints."""
import argparse,datetime,json,os,threading
from pathlib import Path
from experiments.p010.common import read,dump,sha,digest,verify,utc
from experiments.p010.cue_benchmark_group import KEY,HARD_SECONDS,forecast,check_rosters
from experiments.p010.cue_benchmark_roster import RUNS


def keys(spec):
    result=[KEY+'/'+x for x in ('dispatch','claim','terminal')]
    for run in RUNS:
        result.append(KEY+'/'+run+'/cell')
        count=spec['new_outputs'][run]
        result.extend(KEY+'/'+run+'/'+kind+f'/{offset:05d}'
            for offset in range(0,count,256) for kind in ('batch','batch_done'))
        parent=spec['model_bindings'][run]['parent']
        if parent is not None:result.append(parent['terminal_key'])
    if len(result)!=len(set(result)):raise ValueError('Duplicate named original records')
    return result


def records(a):
    import modal
    receipt,export,out=map(Path,(a.receipt,a.export,a.out));spec=read(a.spec)
    env=read(receipt/'RESULT.json');collected=read(export/'COMPLETED.json')
    if env['status']!='completed' or collected['provider_stopped'] is not True:
        raise ValueError('Original complete result and actual STOPPED0 required')
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),keys=keys(spec),spec_sha256=sha(a.spec),no_retry=True))
    timer=threading.Timer(1200,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False);values={}
        for i,k in enumerate(keys(spec)):
            value=store.get(k)
            if value is None:raise ValueError('Missing original named record '+k)
            values[k]=value;dump(out/'confirmed'/f'{i:04d}.json',dict(key=k,value=value))
        dump(out/'RECORDS.json',values)
        dump(out/'COMPLETED.json',dict(utc=utc(),records_sha256=sha(out/'RECORDS.json'),
            original_receipt_sha256=sha(receipt/'RESULT.json'),provider_sha256=sha(export/'PROVIDER_PRIVATE.json'),new_model_calls=0))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_preserved=True,whole_retry=False));raise
    finally:timer.cancel()


def audit(a):
    from transformers import AutoTokenizer
    from src.sft_data import read_jsonl
    from experiments.p010.cue_benchmark_payload import replay
    from experiments.p010.tier3_dispatch import fixed_review,validate_a4
    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    spec=read(a.spec);receipt,export,inputs,out=map(Path,(a.receipt,a.export,a.inputs,a.out))
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),spec_sha256=sha(a.spec),local_seconds=7200,
        no_training=True,no_symbolic_scoring=True,no_old_raw_decode=True,no_binary_reload=True))
    timer=threading.Timer(7200,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        env,sent,local=[read(receipt/n) for n in ('RESULT.json','SUBMITTED.json','INTENT.json')]
        root=export/'evidence';original=read(root/'INTENT.json')
        collected=read(export/'COMPLETED.json');provider=read(export/'PROVIDER_PRIVATE.json')
        rec=read(Path(a.records)/'COMPLETED.json');ledger=read(Path(a.records)/'RECORDS.json')
        if (env['status']!='completed' or sent['run']!='benchmark_group_r1' or local['run']!=sent['run']
                or collected['original_result_sha256']!=sha(receipt/'RESULT.json') or collected['artifact']!=env['artifact']
                or collected['provider_stopped'] is not True or provider['app_id']!=sent['app_id']
                or rec['original_receipt_sha256']!=sha(receipt/'RESULT.json')
                or rec['provider_sha256']!=sha(export/'PROVIDER_PRIVATE.json')
                or rec['records_sha256']!=sha(Path(a.records)/'RECORDS.json') or set(ledger)!=set(keys(spec))
                or ledger[KEY+'/dispatch']!=local or ledger[KEY+'/terminal']!=env or ledger[KEY+'/claim']!=original['claim']
                or original['execution']!=local['execution'] or original['claim']['execution']!=local['execution']
                or original['claim']['epoch']!=original['worker_start_epoch']
                or original['source_files']!=spec['source_files'] or original['input_files']!=spec['input_files']
                or original['selection_sha256']!=spec['selection_sha256'] or original['reviews']!=local['reviews']
                or original['prior_I_reserved_usd']!=local['budget']['prior_reserved_usd']
                or abs(original['hard_deadline_epoch']-original['worker_start_epoch']-HARD_SECONDS)>.001
                or datetime.datetime.fromisoformat(env['finished_utc']).timestamp()>original['hard_deadline_epoch']
                or not 0<env['seconds_including_pack']<=HARD_SECONDS or env['result']!=read(root/'RESULT.json')):
            raise ValueError('Original full group/source/claim/timing/provider binding differs')
        validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
        runtime,selection,results=[read(p) for p in (a.runtime_review,a.selection_review,a.actual_results_review)]
        clean=[fixed_review(x) for x in (runtime,selection,results)];a4=read(a.a4_report);validate_a4(a4,results)
        if (runtime.get('scope')!=spec['runtime_review_scope'] or runtime.get('spec_sha256')!=sha(a.spec)
                or runtime.get('source_files')!=spec['source_files']
                or selection.get('scope')!='p010-C6-complete-search-selection-A3'
                or selection.get('target_commit')!=spec['selection_binding']['target_commit']
                or selection.get('selection_sha256')!=spec['selection_sha256']
                or local['reviews']!=dict(runtime_A2=clean[0],selection_A3=clean[1],actual_results_A3=clean[2],A4=a4)):
            raise ValueError('True exact actual selection and runtime/result reviews differ')
        for name,h in {**spec['source_files'],**spec['verification_source_files']}.items():
            if sha(name)!=h:raise ValueError('Original exact source changed: '+name)
        verify(inputs,spec['input_files']);artifact=env['artifact']
        if (any(k.endswith(('.pt','.safetensors')) for k in artifact['all_files'])
                or read(root/'COMPACT_MEMBERS.json')!=artifact['compact_members']
                or sha(export/'evidence.tar.gz')!=artifact['tar_sha256']):
            raise ValueError('Unplanned training/model archive or changed original bytes')
        verify(root,artifact['compact_members'])
        if sha(a.math_gold)!=spec['math_gold_sha256'] or sha(a.gsm_gold)!=spec['gsm_gold_sha256']:
            raise ValueError('Original full gold inputs differ')
        golds={task:{x['problem_id']:x for x in read_jsonl(path)} for task,path in [('math',a.math_gold),('gsm',a.gsm_gold)]}
        for name,h in spec['local_tokenizer_files'].items():
            if sha(Path(a.tokenizer)/name)!=h:raise ValueError('Original tokenizer changed')
        tokenizer=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True)
        if tokenizer.eos_token_id!=151643:raise ValueError('Original Qwen EOS differs')
        rosters={run:read(inputs/(run+'.json')) for run in RUNS};check_rosters(rosters)
        before=read(root/'BEFORE_GROUP_FORECAST.json');prior=original['prior_I_reserved_usd']
        if before!=forecast(before['elapsed_seconds'],0,[],spec['observed_batch_seconds'],prior):
            raise ValueError('Original before-group arithmetic differs')
        times=[];summaries={}
        for run in RUNS:
            cell=root/'cells'/run;roster=rosters[run];binding=spec['model_bindings'][run]
            expected=dict(run=run,claim=original['claim'],roster_sha256=sha(inputs/(run+'.json')),
                original_model_binding_sha256=digest(binding),prior_completed_batches=len(times))
            if ledger[KEY+'/'+run+'/cell']!=expected or read(root/'cell_intents'/(run+'.json'))!=expected:
                raise ValueError('Original cell identity differs')
            parent=binding['parent']
            if parent is not None and ledger[parent['terminal_key']]!=parent['terminal']:
                raise ValueError('Original completed student parent changed')
            if read(cell/'MODEL_REUSE_PROOF.json')!=dict(run=run,model_files=binding['files'],parent=parent,
                    new_training_updates=0,new_checkpoint_loads=0,new_merge_operations=0):
                raise ValueError('Original persisted model proof differs')
            exit_proof=read(root/'child_exits'/(run+'.json'))
            if exit_proof['exitcode']!=0 or exit_proof['joined_before_next_model'] is not True:
                raise ValueError('Owned model child did not exit before next cell')
            first=read(cell/'BEFORE_MODEL_FORECAST.json')
            if first!=forecast(first['elapsed_seconds'],len(times),times,spec['observed_batch_seconds'],prior):
                raise ValueError('Whole-group inherited batch timing differs')
            values={};cell_times=[]
            for offset in range(0,roster['new_outputs'],256):
                name=f'{offset:05d}.json';f=read(cell/'batch_forecasts'/name)
                values[name]=forecast(f['elapsed_seconds'],len(times),times,spec['observed_batch_seconds'],prior)
                ack=read(cell/'batch_acks'/name);times.append(ack['seconds']);cell_times.append(ack['seconds'])
            data=replay(cell,roster,ledger,tokenizer,golds[roster['task']],values,out/run,KEY+'/'+run)
            actual=read(cell/'RESULT.json')
            if (actual['batch_seconds']!=cell_times or actual['total_completed_batches']!=len(times)
                    or env['result']['cells'][run]!=actual or actual['new_outputs']!=roster['new_outputs']):
                raise ValueError('Original complete cell timing/result differs')
            dump(out/run/'DECODED_ROWS.json',data.pop('decoded'));dump(out/run/'SCORING_ROWS.json',data.pop('scoring'))
            summaries[run]=dict(**data,decoded_sha256=sha(out/run/'DECODED_ROWS.json'),scoring_sha256=sha(out/run/'SCORING_ROWS.json'))
        if len(times)!=85 or env['result']['batch_seconds']!=times or env['result']['new_outputs']!=21371:
            raise ValueError('All and only original complete85 batches required')
        proof=dict(passed=True,utc=utc(),spec_sha256=sha(a.spec),cells=summaries,new_outputs=21371,
            original_receipt_sha256=sha(receipt/'RESULT.json'),selection_sha256=spec['selection_sha256'],
            source_files=spec['source_files'],verification_source_files=spec['verification_source_files'],
            input_files=spec['input_files'],reviews=local['reviews'],technical_unknown=0,
            new_training_updates=0,new_symbolic_scoring=0,old_raw_decodes=0,old_binary_loads=0,independent_A3_pending=True)
        dump(out/'COMPLETED.json',proof);return proof
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('records')
    for n in ('spec','receipt','export','out'):q.add_argument('--'+n,required=True)
    q=sub.add_parser('audit')
    for n in ('spec','receipt','export','records','inputs','tokenizer','math-gold','gsm-gold','runtime-review','selection-review','actual-results-review','a4-report','out'):
        q.add_argument('--'+n,required=True)
    a=p.parse_args();value=records(a) if a.action=='records' else audit(a)
    print(json.dumps(None if value is None else {k:v for k,v in value.items() if k not in ('source_files','verification_source_files','input_files','reviews')}))
