"""One independent original-token endpoint proof, reusing completed training proof."""
import argparse,json
from pathlib import Path
from datetime import datetime
from experiments.p010.common import read,dump,sha,digest,verify,utc
from experiments.p010.e4_endpoint_contract import validate_parent
from experiments.p010.e4_endpoint_evidence import record_keys,verify_endpoint,GOLD_SHA256
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps


def audit(a):
    from transformers import AutoTokenizer
    from src.sft_data import read_jsonl
    spec=read(a.spec);receipt=Path(a.receipt);export=Path(a.export);root=export/'evidence';out=Path(a.out)
    out.mkdir(parents=True,exist_ok=False);dump(out/'INTENT.json',dict(utc=utc(),run=a.run,spec_sha256=sha(a.spec),new_training=0,
        repeated_binary_loading=False,new_generation=0,automatic_retry=False))
    try:
        env=read(receipt/'RESULT.json');sent=read(receipt/'SUBMITTED.json');local=read(receipt/'INTENT.json');original=read(root/'INTENT.json')
        collected=read(export/'COMPLETED.json');provider=read(export/'PROVIDER_PRIVATE.json');rec=read(Path(a.records)/'COMPLETED.json');ledger=read(Path(a.records)/'RECORDS.json')
        child='e4_endpoint_only/'+a.run;parent='e4/'+a.run;training=read(a.training_proof)
        if (env['status']!='completed' or sent['run']!=a.run or local['run']!=a.run or original['run']!=a.run
                or collected['original_result_sha256']!=sha(receipt/'RESULT.json') or collected['artifact']!=env['artifact']
                or collected['provider_stopped'] is not True or provider['app_id']!=sent['app_id']
                or rec['original_receipt_sha256']!=sha(receipt/'RESULT.json') or rec['records_sha256']!=sha(Path(a.records)/'RECORDS.json')
                or set(ledger)!=set(record_keys(a.run)) or ledger[child+'/terminal']!=env
                or sha(a.training_proof)!=spec['parents'][a.run]['proof_file_sha256']
                or digest(training)!=spec['parents'][a.run]['proof_canonical_sha256'] or read(root/'ORIGINAL_TRAINING_PROOF.json')!=training):
            raise ValueError('Actual child/parent/collection/ledger proof differs')
        validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
        validate_parent(training,a.run,ledger[parent+'/claim'],ledger[parent+'/terminal'],
            [ledger[parent+'/'+kind+f'/{i:04d}'] for i in range(0,1319,256) for kind in ('eval','eval_done')],[])
        if (ledger[parent+'/endpoint_only_successor']!=ledger[child+'/claim'] or ledger[child+'/claim']!=original['claim']
                or original['claim']['original_failed_claim']!=training['original_claim']
                or original['claim']['original_state_sha256']!=training['state_sha256']
                or original['claim']['execution']!=local['execution'] or original['execution']!=local['execution']
                or original['source_files']!=spec['source_files'] or original['original_failed_terminal']!=training['original_failed_terminal']
                or original['prior_T_reserved_usd']!=local['budget']['prior_reserved_usd']
                or original['approvals']!=local['approvals'] or original['claim']['epoch']!=original['worker_start_epoch']
                or abs(original['hard_deadline_epoch']-original['worker_start_epoch']-1200)>.001
                or datetime.fromisoformat(env['finished_utc']).timestamp()>original['hard_deadline_epoch']
                or not 0<env['seconds_including_pack']<=1200 or env['result']!=read(root/'RESULT.json')
                or env['result']['original_training_proof_sha256']!=digest(training)):
            raise ValueError('Original scope, owner/audit identity, failed parent or timer differs')
        owner=read(a.owner);review=read(a.runtime_review)
        if (owner['decision']!='APPROVED' or owner['scope']!='p010-E4-completed-state-endpoint-only-exception'
                or owner['spec_sha256']!=sha(a.spec) or owner['cells']!=sorted(spec['parents'])
                or owner['maximum_new_reserved_usd']!='5.04' or not owner['direct_user_message']
                or review['decision'] not in ('PASS','PASS-WITH-NOTES') or review['scope']!='p010-C8-endpoint-only-repair-A2'
                or review['spec_sha256']!=sha(a.spec) or sha(review['local_report_file'])!=review['report_sha256']
                or local['approvals']!=dict(owner={k:v for k,v in owner.items() if not k.startswith('local_')},audit={k:v for k,v in review.items() if k!='local_report_file'})):
            raise ValueError('Real owner exception and exact A2 must remain bound')
        for name,value in spec['source_files'].items():
            if sha(name)!=value:raise ValueError('Original reviewed source changed')
        files=env['artifact']['all_files'];compact=env['artifact']['compact_members']
        if (any(k.endswith(('.pt','.safetensors')) for k in files) or read(root/'COMPACT_MEMBERS.json')!=compact
                or sha(export/'evidence.tar.gz')!=env['artifact']['tar_sha256']):raise ValueError('Unexpected child training state or changed archive')
        verify(root,compact)
        if sha(a.endpoint)!=spec['endpoint_file_sha256'] or sha(a.gold)!=GOLD_SHA256:raise ValueError('Original endpoint or gold changed')
        parent_spec=read('reports/p010_20261019/e4_runtime_v1/SPEC.json')
        if sha('reports/p010_20261019/e4_runtime_v1/SPEC.json')!=spec['original_spec_sha256']:raise ValueError('Original E4 spec changed')
        tok=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True)
        for name,item in parent_spec['model']['files'].items():
            if name in ('tokenizer.json','tokenizer_config.json','config.json','special_tokens_map.json') and sha(Path(a.tokenizer)/name)!=item['sha256']:
                raise ValueError('Original OLMo tokenizer/config changed')
        gold_rows=read_jsonl(a.gold);gold={x['problem_id']:x for x in gold_rows}
        if len(gold_rows)!=1319:raise ValueError('Full unique gold roster required')
        value=verify_endpoint(root,read(a.endpoint),ledger,a.run,original['prior_T_reserved_usd'],tok,gold,parent_spec['model']['vocab_size'],out)
        dump(out/'DECODED_ROWS.json',value.pop('decoded'))
        proof=dict(passed=True,run=a.run,**value,original_training_updates=1024,original_targets=2097148,state_sha256=training['state_sha256'],
            original_failed_parent_remains_failed=True,training_proof_file_sha256=sha(a.training_proof),original_receipt_sha256=sha(receipt/'RESULT.json'),
            original_artifact_digest=digest(files),spec_sha256=sha(a.spec),source_files=spec['source_files'],decoded_rows_sha256=sha(out/'DECODED_ROWS.json'),
            gold_sha256=GOLD_SHA256,approvals=local['approvals'],utc=utc())
        dump(out/'COMPLETED.json',proof);return proof
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_originals_preserved=True,automatic_retry=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('spec','receipt','export','records','run','training-proof','endpoint','gold','tokenizer','owner','runtime-review','out'):p.add_argument('--'+name,required=True)
    x=audit(p.parse_args());print(json.dumps({k:v for k,v in x.items() if k not in ('source_files','approvals')}))
