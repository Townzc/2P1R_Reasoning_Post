"""Publish-before-prepare E012 CPU release; never launches or contacts a server."""
from datetime import datetime,timezone
import argparse
import json
from pathlib import Path

from src.relation_diagnostic_execution import CONFIG,RELEASE,load_inputs,provenance
from src.relation_engineering import dump
from src.sft_data import sha256_file
from scripts.run_relation_diagnostics import check_ledger


def main():
    p = argparse.ArgumentParser(); p.add_argument('--tokenizer-dir',required=True)
    p.add_argument('--ledger',required=True); args = p.parse_args()
    if RELEASE.exists(): raise FileExistsError('Immutable E012 execution release already exists')
    source = provenance(); prepared = load_inputs(args.tokenizer_dir,require_release=False)
    cfg = prepared['cfg']; accounting = check_ledger(cfg,args.ledger,cfg['arm_order'][0],prepared)
    report = {**source,'phase':'E012','status':'prepared_execution_not_run',
        'execution_config_sha256':sha256_file(CONFIG),'data_manifest_sha256':cfg['data_manifest_sha256'],
        'tokenizer':prepared['tokenizer_record'],'initial_accounting':accounting,
        'prepared_at_utc':datetime.now(timezone.utc).isoformat(),'gpu_seconds_added':0,'model_calls':0,
        'arms':{arm:{'run_id':data['cfg']['run_id'],'train_rows':len(data['train']),
            'dev_rows':len(data['dev']),'generation_prompts':len(data['train'])+2*len(data['dev']),
            'optimizer_updates':cfg['steps'],'supervised_tokens':data['budget']['supervised_response_tokens'],
            'processed_tokens':data['budget']['processed_nonpadding_tokens'],'max_seconds':cfg['max_seconds'],
            'guard_seconds':cfg['guard_seconds']} for arm,data in prepared['arms'].items()}}
    dump(RELEASE,report)
    print(json.dumps({'status':report['status'],'gpu_seconds_added':0,'arms':report['arms']},indent=2))


if __name__=='__main__': main()
