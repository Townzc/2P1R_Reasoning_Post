"""Re-score saved E011 token streams and reconcile full dose; never infer not-run results."""
import argparse
import json
import math
from pathlib import Path

from scripts.audit_family_matching import verified_tokenizer
from src.relation_engineering import (CONFIG, load_frozen, score_completion, summarize, dump)
from src.relation_experiment import profile, engineering_gate
from src.sft_data import read_jsonl, sha256_file


def audit_predictions(path, rows, tokenizer, cfg):
    predictions = read_jsonl(path)
    if len(predictions) != len(rows):
        raise ValueError('Missing or duplicated prediction')
    for prediction, row in zip(predictions, rows):
        if any(prediction.get(k) != v for k, v in row.items()):
            raise ValueError('Prediction identity, prompt, view or label changed')
        ids = prediction['generated_ids']
        if not ids or len(ids) > cfg['max_new_tokens'] or any(type(i) is not int or i < 0 or i >= len(tokenizer) for i in ids):
            raise ValueError('Invalid output token sequence')
        eos = ids[-1] == tokenizer.eos_token_id
        if tokenizer.eos_token_id in ids[:-1] or not eos and len(ids) != cfg['max_new_tokens']:
            raise ValueError('Invalid termination or padded token stream')
        raw = tokenizer.decode(ids[:-1] if eos else ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
        if raw != prediction['text'] or len(ids) != prediction['generated_tokens']:
            raise ValueError('Saved text differs from raw token stream')
        score = score_completion(row, raw, eos, not eos and len(ids) == cfg['max_new_tokens'])
        if score != prediction['score']:
            raise ValueError('Saved score differs from exposed-table verification')
    return predictions


def audit(directory, tokenizer):
    cfg, data, train, evaluation, encoded, schedule, budget = load_frozen(tokenizer)
    directory = Path(directory)
    if directory.name != cfg['run_id']:
        raise ValueError('Wrong registered run identity')
    manifest = json.loads((directory/'run_manifest.json').read_text())
    if manifest['status'] != 'completed' or manifest['steps_completed'] != cfg['steps'] or manifest['config'] != cfg:
        raise ValueError('Run is absent, failed, incomplete or changed')
    if manifest['data_manifest_sha256'] != sha256_file(Path(cfg['data_dir'])/'manifest.json'):
        raise ValueError('Run input manifest differs')
    if any(manifest['source_files_sha256'].get(p) != h for p, h in data['source_files_sha256'].items()):
        raise ValueError('Execution dependencies differ from prepared source')
    for name in ('actual_budget.json', 'planned_budget.json'):
        if json.loads((directory/name).read_text()) != budget:
            raise ValueError('Token/exposure budget mismatch')
    history = read_jsonl(directory/'train_history.jsonl')
    if len(history) != cfg['steps']:
        raise ValueError('Wrong history dose')
    for i, row in enumerate(history):
        if row['step'] != i+1 or any(row[k] != budget['per_update'][i][k] for k in ('supervised_tokens', 'processed_tokens')):
            raise ValueError('Step or per-update token mismatch')
        if any(not math.isfinite(row[k]) or row[k] < 0 for k in ('seconds', 'response_nll', 'grad_norm', 'peak_allocated_mib', 'peak_reserved_mib')) or row['seconds'] == 0:
            raise ValueError('Nonfinite or invalid history')
    throughput = profile(history, cfg)
    if throughput != json.loads((directory/'throughput.json').read_text()) or not throughput['profile_complete']:
        raise ValueError('Profile differs or incomplete')
    baseline = audit_predictions(directory/'base_dev_clean.jsonl', [r for r in evaluation['dev'] if r['view'] == 'clean'], tokenizer, cfg)
    training = audit_predictions(directory/'final_train.jsonl', evaluation['train'], tokenizer, cfg)
    dev = audit_predictions(directory/'final_dev.jsonl', evaluation['dev'], tokenizer, cfg)
    metrics = json.loads((directory/'metrics.json').read_text())
    if metrics != json.loads((directory/'evaluation_metrics.json').read_text()):
        raise ValueError('Final metrics differ')
    nll = metrics['train_reference_nll']
    if nll['reference_count'] != len(encoded) or nll['supervised_tokens'] != sum(r['n_supervised'] for r in encoded) or not math.isfinite(nll['nll']) or nll['nll'] < 0 or nll['nll'] != nll['response_loss_sum']/nll['supervised_tokens']:
        raise ValueError('NLL accounting differs')
    expected = {'steps': len(history), 'train': summarize(training), 'baseline_dev_clean': summarize(baseline),
                'dev_by_view': {v: summarize([p for p in dev if p['view'] == v]) for v in cfg['dev_views']},
                'throughput': throughput,
                'engineering_gate': engineering_gate(cfg, len(history), throughput, summarize(training), nll['nll'])}
    if any(metrics[k] != v for k, v in expected.items()):
        raise ValueError('Recomputed metrics or gate differ')
    receipt = json.loads((directory/'resource_receipt.json').read_text())
    if receipt['run_id'] != cfg['run_id'] or receipt['status'] != 'completed' or receipt['exit_code'] != 0 or receipt['max_seconds'] != cfg['max_seconds'] or receipt['charged_seconds'] != math.ceil(receipt['elapsed_seconds']) or not 0 < receipt['charged_seconds'] <= cfg['max_seconds']+cfg['guard_seconds']:
        raise ValueError('Bounded execution receipt differs')
    checkpoint = json.loads((directory/'checkpoint_manifest.json').read_text())
    if checkpoint['kind'] != 'model_weights_only_not_optimizer_or_rng_resume' or not any(p.endswith('.safetensors') for p in checkpoint['files']):
        raise ValueError('Missing final checkpoint manifest')
    return {'phase': 'E011', 'verified_compact_outputs': True, 'predictions_rechecked': len(baseline)+len(training)+len(dev),
            'updates_reconciled': len(history), 'charged_seconds': receipt['charged_seconds'],
            'engineering_gate': expected['engineering_gate'], 'metrics': expected,
            'checkpoint_backup_verification': 'separate_full_file_hash_and_independent_copy_required',
            'reference_nll_scope': 'saved_sum_accounting_only_no_model_reexecution',
            'files_sha256': {p.name: sha256_file(p) for p in sorted(directory.iterdir()) if p.is_file()}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    if Path(a.out).exists():
        raise FileExistsError('Immutable verification output exists')
    tokenizer, _ = verified_tokenizer(Path(a.tokenizer_dir))
    result = audit(a.run_dir, tokenizer)
    dump(a.out, result)
    print(json.dumps({k: result[k] for k in ('verified_compact_outputs', 'predictions_rechecked', 'engineering_gate')}))


if __name__ == '__main__':
    main()
