"""One complete C6 raw/probability audit, then separate gold-free selection."""
import argparse
import datetime
import os
import threading
import time
from pathlib import Path
from experiments.p010.common import dump,read,sha,digest,verify,utc


def expire_owned_parser():
    """Stop only this job's child processes before the bounded local exit."""
    import multiprocessing
    children=multiprocessing.active_children()
    for child in children:
        if child.is_alive():child.kill()
    for child in children:child.join(timeout=1)
    os._exit(124)


def audit(a):
    from transformers import AutoTokenizer
    from experiments.p010.cue_search_evidence import record_keys,verify_raw
    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),spec_sha256=sha(a.spec),local_seconds=6000,
        new_model_calls=0,new_scoring=0,automatic_retry=False))
    timer=threading.Timer(6000,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        spec=read(a.spec);receipt=Path(a.receipt);export=Path(a.export);root=export/'evidence'
        env=read(receipt/'RESULT.json');sent=read(receipt/'SUBMITTED.json');local=read(receipt/'INTENT.json')
        original=read(root/'INTENT.json');collected=read(export/'COMPLETED.json');provider=read(export/'PROVIDER_PRIVATE.json')
        rec=read(Path(a.records)/'COMPLETED.json');ledger=read(Path(a.records)/'RECORDS.json')
        review=read(a.runtime_review)
        if (env['status']!='completed' or sent['run']!='search_r1' or local['run']!='search_r1'
                or collected['original_result_sha256']!=sha(receipt/'RESULT.json')
                or collected['artifact']!=env['artifact'] or collected['provider_stopped'] is not True
                or provider['app_id']!=sent['app_id']
                or rec['original_receipt_sha256']!=sha(receipt/'RESULT.json')
                or rec['records_sha256']!=sha(Path(a.records)/'RECORDS.json')
                or rec['provider_sha256']!=sha(export/'PROVIDER_PRIVATE.json')
                or set(ledger)!=set(record_keys()) or ledger['cue/search_r1/terminal']!=env
                or ledger['cue/search_r1/claim']!=original['claim']
                or original['claim']['epoch']!=original['worker_start_epoch']
                or original['claim']['execution']!=local['execution'] or original['execution']!=local['execution']
                or original['source_files']!=spec['source_files']
                or original['prior_I_reserved_usd']!=local['budget']['prior_reserved_usd']
                or original['approval']!=local['approval'] or original['gold_used'] is not False
                or original['correctness_used'] is not False or original['training_updates']!=0
                or abs(original['hard_deadline_epoch']-original['worker_start_epoch']-1800)>.001
                or datetime.datetime.fromisoformat(env['finished_utc']).timestamp()>original['hard_deadline_epoch']
                or not 0<env['seconds_including_pack']<=1800 or env['result']!=read(root/'RESULT.json')):
            raise ValueError('Original C6 claim/result/receipt/provider/source/timer binding differs')
        validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
        if (review['decision'] not in ('PASS','PASS-WITH-NOTES')
                or review['scope']!='p010-C6-search-input-runtime-and-selection-A2'
                or review['spec_sha256']!=sha(a.spec)
                or sha(review['local_report_file'])!=review['report_sha256']
                or local['approval']!={k:v for k,v in review.items() if k!='local_report_file'}):
            raise ValueError('Actual exact complete A2 binding required')
        for name,value in {**spec['source_files'],**spec['verification_source_files']}.items():
            if sha(name)!=value:raise ValueError('Original reviewed source changed: '+name)
        artifact=env['artifact']
        if (any(k.endswith(('.pt','.safetensors')) for k in artifact['all_files'])
                or read(root/'COMPACT_MEMBERS.json')!=artifact['compact_members']
                or sha(export/'evidence.tar.gz')!=artifact['tar_sha256']):
            raise ValueError('Original search archive differs or contains unplanned training state')
        verify(root,artifact['compact_members'])
        if sha(a.dev)!=spec['dev_input_sha256'] or original['dev_input_sha256']!=sha(a.dev):
            raise ValueError('Original gold-free dev input changed')
        dev=read(a.dev)
        if read(root/'DEV_PROMPTS.json')!=dev:raise ValueError('Original worker dev input differs')
        for name,value in spec['local_tokenizer_files'].items():
            if sha(Path(a.tokenizer)/name)!=value:raise ValueError('Original tokenizer bytes differ')
        tokenizer=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True)
        if tokenizer.eos_token_id!=151643:raise ValueError('Original base EOS differs')
        decoded,summary=verify_raw(root,dev,ledger,spec,original['prior_I_reserved_usd'],tokenizer,out)
        dump(out/'DECODED_ROWS.json',decoded)
        proof=dict(passed=True,**summary,utc=utc(),spec_sha256=sha(a.spec),
            original_receipt_sha256=sha(receipt/'RESULT.json'),original_artifact_digest=digest(artifact['all_files']),
            decoded_rows_sha256=sha(out/'DECODED_ROWS.json'),proposal_file_sha256=sha(root/'PROPOSAL.json'),
            dev_input_sha256=sha(a.dev),source_files=spec['source_files'],verification_source_files=spec['verification_source_files'],
            approval=local['approval'],selected_cue=None,independent_A3_pending=True)
        dump(out/'COMPLETED.json',proof)
        return {k:v for k,v in proof.items() if k not in ('source_files','verification_source_files','approval')}
    except BaseException as exc:
        dump(out/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),
            partial_valid_parts_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


def select_once(a):
    from experiments.p010.cue_key_process import group_rows,LOCAL_SECONDS
    from experiments.p010.cue_selection import select
    oracle=Path(a.oracle);out=Path(a.out);spec=read(a.spec);proof=read(oracle/'COMPLETED.json')
    if (proof.get('passed') is not True or proof['spec_sha256']!=sha(a.spec)
            or proof['decoded_rows_sha256']!=sha(oracle/'DECODED_ROWS.json')
            or proof['dev_input_sha256']!=sha(a.dev) or proof['proposal_file_sha256']!=sha(a.proposal)
            or proof['rows']!=10080 or proof['technical_unknown']!=0):
        raise ValueError('Complete actual original raw/probability oracle required')
    for name,value in spec['verification_source_files'].items():
        if sha(name)!=value:raise ValueError('Original exact selection source changed')
    now=time.time();cutoff=datetime.datetime(2026,10,21,19,tzinfo=datetime.timezone.utc).timestamp()
    cap=min(LOCAL_SECONDS,int(cutoff-now-30))
    scenario=1.2*(10080*8+300)
    if cap<scenario:raise TimeoutError('Full original worst-case local parsing window does not fit')
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),oracle_file_sha256=sha(oracle/'COMPLETED.json'),
        spec_sha256=sha(a.spec),local_cap_seconds=cap,deadline_epoch=now+cap,
        serial_outer_timeout_scenario_seconds=scenario,not_expected_runtime=True,
        gold_used=False,correctness_used=False,test_data_used=False,automatic_retry=False))
    timer=threading.Timer(cap+5,expire_owned_parser);timer.daemon=True;timer.start()
    try:
        rows=read(oracle/'DECODED_ROWS.json')
        observations=group_rows(rows,out/'grouping',now+cap)
        candidates=[[]]+[r['token_ids'] for r in read(a.proposal)['candidates']]
        result=select(candidates,[r['problem_id'] for r in read(a.dev)],observations)
        dump(out/'SELECTION.json',result)
        done=dict(utc=utc(),passed=True,selection_sha256=sha(out/'SELECTION.json'),
            oracle_file_sha256=sha(oracle/'COMPLETED.json'),spec_sha256=sha(a.spec),
            selected_token_ids=result['selected_token_ids'],selected_candidate=result['selected_candidate'],
            elapsed_seconds=time.time()-now,technical_unknown=0,gold_used=False,
            correctness_used=False,test_data_used=False,independent_A3_pending=True)
        dump(out/'COMPLETED.json',done)
        return done
    except BaseException as exc:
        dump(out/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),
            partial_valid_parts_preserved=True,automatic_retry=False,selection_allowed=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    import json
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    audit_parser=sub.add_parser('audit')
    for name in ('spec','receipt','export','records','dev','tokenizer','runtime-review','out'):
        audit_parser.add_argument('--'+name,required=True)
    selection_parser=sub.add_parser('select')
    for name in ('spec','oracle','proposal','dev','out'):selection_parser.add_argument('--'+name,required=True)
    args=p.parse_args();print(json.dumps(audit(args) if args.action=='audit' else select_once(args)))
