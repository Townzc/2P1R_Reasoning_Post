"""CPU verification of E013 recorded token streams, scores, exposures and receipt."""
import argparse
import json
from pathlib import Path

from scripts.audit_family_matching import verified_tokenizer
from src.real_math_engineering import load_frozen, score_completion, summarize, engineering_gate, dump
from src.relation_experiment import profile
from src.sft_data import read_jsonl, sha256_file


def audit_predictions(path, expected_rows, tokenizer, cfg):
    predictions = read_jsonl(path)
    if len(predictions) != len(expected_rows):
        raise ValueError('Missing or extra predictions')
    for pred, row in zip(predictions, expected_rows):
        if any(pred.get(k) != v for k, v in row.items()):
            raise ValueError('Prediction identity/prompt/gold differs')
        tokens = pred['generated_ids']
        if not tokens or len(tokens) > cfg['max_new_tokens'] or any(type(i) is not int or not 0 <= i < len(tokenizer) for i in tokens):
            raise ValueError('Invalid generated token stream')
        eos = tokenizer.eos_token_id in tokens
        if eos and tokens.index(tokenizer.eos_token_id) != len(tokens)-1:
            raise ValueError('Recorded stream extends beyond EOS')
        if not eos and len(tokens) != cfg['max_new_tokens']:
            raise ValueError('Undocumented early generation stop')
        text = tokenizer.decode(tokens[:-1] if eos else tokens, skip_special_tokens=False,
                                clean_up_tokenization_spaces=False)
        score = score_completion(row, text, eos, not eos)
        if pred['text'] != text or pred['generated_tokens'] != len(tokens) or pred['score'] != score:
            raise ValueError('Text/token/score record differs')
    return predictions


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    tokenizer, _ = verified_tokenizer(Path(a.tokenizer_dir))
    cfg, _, train, dev, _, _, budget = load_frozen(tokenizer)
    run = Path('runs')/cfg['run_id']
    manifest = json.loads((run/'run_manifest.json').read_text())
    if manifest['status'] != 'completed' or manifest['config'] != cfg:
        raise ValueError('Incomplete E013; retain its artifacts and report failure separately')
    results = json.loads((run/'metrics.json').read_text())
    for name, rows, key in [('base_dev', dev, 'base_dev'), ('final_train', train, 'train'), ('final_dev', dev, 'final_dev')]:
        if summarize(audit_predictions(run/f'{name}.jsonl', rows, tokenizer, cfg)) != results[key]:
            raise ValueError('Aggregate prediction metrics differ')
    history = read_jsonl(run/'train_history.jsonl')
    if len(history) != cfg['steps'] or manifest['steps_completed'] != cfg['steps']:
        raise ValueError('Incomplete optimizer trajectory')
    for step, (record, counts) in enumerate(zip(history, budget['per_update']), 1):
        if record['step'] != step or any(record[k] != counts[k] for k in ('supervised_tokens', 'processed_tokens')):
            raise ValueError('Actual per-update token dose differs')
    for name in ('planned_budget.json', 'actual_budget.json'):
        if json.loads((run/name).read_text()) != budget:
            raise ValueError('Recorded exposure differs')
    throughput = profile(history, cfg)
    if throughput != results['throughput'] or throughput != json.loads((run/'throughput.json').read_text()):
        raise ValueError('Profile metrics differ')
    if engineering_gate(cfg, len(history), throughput, results['train'], results['train_reference_nll']['nll']) != results['engineering_gate']:
        raise ValueError('Engineering gate differs')
    receipt = json.loads((run/'resource_receipt.json').read_text())
    if receipt['run_id'] != cfg['run_id'] or receipt['status'] != 'completed' or receipt['exit_code'] != 0 or not 0 < receipt['charged_seconds'] <= cfg['max_seconds']+cfg['guard_seconds']:
        raise ValueError('Bounded resource receipt differs')
    dump(a.out, {'status': 'passed_record_consistency_checks', 'model_rerun': False,
        'nll_independently_recomputed': False, 'proof_correctness_verified': False,
        'raw_token_streams_checked': 64, 'updates_checked': len(history),
        'engineering_gate': results['engineering_gate'], 'resource_receipt_sha256': sha256_file(run/'resource_receipt.json'),
        'run_manifest_sha256': sha256_file(run/'run_manifest.json')})


if __name__ == '__main__':
    main()
