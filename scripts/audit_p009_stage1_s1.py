"""One full S1 state/raw oracle. Independent frozen symbolic scoring follows.

The separate exclusive output directory preserves attempts and all partial data;
there is no full-job retry path and this oracle never invokes math-verify.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from src.sft_data import read_jsonl
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009.stage1_s1_funded_binding import (
    CAMPAIGN, FIRST_PAIR, validate, intent, marker, dispatch_key, logical_key,
)
from experiments.learning_regime_p009.stage1_s1_funded_evidence import (
    verify_training_payload, verify_endpoint_payload,
)


def lineage(args):
    root = Path(args.root); inputs = Path(args.inputs); spec = read(args.admission)
    env = read(args.receipt); ledger = read(args.ledger); provider = read(args.provider)
    sent = read(root/'intent.json'); run = sent['run_id']; cap = validate(spec,sent['plan'],run,sent['release'])
    if sent['spec'] != spec or run != args.run: raise ValueError('Original spec/run differs')
    for path,h in spec['source_files'].items():
        if sha(path) != h: raise ValueError('Exact reviewed source changed')
    pre = 'midpoint/'+CAMPAIGN+'/'; claim = ledger[pre+'claim/'+run]; terminal = ledger[pre+'terminal/'+run]
    if (terminal != env['receipt'] or terminal['status'] != 'completed'
        or terminal['run_id'] != run or claim['run_id'] != run
        or claim['reserved_cents'] != 655 or terminal['actual_cost_cents'] != 655
        or terminal['attempt_id'] != claim['attempt_id']
        or ledger[pre+'attempt/'+run+'/'+claim['attempt_id']] != claim
        or terminal['claim_sha256'] != digest(claim)
        or terminal['evidence_sha256'] != digest(env['artifact_manifest'])
        or ledger[pre+'intent/'+run] != intent(spec,run)
        or claim['intent_sha256'] != digest(intent(spec,run)) or claim['plan_sha256'] != digest(sent['plan'])):
        raise ValueError('Original full claim/intent/terminal/envelope differs')
    expected = marker(spec,run,sent['release'])
    if expected['provider_app_id'] != args.app_id or any(ledger.get(k) != expected for k in (dispatch_key(run),logical_key(run))):
        raise ValueError('Permanent original dispatch fences differ')
    if any(ledger.get(k) != v for k,v in spec['required_records'].items()):
        raise ValueError('Actual completed/failed dependencies changed')
    first = [] if run in FIRST_PAIR else sent['release']['futility_review']['first_pair_app_ids']
    if run not in FIRST_PAIR and any(ledger.get(k) != v for k,v in sent['release']['futility_review']['required_terminal_records'].items()):
        raise ValueError('Actual first-pair evidence changed')
    apps = list(dict.fromkeys(spec['required_stopped_app_ids']+first+[args.app_id]))
    if provider['app_ids'] != apps or provider['state'] != 'stopped' or provider['owned_container_ids']:
        raise ValueError('Original dependent apps and actual app must be STOPPED0')
    validate_stopped_apps(apps,provider['original_app_info'],provider['owned_containers'])
    if (abs(sent['hard_deadline_epoch']-sent['worker_started_epoch']-4500) > .001
        or terminal['finished_epoch'] > sent['hard_deadline_epoch']):
        raise ValueError('Original whole-worker cap exceeded')
    files = read(root/'artifact_manifest.json')
    if files != env['artifact_manifest']: raise ValueError('Original artifact roster differs')
    if {k for k in files if k.endswith('.pt')} != {'checkpoint_1024/state.pt'}:
        raise ValueError('Only the original terminal1024 checkpoint is allowed')
    verify(root,files); verify(inputs,spec['inputs'])
    result = read(root/'result.json')
    if result != env['result'] or any(result.get(k) != v for k,v in
            dict(new_outputs=500,updates=1024,targets=2097148,reserved_cents=655).items()):
        raise ValueError('Full original scientific result/dose differs')
    return spec, sent, env, ledger, terminal


def audit(args):
    out = Path(args.out); out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(run_id=args.run,utc=datetime.now(timezone.utc).isoformat(),
                              automatic_retry=False, full_job_repetition_forbidden=True))
    try:
        spec,sent,env,ledger,terminal = lineage(args)
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True,use_fast=True)
        for name,item in spec['base']['files'].items():
            if name in ('tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','config.json'):
                if sha(Path(args.tokenizer)/name) != item['sha256']: raise ValueError('Original tokenizer/config differs')
        if sha(args.gold) != spec['gold_file_sha256']: raise ValueError('Frozen original MATH gold file differs')
        gold = {row['problem_id']:row for row in read_jsonl(args.gold)}
        trained = verify_training_payload(args.root,args.inputs,spec,args.run,terminal,ledger,tokenizer)
        endpoint = read(Path(args.inputs)/'S1_ENDPOINT.json')
        decoded = verify_endpoint_payload(args.root,endpoint,spec,args.run,terminal,trained,tokenizer,gold)
        dump(out/'DECODED_ROWS.json',decoded['decoded']); dump(out/'SCORING_ROWS.json',decoded['scoring_rows'])
        value = dict(passed=True,run_id=args.run,updates_verified=1024,targets_verified=2097148,
            state_sha256=trained['state_sha256'],artifact_digest=digest(env['artifact_manifest']),
            original_intent_file_sha256=sha(Path(args.root)/'intent.json'),
            original_receipt_file_sha256=sha(args.receipt),original_ledger_file_sha256=sha(args.ledger),
            original_provider_file_sha256=sha(args.provider),spec_sha256=digest(spec),source_files=spec['source_files'],
            outputs_decoded=500,technical_unknown=0,logical_stops=decoded['logical_stops'],
            decoded_file_sha256=sha(out/'DECODED_ROWS.json'),scoring_rows_file_sha256=sha(out/'SCORING_ROWS.json'),
            actual_runtime_report_sha256=sent['release']['runtime_review']['report_sha256'],
            actual_NC_A4_report_sha256=sent['release']['NC_A4_review']['report_sha256'],
            full_runtime_lineage_admission_checked=True,symbolic_scoring_performed=False,
            scientific_G1_admitted=False,external_A4_pending=True,utc=datetime.now(timezone.utc).isoformat())
        dump(out/'COMPLETED.json',value); return value
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),automatic_retry=False,
                                   partial_evidence_preserved=True))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root','inputs','admission','run','receipt','ledger','provider','app-id','tokenizer','gold','out'):
        parser.add_argument('--'+name,required=True)
    value = audit(parser.parse_args()); print(json.dumps({k:v for k,v in value.items() if k!='source_files'}))
