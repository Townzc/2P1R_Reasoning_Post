"""Independently reconcile compact E013 data with C017 raw sources, CPU only."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import random

from scripts.audit_family_matching import verified_tokenizer
from scripts.run_relation_engineering import check_ledger
from src.real_math_audit import sha
from src.real_math_engineering import CONFIG, SELECTION, load_frozen, validate_rows, dump
from src.sft_data import read_jsonl, sha256_file


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--parents', required=True)
    p.add_argument('--candidates', required=True)
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--ledger', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    if Path(a.out).exists():
        raise FileExistsError('Verification output is immutable')
    tokenizer, _ = verified_tokenizer(Path(a.tokenizer_dir))
    cfg, manifest, train, dev, encoded, schedule, budget = load_frozen(tokenizer)
    if sha256_file(a.parents) != manifest['private_parent_sha256'] or sha256_file(a.candidates) != manifest['private_candidate_sha256']:
        raise ValueError('Raw audit sources differ')
    originals = {r['id']: r for r in read_jsonl(a.parents)}
    decisions = read_jsonl(SELECTION)
    selected = {(d['problem_id'], d['candidate_index']): d for d in decisions}
    raw = [r for r in read_jsonl(a.candidates) if (r['problem_id'], r['candidate_index']) in selected]
    if len(raw) != 32:
        raise ValueError('Raw candidate count differs')
    sources = {(r['problem_id'], r['candidate_index']): r for r in raw}
    for row in train+dev:
        parent = originals[row['problem_id']]
        if parent['original_split'] != 'train' or parent['dataset'] != 'gsm8k' or parent['problem'] != row['prompt'] or parent['answer'] != row['answer'] or parent['group_id'] != row['group_id']:
            raise ValueError('Original problem/answer/group identity differs')
    dev_original = sorted((r for r in originals.values() if r['dataset'] == 'gsm8k'
                         and r['partition'] == 'development'), key=lambda r: r['rank'])[:16]
    if [r['id'] for r in dev_original] != [r['problem_id'] for r in dev]:
        raise ValueError('Development rank selection differs')
    for row, d in zip(train, decisions):
        r = sources[(row['problem_id'], int(row['path_id']))]
        if row['response'] != r['row']['generated_solution'] or sha(json.dumps(r['row'], sort_keys=True, ensure_ascii=False)) != d['source_row_sha256'] or any(r[k] != d[k] for k in ('shard', 'row_index')):
            raise ValueError('Original candidate provenance differs')
    # Bypass AutoTokenizer, encode_row and budget_report for independent counts.
    from tokenizers import Tokenizer
    raw_tokenizer = Tokenizer.from_file(str(Path(a.tokenizer_dir)/'tokenizer.json'))
    counts = []
    for row, expected in zip(train, encoded):
        prompt = 'Problem: '+row['prompt']+'\nSolution:\n'
        raw_encoding = raw_tokenizer.encode(prompt+row['response'], add_special_tokens=False)
        if any(s < len(prompt) < e for s, e in raw_encoding.offsets):
            raise ValueError('Independent offset boundary crosses a token')
        labels = [i if s >= len(prompt) and e > s else -100
                  for i, (s, e) in zip(raw_encoding.ids, raw_encoding.offsets)] + [tokenizer.eos_token_id]
        ids = raw_encoding.ids+[tokenizer.eos_token_id]
        independent = {'supervised_tokens': sum(i != -100 for i in labels[1:]), 'processed_tokens': len(ids)}
        if expected['input_ids'] != ids or expected['labels'] != labels:
            raise ValueError('Independent exact IDs/labels differ')
        counts.append(independent)
    rng, stream = random.Random(17), []
    for _ in range(32):
        order = list(range(32)); rng.shuffle(order); stream.extend(order)
    independent_schedule = [stream[i:i+4] for i in range(0, len(stream), 4)]
    if schedule != independent_schedule or set(Counter(stream).values()) != {32}:
        raise ValueError('Independent 32-epoch schedule differs')
    independent_updates = [{key: sum(counts[i][key] for i in update)
                            for key in ('supervised_tokens', 'processed_tokens')} for update in schedule]
    if independent_updates != budget['per_update'] or sum(r['supervised_tokens'] for r in independent_updates) != 167232 or sum(r['processed_tokens'] for r in independent_updates) != 229056 or budget['padding_tokens'] != 0:
        raise ValueError('Independent aggregate/update accounting differs')
    failures = []
    for label in ('missing_train', 'reordered_train', 'changed_answer', 'changed_prompt', 'duplicate_group', 'changed_candidate', 'held_out_id', 'reordered_dev'):
        tt, dd = copy.deepcopy(train), copy.deepcopy(dev)
        if label == 'missing_train': tt.pop()
        elif label == 'reordered_train': tt[0], tt[1] = tt[1], tt[0]
        elif label == 'changed_answer': tt[0]['answer'] = '999999'
        elif label == 'changed_prompt': tt[0]['prompt'] += ' altered'
        elif label == 'duplicate_group': dd[0]['group_id'] = tt[0]['group_id']
        elif label == 'changed_candidate': tt[0]['response'] += ' altered'
        elif label == 'held_out_id': tt[0]['problem_id'] = 'gsm8k/test/00000'
        elif label == 'reordered_dev': dd[0], dd[1] = dd[1], dd[0]
        try:
            validate_rows(cfg, tt, dd, tokenizer)
        except ValueError:
            failures.append(label)
        else:
            raise ValueError('Tampered input was not rejected: '+label)
    ledger_before = sha256_file(a.ledger)
    accounting = check_ledger(cfg, a.ledger, json.loads(Path('configs/resource_budget.json').read_text()))
    if sha256_file(a.ledger) != ledger_before:
        raise ValueError('CPU verification changed the resource ledger')
    result = {'status': 'passed_cpu_input_verification', 'source_rows_checked': 32, 'original_train_parents_checked': 48,
        'train_dev_groups_disjoint': True, 'independent_raw_tokenizer_labels_checked': 32,
        'independent_updates_checked': 256, 'supervised_tokens': 167232, 'processed_tokens': 229056,
        'padding_tokens': 0, 'tampered_cases_rejected': failures, 'accounting': accounting,
        'model_weights_loaded': False, 'gpu_seconds_added': 0, 'teacher_calls': 0,
        'data_manifest_sha256': sha256_file(Path(cfg['data_dir'])/'manifest.json')}
    dump(a.out, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
