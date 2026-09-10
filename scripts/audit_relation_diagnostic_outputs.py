"""Recompute E012 outputs from raw tokens and token-level measurements; no model."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

from src.relation_diagnostic_execution import (RELEASE,load_inputs,verify_source_hashes,
    account,result_metrics,score_tokens)
from src.relation_diagnostic_verifier import summarize
from src.relation_engineering import dump
from src.relation_experiment import profile
from src.sft_data import read_jsonl,sha256_file

OUTPUTS = ('run_manifest.json','preflight.json','planned_budget.json','actual_budget.json',
    'train_history.jsonl','throughput.json','base_dev.jsonl','baseline_metrics.json',
    'final_train.jsonl','final_dev.jsonl','train_reference_tokens.jsonl',
    'evaluation_metrics.json','metrics.json','checkpoint_manifest.json','resource_receipt.json','stdout.log')


def audit_predictions(path, rows, tokenizer, cfg, model_vocab_size=None, known_token_ids=None):
    predictions = read_jsonl(path); vocab = model_vocab_size if model_vocab_size is not None else len(tokenizer)
    known = frozenset(tokenizer.get_vocab().values()) if known_token_ids is None else known_token_ids
    if len(predictions)!=len(rows): raise ValueError('Missing or duplicated prediction')
    for pred,row in zip(predictions,rows):
        if any(pred.get(k)!=v for k,v in row.items()): raise ValueError('Frozen prediction identity or label changed')
        ids = pred['generated_ids']
        if not ids or len(ids)>cfg['max_new_tokens'] or any(type(x) is not int or not 0<=x<vocab for x in ids):
            raise ValueError('Invalid raw output token sequence')
        eos = ids[-1]==tokenizer.eos_token_id
        if tokenizer.eos_token_id in ids[:-1] or not eos and len(ids)!=cfg['max_new_tokens']:
            raise ValueError('Invalid EOS, padding or early termination')
        text = tokenizer.decode(ids[:-1] if eos else ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
        if text!=pred['text'] or pred['generated_tokens']!=len(ids): raise ValueError('Raw text/length differs from token stream')
        result = score_tokens(row,text,ids,eos,not eos and len(ids)==cfg['max_new_tokens'],known)
        if result!=pred['score']: raise ValueError('Saved proof or semantic line scores differ')
    return predictions


def audit(directory, prepared, arm):
    directory = Path(directory); data = prepared['arms'][arm]; cfg = data['cfg']; tok = prepared['tokenizer']
    if directory.name!=cfg['run_id']: raise ValueError('Wrong registered run identity')
    if any(not (directory/name).is_file() for name in OUTPUTS): raise ValueError('Incomplete compact outputs')
    get = lambda name:json.loads((directory/name).read_text())
    m = get('run_manifest.json')
    if m['status']!='completed' or m['steps_completed']!=cfg['steps'] or m['config']!=cfg:
        raise ValueError('Changed, failed or incomplete execution manifest')
    if m['data_manifest_sha256']!=cfg['data_manifest_sha256'] or m['execution_release_sha256']!=sha256_file(RELEASE):
        raise ValueError('Data or execution release binding changed')
    expected_sources = {**prepared['release']['source_files_sha256'],str(RELEASE):sha256_file(RELEASE)}
    if m['source_files_sha256']!=expected_sources: raise ValueError('Execution dependencies differ from release')
    verify_source_hashes(m['source_commit'],m['source_files_sha256'])
    if m['tokenizer']!=prepared['tokenizer_record'] or m['model_revision']!=prepared['tokenizer_record']['revision'] or m['model']!=prepared['tokenizer_record']['repo_id']:
        raise ValueError('Model/tokenizer identity changed')
    fixed = {'weights':'fresh_pinned_base','parameter_dtype':'float32','autocast_dtype':'bfloat16',
        'optimizer':'AdamW_foreach_false','attention':'sdpa','gradient_checkpointing':'nonreentrant',
        'tf32':False,'holdout_access':False,'scientific_treatment_comparison':False,
        'eos_token_id':tok.eos_token_id,'pad_token_id':tok.pad_token_id,
        'model_vocab_size':prepared['model_vocab_size'],'tokenizer_size':len(tok)}
    if any(m.get(k)!=v for k,v in fixed.items()): raise ValueError('Recipe or evidence scope differs')
    preflight = get('preflight.json')
    if sha256_file(directory/'preflight.json')!=m['preflight_sha256'] or preflight['source_commit']!=m['source_commit'] or preflight['arm']!=arm or preflight['server']!=m['server'] or not m['server']['model']['all_files_verified']:
        raise ValueError('Preflight binding mismatch')
    history = read_jsonl(directory/'train_history.jsonl')
    if len(history)!=cfg['steps']: raise ValueError('Wrong optimizer-update count')
    for i,row in enumerate(history):
        if row['step']!=i+1 or row['row_indices']!=data['schedule'][i]: raise ValueError('Wrong update or sample order')
        if any(row[k]!=data['budget']['per_update'][i][k] for k in ('supervised_tokens','processed_tokens')):
            raise ValueError('Wrong per-update token count')
        if any(type(row[k]) not in (float,int) or not math.isfinite(row[k]) or row[k]<0 for k in ('response_nll','grad_norm','seconds','peak_allocated_mib','peak_reserved_mib')) or row['seconds']==0:
            raise ValueError('Invalid training/profile history')
    executed = [r['row_indices'] for r in history]
    budget = account(data['train'],data['encoded'],executed,cfg['microbatch_size'])
    if budget!=data['budget'] or get('planned_budget.json')!=budget or get('actual_budget.json')!=budget:
        raise ValueError('Actual and frozen dose differ')
    if get('throughput.json')!=profile(history,cfg): raise ValueError('Profile summary differs')
    kwargs = {'model_vocab_size':prepared['model_vocab_size'],'known_token_ids':prepared['known_token_ids']}
    baseline = audit_predictions(directory/'base_dev.jsonl',data['dev'],tok,cfg,**kwargs)
    training = audit_predictions(directory/'final_train.jsonl',data['train'],tok,cfg,**kwargs)
    dev = audit_predictions(directory/'final_dev.jsonl',data['dev'],tok,cfg,**kwargs)
    if get('baseline_metrics.json')!=summarize(data['dev'],[p['score'] for p in baseline]):
        raise ValueError('Baseline summary differs')
    refs = read_jsonl(directory/'train_reference_tokens.jsonl')
    metrics = result_metrics(data,history,baseline,training,dev,refs,prepared['model_vocab_size'])
    if get('metrics.json')!=metrics or get('evaluation_metrics.json')!=metrics:
        raise ValueError('Recomputed field statistics, metrics or gate differ')
    receipt = get('resource_receipt.json')
    elapsed = receipt['elapsed_seconds']
    if type(elapsed) not in (float,int) or not math.isfinite(elapsed) or elapsed<=0:
        raise ValueError('Invalid charged wall time')
    if (receipt['run_id'],receipt['status'],receipt['exit_code'],receipt['max_seconds'])!=(cfg['run_id'],'completed',0,cfg['max_seconds']) or type(receipt['charged_seconds']) is not int or receipt['charged_seconds']!=math.ceil(elapsed) or not 0<receipt['charged_seconds']<=cfg['max_seconds']+cfg['guard_seconds']:
        raise ValueError('Bounded execution receipt mismatch')
    checkpoint = get('checkpoint_manifest.json'); files = checkpoint['files']
    if checkpoint['kind']!='model_weights_only_not_optimizer_or_rng_resume' or not any(n.endswith('.safetensors') for n in files):
        raise ValueError('Missing final checkpoint manifest')
    for name,item in files.items():
        if Path(name).name!=name or type(item['bytes']) is not int or item['bytes']<=0 or not re.fullmatch('[0-9a-f]{64}',item['sha256']):
            raise ValueError('Malformed checkpoint file manifest')
    return {'phase':'E012','arm':arm,'verified_compact_outputs':True,
        'predictions_rechecked':len(baseline)+len(training)+len(dev),'updates_reconciled':len(history),
        'reference_rows_rechecked':len(refs),'charged_seconds':receipt['charged_seconds'],
        'engineering_gate':metrics['engineering_gate'],'metrics':metrics,
        'teacher_forced_audit_scope':'all_saved_token_alignment_top1_CE_consistency_and_aggregates_not_independent_logit_reexecution',
        'checkpoint_backup_verification':'separate_independent_file_hash_verification_required',
        'files_sha256':{name:sha256_file(directory/name) for name in OUTPUTS}}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--run-dir',required=True); p.add_argument('--arm',required=True)
    p.add_argument('--tokenizer-dir',required=True); p.add_argument('--out',required=True); args = p.parse_args()
    if Path(args.out).exists(): raise FileExistsError('Immutable audit receipt exists')
    prepared = load_inputs(args.tokenizer_dir); result = audit(args.run_dir,prepared,args.arm)
    dump(args.out,result)
    print(json.dumps({k:result[k] for k in ('verified_compact_outputs','predictions_rechecked','engineering_gate')}))


if __name__=='__main__': main()
