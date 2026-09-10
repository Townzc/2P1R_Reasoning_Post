"""Inspect by default; execute only one explicit, bounded E012 stage."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from scripts.run_relation_engineering import server_preflight
from src.relation_diagnostic_execution import CONFIG,RELEASE,load_inputs,provenance
from src.relation_engineering import dump
from src.sft_data import sha256_file


def require_published(path):
    path = Path(path)
    subprocess.check_output(['git','ls-files','--error-unmatch',str(path)],stderr=subprocess.STDOUT)
    published = subprocess.check_output(['git','show',f'HEAD:{path}'])
    if hashlib.sha256(published).hexdigest()!=sha256_file(path):
        raise ValueError('Publish exact prior compact outputs before continuation')


def check_backup(run_id, directory, *, require_publication=True, receipt_path=None):
    path = Path(receipt_path) if receipt_path is not None else Path('reports')/f'{run_id}_checkpoint_backup.json'
    proof = json.loads(path.read_text()); checkpoint = json.loads((Path(directory)/'checkpoint_manifest.json').read_text())
    if proof.get('status')!='verified_independent_backup' or proof.get('run_id')!=run_id:
        raise ValueError('Previous stage needs verified independent checkpoint backup')
    if proof.get('checkpoint_manifest_sha256')!=sha256_file(Path(directory)/'checkpoint_manifest.json') or proof.get('files')!=checkpoint['files']:
        raise ValueError('Backup receipt does not match saved checkpoint files')
    if proof.get('file_count')!=len(checkpoint['files']) or proof.get('total_bytes')!=sum(v['bytes'] for v in checkpoint['files'].values()):
        raise ValueError('Incomplete independent checkpoint backup')
    if require_publication: require_published(path)


def check_ledger(cfg, path, arm, prepared, *, root=Path('runs'), prior_verifier=None, require_publication=True):
    """No writes/reservations. Old receipts stay exact; only ordered passed stages may follow."""
    path = Path(path); root = Path(root)
    if not path.is_file(): raise ValueError('Restore the current ledger; never initialize a new allowance')
    raw = path.read_bytes(); ledger = json.loads(raw)
    budget = json.loads(Path('configs/resource_budget.json').read_text())
    if ledger.get('budget_id')!=budget['budget_id'] or ledger.get('authorized_gpu_seconds')!=7200 or cfg['authorized_gpu_seconds']!=7200 or budget['authorized_gpu_seconds']!=7200 or budget['gpus']!=1:
        raise ValueError('Original single-GPU authorization changed')
    jobs = ledger['jobs']; index = cfg['arm_order'].index(arm); base_n = cfg['expected_prior_jobs']
    if len(jobs)!=base_n+index or len(cfg['base_receipts'])!=base_n:
        raise ValueError('Stale ledger, unexpected jobs or out-of-order stage')
    if len({r['run_id'] for r in jobs})!=len(jobs) or any(r['status']=='reserved' or type(r['charged_seconds']) is not int or r['charged_seconds']<0 for r in jobs):
        raise ValueError('Duplicate jobs, invalid charges or unresolved reservation')
    for actual, anchor in zip(jobs[:base_n],cfg['base_receipts']):
        receipt = root/anchor['run_id']/'resource_receipt.json'
        if sha256_file(receipt)!=anchor['receipt_sha256'] or actual!=json.loads(receipt.read_text()):
            raise ValueError('Historical receipt prefix changed')
    if sum(r['charged_seconds'] for r in jobs[:base_n])!=cfg['expected_prior_used_seconds']:
        raise ValueError('Historical GPU usage changed')
    current_hash = hashlib.sha256(raw).hexdigest()
    if not index and current_hash!=cfg['expected_initial_ledger_sha256']:
        raise ValueError('Initial ledger is stale or changed')
    verified_prior = []
    for i, previous in enumerate(cfg['arm_order'][:index]):
        rid = cfg['run_ids'][previous]; directory = root/rid; receipt = directory/'resource_receipt.json'
        if jobs[base_n+i]['run_id']!=rid or jobs[base_n+i]!=json.loads(receipt.read_text()):
            raise ValueError('Preceding stage receipt chain differs')
        previous_receipt = jobs[base_n+i]
        if previous_receipt['status']!='completed' or previous_receipt.get('exit_code')!=0 or previous_receipt.get('max_seconds')!=cfg['max_seconds'] or not 0<previous_receipt['charged_seconds']<=cfg['max_seconds']+cfg['guard_seconds']:
            raise ValueError('Preceding job did not complete within its resource cap')
        if prior_verifier is None:
            from scripts.audit_relation_diagnostic_outputs import audit
            proof = audit(directory,prepared,previous)
        else: proof = prior_verifier(directory,prepared,previous)
        if not proof['verified_compact_outputs'] or not proof['engineering_gate']['passed']:
            raise ValueError('Previous training gate did not pass; stop the ladder')
        if require_publication:
            for name in proof['files_sha256']: require_published(directory/name)
            check_backup(rid,directory)
        verified_prior.append({'arm':previous,'verified_compact_outputs':True,'gate_passed':True})
    used = sum(r['charged_seconds'] for r in jobs); remaining = 7200-used
    phase_need = (len(cfg['arm_order'])-index)*(cfg['max_seconds']+cfg['guard_seconds'])
    if cfg['guard_seconds']!=15 or remaining<phase_need:
        raise ValueError('All remaining conditional caps and guards must fit; no shortened jobs')
    rid = cfg['run_ids'][arm]
    if rid in {r['run_id'] for r in jobs} or (root/rid).exists(): raise FileExistsError('Immutable run identity already used')
    return {'ledger_sha256':current_hash,'used_seconds':used,'remaining_seconds':remaining,
            'prior_receipts':len(jobs),'reservations':0,'current_job_max_reservation_seconds':cfg['max_seconds']+15,
            'remaining_ladder_max_reservation_seconds':phase_need,'verified_prior_stages':verified_prior}


def inspection(prepared, arm, accounting):
    data = prepared['arms'][arm]
    return {'phase':'E012','status':'not_run','arm':arm,'run_id':data['cfg']['run_id'],
        'accounting':accounting,'data_manifest_sha256':data['cfg']['data_manifest_sha256'],
        'execution_release_sha256':sha256_file(RELEASE),'model_execution_performed':False,
        'train_rows':len(data['train']),'dev_rows':len(data['dev']),
        'generation_prompts':len(data['train'])+2*len(data['dev']),
        'optimizer_updates':data['cfg']['steps'],'supervised_tokens':data['budget']['supervised_response_tokens'],
        'processed_tokens':data['budget']['processed_nonpadding_tokens']}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--arm',choices=['single_step','given_route','fixed_reference'],default='single_step')
    p.add_argument('--ledger',default='.local/resource_ledger.json'); p.add_argument('--tokenizer-dir',required=True)
    p.add_argument('--expected-published-commit',help='Current GitHub commit independently checked before server synchronization')
    p.add_argument('--execute',action='store_true'); args = p.parse_args()
    source = provenance(include_release=True); prepared = load_inputs(args.tokenizer_dir); cfg = prepared['cfg']
    accounting = check_ledger(cfg,args.ledger,args.arm,prepared)
    report = {**inspection(prepared,args.arm,accounting),'source_commit':source['source_commit'],'execute_requested':args.execute}
    print(json.dumps(report,indent=2),flush=True)
    if not args.execute: return 0
    if args.expected_published_commit!=source['source_commit']:
        raise ValueError('Supply the independently verified current published commit; synchronize first')
    server = server_preflight(prepared['arms'][args.arm]['cfg'],Path(args.tokenizer_dir))
    Path('.local').mkdir(exist_ok=True)
    path = Path('.local')/f"e012_preflight_{args.arm}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.json"
    dump(path,{**report,'server':server,'checked_at_utc':datetime.now(timezone.utc).isoformat()})
    # Re-read every prior receipt; the watchdog then rechecks this exact hash under lock.
    current = check_ledger(cfg,args.ledger,args.arm,prepared)
    rid = cfg['run_ids'][args.arm]
    command = [sys.executable,'-m','scripts.run_bounded','--run-id',rid,'--max-seconds',str(cfg['max_seconds']),
        '--ledger',args.ledger,'--expected-ledger-sha256',current['ledger_sha256'],'--require-full-cap','--',
        sys.executable,'-m','src.relation_diagnostic_training','--arm',args.arm,'--snapshot',args.tokenizer_dir,'--preflight',str(path)]
    code = subprocess.call(command)
    if code: return code
    from scripts.audit_relation_diagnostic_outputs import audit
    verified = audit(Path('runs')/rid,prepared,args.arm)
    dump(Path('runs')/rid/'outputs_verification.json',verified)
    print(json.dumps({'stage_completed':True,'engineering_gate':verified['engineering_gate'],
                     'next_stage_auto_launched':False}),flush=True)
    return 0


if __name__=='__main__': sys.exit(main())
