"""One full 21,371-row oracle over failed-parent preservation plus the new2,500."""
import argparse,datetime,json,os,threading
from pathlib import Path
from experiments.p010.common import read,dump,sha,digest,verify,utc
from experiments.p010.cue_remaining import KEY,PARENT,RUN,HARD_SECONDS,forecast
from experiments.p010.cue_benchmark_roster import RUNS


def keys(spec):
    result=[KEY+'/'+s for s in ('dispatch','claim','terminal')]
    result += [KEY+'/'+kind+f'/{first:05d}' for first in range(0,2500,256) for kind in ('batch','batch_done')]
    result += [PARENT+'/claim',PARENT+'/terminal',PARENT+'/'+RUN+'/cell']
    result += [PARENT+'/'+RUN+'/'+kind+f'/{first:05d}' for first in range(0,2500,256) for kind in ('batch','batch_done')]
    result += [spec['original_model_bindings'][run]['parent']['terminal_key'] for run in ('s1_n400_math',RUN)]
    assert len(result)==len(set(result));return result


def records(a):
    import modal
    spec=read(a.spec);receipt,export,out=map(Path,(a.receipt,a.export,a.out))
    if read(receipt/'RESULT.json')['status']!='completed' or not read(export/'COMPLETED.json')['provider_stopped']:
        raise ValueError('Real new terminal and actual STOPPED0 required')
    out.mkdir(parents=True,exist_ok=False);dump(out/'INTENT.json',dict(utc=utc(),keys=keys(spec),local_seconds=1200,no_retry=True))
    timer=threading.Timer(1200,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False);values={}
        for i,k in enumerate(keys(spec)):
            v=store.get(k);is_parent_empty=k.startswith(PARENT+'/'+RUN+'/batch')
            if (is_parent_empty and v is not None) or (not is_parent_empty and v is None):raise ValueError('Unexpected original/new record '+k)
            values[k]=v;dump(out/'confirmed'/f'{i:04d}.json',dict(key=k,value=v))
        dump(out/'RECORDS.json',values);dump(out/'COMPLETED.json',dict(utc=utc(),records_sha256=sha(out/'RECORDS.json'),receipt_sha256=sha(receipt/'RESULT.json'),provider_sha256=sha(export/'PROVIDER_PRIVATE.json')))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


def audit(a):
    from transformers import AutoTokenizer
    from src.sft_data import read_jsonl
    from experiments.p010.cue_benchmark_payload import replay
    from experiments.p010.cue_benchmark_group import forecast as original_forecast,check_rosters
    from experiments.p010.cue_remaining_binding import owner_review
    from experiments.p010.tier3_dispatch import fixed_review,validate_a4
    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    spec=read(a.spec);receipt,export,inputs,preserved,out=map(Path,(a.receipt,a.export,a.inputs,a.preservation,a.out))
    original_spec=read(spec['original_spec_file']);parent_receipt=Path(a.parent_receipt)
    if sha(spec['original_spec_file'])!=spec['original_spec_sha256']:raise ValueError('Original immutable spec changed')
    env,sent,local=[read(receipt/n) for n in ('RESULT.json','SUBMITTED.json','INTENT.json')]
    root=export/'evidence';worker=read(root/'INTENT.json');col=read(export/'COMPLETED.json');provider=read(export/'PROVIDER_PRIVATE.json')
    ledger=read(Path(a.records)/'RECORDS.json');rec=read(Path(a.records)/'COMPLETED.json')
    old=preserved/'evidence';oldworker=read(old/'INTENT.json');oldledger=read(preserved/'LEDGER.json');pres=read(preserved/'COMPLETED.json')
    oldprovider=read(preserved/'PROVIDER_PRIVATE.json');oldsent=read(parent_receipt/'SUBMITTED.json');oldlocal=read(parent_receipt/'INTENT.json')
    if (sha(preserved/'MANIFEST.json')!=spec['failed_parent_manifest_sha256'] or sha(preserved/'COMPLETED.json')!=spec['preservation_completed_sha256']
            or sha(preserved/'LEDGER.json')!=spec['failed_parent_ledger_sha256'] or not pres['provider_stopped'] or pres['owned_count']!=0
            or pres['total_saved_raw_rows']!=18871 or (preserved/'FAILED.json').exists() or (parent_receipt/'RESULT.json').exists()
            or not (parent_receipt/'ERROR.json').exists() or oldprovider['app_id']!=oldsent['app_id']
            or oldledger[PARENT+'/dispatch']!=oldlocal or oldledger[PARENT+'/claim']!=oldworker['claim']
            or oldledger[PARENT+'/terminal']!=spec['failed_parent']['terminal'] or oldledger[PARENT+'/terminal']['status']!='failed'
            or oldworker['execution']!=oldlocal['execution'] or oldworker['source_files']!=original_spec['source_files']
            or oldworker['input_files']!=original_spec['input_files'] or oldworker['reviews']!=oldlocal['reviews']):
        raise ValueError('Exact failed original parent, preservation or real lineage differs')
    validate_stopped_apps([oldsent['app_id']],oldprovider['original_info'],oldprovider['owned'])
    verify(old,read(preserved/'MANIFEST.json'))
    for s in ('claim','terminal'):
        if ledger[PARENT+'/'+s]!=oldledger[PARENT+'/'+s]:raise ValueError('Failed parent changed after preservation')
    if ledger[PARENT+'/'+RUN+'/cell']!=oldledger[PARENT+'/'+RUN+'/cell']:raise ValueError('Original reserved cell changed')
    for first in range(0,2500,256):
        for kind in ('batch','batch_done'):
            k=PARENT+'/'+RUN+'/'+kind+f'/{first:05d}'
            if oldledger[k] is not None or ledger[k] is not None:raise ValueError('Original T72 generated/attempted prefix exists')
    if (env['status']!='completed' or sent['run']!='t72_remaining_r1' or local['run']!=sent['run']
            or col['original_result_sha256']!=sha(receipt/'RESULT.json') or col['artifact']!=env['artifact'] or not col['provider_stopped']
            or provider['app_id']!=sent['app_id'] or rec['receipt_sha256']!=sha(receipt/'RESULT.json')
            or rec['provider_sha256']!=sha(export/'PROVIDER_PRIVATE.json') or rec['records_sha256']!=sha(Path(a.records)/'RECORDS.json')
            or set(ledger)!=set(keys(spec)) or ledger[KEY+'/dispatch']!=local or ledger[KEY+'/terminal']!=env or ledger[KEY+'/claim']!=worker['claim']
            or worker['execution']!=local['execution'] or worker['claim']['epoch']!=worker['worker_start_epoch']
            or worker['claim']['execution']!=local['execution'] or worker['source_files']!=spec['source_files']
            or worker['input_files']!=spec['input_files'] or worker['reviews']!=local['reviews'] or worker['budget']!=local['budget']
            or worker['failed_parent']!=spec['failed_parent'] or abs(worker['hard_deadline_epoch']-worker['worker_start_epoch']-HARD_SECONDS)>.001
            or datetime.datetime.fromisoformat(env['finished_utc']).timestamp()>worker['hard_deadline_epoch']
            or not 0<env['seconds_including_pack']<=HARD_SECONDS or env['result']!=read(root/'RESULT.json')):
        raise ValueError('Exact new result/source/claim/provider/clock binding differs')
    validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
    reviewed=owner_review(spec,read(a.owner_decision),read(a.runtime_review),a.spec)
    if any(local['reviews'][k]!=v for k,v in reviewed.items()):raise ValueError('True scoped owner/exact A2 differs')
    oruntime=read(a.original_runtime_review);fixed_review(oruntime)
    if oruntime['spec_sha256']!=spec['original_spec_sha256'] or oruntime['source_files']!=original_spec['source_files'] or oldlocal['reviews']['runtime_A2']!=fixed_review(oruntime):
        raise ValueError('Original real A2 binding differs')
    validate_a4(local['reviews']['A4'],local['reviews']['actual_results_A3'])
    if any(local['reviews'][k]!=oldlocal['reviews'][k] for k in ('selection_A3','actual_results_A3','A4')):
        raise ValueError('Original selected cue/result A3/A4 cannot change')
    for name,h in {**original_spec['source_files'],**original_spec['verification_source_files'],**spec['source_files'],**spec['verification_source_files']}.items():
        if sha(name)!=h:raise ValueError('Frozen original/new source changed '+name)
    verify(inputs,spec['input_files']);verify(root,env['artifact']['compact_members'])
    if (read(root/'COMPACT_MEMBERS.json')!=env['artifact']['compact_members'] or sha(export/'evidence.tar.gz')!=env['artifact']['tar_sha256']
            or any(n.endswith(('.pt','.safetensors')) for n in env['artifact']['all_files'])):raise ValueError('Changed original new archive or unplanned binary')
    if sha(a.math_gold)!=spec['math_gold_sha256'] or sha(a.gsm_gold)!=spec['gsm_gold_sha256']:raise ValueError('Frozen full gold inputs differ')
    golds={task:{x['problem_id']:x for x in read_jsonl(path)} for task,path in [('math',a.math_gold),('gsm',a.gsm_gold)]}
    for name,h in spec['local_tokenizer_files'].items():
        if sha(Path(a.tokenizer)/name)!=h:raise ValueError('Frozen tokenizer changed')
    tokenizer=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True)
    if tokenizer.eos_token_id!=151643:raise ValueError('Original native EOS differs')
    rosters={run:read(inputs/(run+'.json')) for run in RUNS};check_rosters(rosters)
    out.mkdir(parents=True,exist_ok=False);dump(out/'INTENT.json',dict(utc=utc(),spec_sha256=sha(a.spec),local_seconds=7200,
        first_decode_of_preserved18871=True,new_remaining_outputs=2500,no_old_no_cue_decodes=True,no_symbolic_scoring=True,no_binary_load=True))
    timer=threading.Timer(7200,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        before=read(old/'BEFORE_GROUP_FORECAST.json');prior=oldworker['prior_I_reserved_usd']
        if before!=original_forecast(before['elapsed_seconds'],0,[],original_spec['observed_batch_seconds'],prior):raise ValueError('Original group forecast differs')
        oldtimes=[];summaries={}
        for run in RUNS:
            is_new=run==RUN;cell=root if is_new else old/'cells'/run;roster=rosters[run]
            binding=spec['corrected_model_binding'] if is_new else original_spec['model_bindings'][run]
            if binding['parent'] is not None and ledger[binding['parent']['terminal_key']]!=binding['parent']['terminal']:raise ValueError('Completed model ancestor changed')
            if read(cell/'MODEL_REUSE_PROOF.json')!=dict(run=run,model_files=binding['files'],parent=binding['parent'],new_training_updates=0,new_checkpoint_loads=0,new_merge_operations=0):raise ValueError('Original persisted model hashes differ')
            if not is_new:
                expected=dict(run=run,claim=oldworker['claim'],roster_sha256=sha(inputs/(run+'.json')),original_model_binding_sha256=digest(binding),prior_completed_batches=len(oldtimes))
                if oldledger[PARENT+'/'+run+'/cell']!=expected or read(old/'cell_intents'/(run+'.json'))!=expected:raise ValueError('Original cell identity differs')
                ex=read(old/'child_exits'/(run+'.json'))
                if ex['exitcode']!=0 or ex['joined_before_next_model'] is not True:raise ValueError('Old complete child never exited')
            first=read(cell/'BEFORE_MODEL_FORECAST.json');ct=[];values={}
            expectedfirst=forecast(first['elapsed_seconds'],0,[],spec['observed_batch_seconds'],worker['budget']['prior_reserved_usd']) if is_new else original_forecast(first['elapsed_seconds'],len(oldtimes),oldtimes,original_spec['observed_batch_seconds'],prior)
            if first!=expectedfirst:raise ValueError('Actual before-model forecast differs')
            for offset in range(0,roster['new_outputs'],256):
                name=f'{offset:05d}.json';f=read(cell/'batch_forecasts'/name)
                values[name]=forecast(f['elapsed_seconds'],len(ct),ct,spec['observed_batch_seconds'],worker['budget']['prior_reserved_usd']) if is_new else original_forecast(f['elapsed_seconds'],len(oldtimes),oldtimes,original_spec['observed_batch_seconds'],prior)
                ack=read(cell/'batch_acks'/name);ct.append(ack['seconds'])
                if not is_new:oldtimes.append(ack['seconds'])
            data=replay(cell,roster,ledger if is_new else oldledger,tokenizer,golds[roster['task']],values,out/run,KEY if is_new else PARENT+'/'+run)
            result=read(cell/'RESULT.json')
            if result['batch_seconds']!=ct or result['new_outputs']!=roster['new_outputs']:raise ValueError('Complete cell result differs')
            if not is_new and result['total_completed_batches']!=len(oldtimes):raise ValueError('Original inherited time history differs')
            dump(out/run/'DECODED_ROWS.json',data.pop('decoded'));dump(out/run/'SCORING_ROWS.json',data.pop('scoring'))
            summaries[run]=dict(**data,decoded_sha256=sha(out/run/'DECODED_ROWS.json'),scoring_sha256=sha(out/run/'SCORING_ROWS.json'),origin='new_remaining_call' if is_new else 'preserved_failed_parent_complete_cell')
        if len(oldtimes)!=75 or spec['observed_batch_seconds']!=original_spec['observed_batch_seconds']+oldtimes:
            raise ValueError('All75 preserved full batches must appear in new forecast')
        if env['result']['new_outputs']!=2500 or env['result']['prior18871_regenerated']!=0:raise ValueError('Only original2500 remaining outputs')
        proof=dict(passed=True,utc=utc(),spec_sha256=sha(a.spec),cells=summaries,new_outputs=21371,
            outputs_from_failed_parent=18871,outputs_from_new_remaining_call=2500,original_parent_status='failed',
            original_failure_manifest_sha256=spec['failed_parent_manifest_sha256'],original_preserved_ledger_sha256=spec['failed_parent_ledger_sha256'],
            source_files=spec['source_files'],verification_source_files=spec['verification_source_files'],input_files=spec['input_files'],
            original_receipt_sha256=sha(receipt/'RESULT.json'),selection_sha256=spec['selection_sha256'],reviews=local['reviews'],
            technical_unknown=0,new_training_updates=0,new_symbolic_scoring=0,old_no_cue_decodes=0,old_binary_loads=0,independent_A3_pending=True)
        dump(out/'COMPLETED.json',proof);return proof
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('records')
    for n in ('spec','receipt','export','out'):q.add_argument('--'+n,required=True)
    q=sub.add_parser('audit')
    for n in ('spec','receipt','parent-receipt','preservation','export','records','inputs','tokenizer','math-gold','gsm-gold','runtime-review','owner-decision','original-runtime-review','out'):q.add_argument('--'+n,required=True)
    a=p.parse_args();records(a) if a.action=='records' else audit(a)
