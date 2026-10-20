"""One full raw/source/restore proof for the new S1 sample-only evaluations."""
import argparse,datetime,json,os,threading
from pathlib import Path
from experiments.p010.common import dump,read,sha,digest,verify,utc


def audit(a):
    from transformers import AutoTokenizer
    from src.sft_data import read_jsonl
    from experiments.p010.existing_samples_evidence import record_keys,verify_samples,GOLD_SHA256,SCORER_SHA256
    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),run=a.run,spec_sha256=sha(a.spec),local_seconds=6000,
        new_model_calls=0,new_symbolic_scoring=0,repeated_binary_loading=False,automatic_retry=False))
    timer=threading.Timer(6000,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        spec=read(a.spec);parent=spec['parents'][a.run];receipt=Path(a.receipt);export=Path(a.export);root=export/'evidence'
        env=read(receipt/'RESULT.json');sent=read(receipt/'SUBMITTED.json');local=read(receipt/'INTENT.json')
        original=read(root/'INTENT.json');collected=read(export/'COMPLETED.json');provider=read(export/'PROVIDER_PRIVATE.json')
        rec=read(Path(a.records)/'COMPLETED.json');ledger=read(Path(a.records)/'RECORDS.json');key='existing_s1_samples/'+a.run
        review=read(a.runtime_review)
        if (env['status']!='completed' or sent['run']!=a.run or local['run']!=a.run or original['run']!=a.run
                or collected['original_result_sha256']!=sha(receipt/'RESULT.json')
                or collected['artifact']!=env['artifact'] or collected['provider_stopped'] is not True
                or provider['app_id']!=sent['app_id'] or rec['original_receipt_sha256']!=sha(receipt/'RESULT.json')
                or rec['records_sha256']!=sha(Path(a.records)/'RECORDS.json')
                or rec['provider_sha256']!=sha(export/'PROVIDER_PRIVATE.json')
                or rec['original_terminal']!=parent['terminal'] or set(ledger)!=set(record_keys(a.run))
                or ledger[key+'/terminal']!=env or ledger[key+'/claim']!=original['claim']
                or original['claim']['epoch']!=original['worker_start_epoch']
                or original['claim']['execution']!=local['execution'] or original['execution']!=local['execution']
                or original['source_files']!=spec['source_files']
                or original['prior_T_reserved_usd']!=local['budget']['prior_reserved_usd']
                or original['approval']!=local['approval'] or original['original_parent_terminal']!=parent['terminal']
                or original['original_state_sha256']!=parent['proof']['checkpoint']['sha256']
                or original['new_training_updates']!=0
                or abs(original['hard_deadline_epoch']-original['worker_start_epoch']-1200)>.001
                or datetime.datetime.fromisoformat(env['finished_utc']).timestamp()>original['hard_deadline_epoch']
                or not 0<env['seconds_including_pack']<=1200 or env['result']!=read(root/'RESULT.json')):
            raise ValueError('Original sample/parent/claim/receipt/provider/source/timer binding differs')
        validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
        if (review['decision'] not in ('PASS','PASS-WITH-NOTES')
                or review['scope']!='p010-C5-existing-S1-sample-only-A2'
                or review['spec_sha256']!=sha(a.spec) or sha(review['local_report_file'])!=review['report_sha256']
                or local['approval']!={k:v for k,v in review.items() if k!='local_report_file'}):
            raise ValueError('Actual exact original-state/input/runtime A2 required')
        for name,value in {**spec['source_files'],**spec['verification_source_files']}.items():
            if sha(name)!=value:raise ValueError('Original reviewed source changed: '+name)
        artifact=env['artifact'];files=artifact['all_files']
        if (any(k.endswith('.pt') for k in files)
                or {k.removeprefix('merged/'):v for k,v in files.items() if k.startswith('merged/')}!=parent['proof']['merged_files']
                or read(root/'COMPACT_MEMBERS.json')!=artifact['compact_members']
                or sha(export/'evidence.tar.gz')!=artifact['tar_sha256']):
            raise ValueError('Original sample archive/model hash differs or unplanned checkpoint exists')
        verify(root,artifact['compact_members'])
        if sha(a.endpoint)!=spec['endpoint_sha256'] or sha(a.gold)!=GOLD_SHA256:
            raise ValueError('Exact original endpoint/gold changed')
        for name,value in spec['local_tokenizer_files'].items():
            if sha(Path(a.tokenizer)/name)!=value:raise ValueError('Original tokenizer bytes differ')
        tok=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True)
        if tok.eos_token_id!=151643:raise ValueError('Original EOS differs')
        gold_rows=read_jsonl(a.gold);gold={row['problem_id']:row for row in gold_rows}
        if len(gold_rows)!=500 or len(gold)!=500:raise ValueError('All original unique500 gold rows required')
        value=verify_samples(root,read(a.endpoint),spec,a.run,ledger,tok,gold,original['prior_T_reserved_usd'],out)
        dump(out/'DECODED_ROWS.json',value.pop('decoded'));dump(out/'SCORING_ROWS.json',value.pop('scoring'))
        proof=dict(passed=True,run=a.run,**value,utc=utc(),spec_sha256=sha(a.spec),
            original_receipt_sha256=sha(receipt/'RESULT.json'),original_artifact_digest=digest(files),
            decoded_rows_sha256=sha(out/'DECODED_ROWS.json'),scoring_rows_sha256=sha(out/'SCORING_ROWS.json'),
            gold_sha256=GOLD_SHA256,scorer_sha256=SCORER_SHA256,source_files=spec['source_files'],
            verification_source_files=spec['verification_source_files'],approval=local['approval'],
            original_greedy_reused=True,independent_A3_pending=True)
        dump(out/'COMPLETED.json',proof);return proof
    except BaseException as exc:
        dump(out/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),
            partial_valid_parts_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('spec','run','receipt','export','records','endpoint','gold','tokenizer','runtime-review','out'):
        p.add_argument('--'+name,required=True)
    value=audit(p.parse_args());print(json.dumps({k:v for k,v in value.items() if k not in ('source_files','verification_source_files','approval')}))
