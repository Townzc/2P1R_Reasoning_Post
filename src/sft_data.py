"""Exact serialization, response labels and deterministic exposure accounting.

No packing: each sequence has its own attention-mask row. No truncation.
Token budgets include supervised terminal EOS and exclude padding.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def prefix(prompt):
    return f"Problem: {prompt}\nSolution:\n"


def encode_row(row, tokenizer, max_length):
    if not row['prompt'].strip() or not row['response'].strip():
        raise ValueError('Empty prompt or response')
    prompt = prefix(row['prompt'])
    text = prompt + row['response']
    encoded = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    ids, offsets = list(encoded['input_ids']), encoded['offset_mapping']
    boundary = len(prompt)
    if any(start < boundary < end for start, end in offsets):
        raise ValueError('A token crosses the prompt/response boundary')
    labels = [token if start >= boundary and end > start else -100
              for token, (start, end) in zip(ids, offsets)]
    first = next((i for i, x in enumerate(labels) if x != -100), None)
    if first is None or first == 0:
        raise ValueError('Need nonempty prompt and supervised response')
    if ids[:first] != tokenizer(prompt, add_special_tokens=False)['input_ids']:
        raise ValueError('Training/inference prompt tokenization differs')
    eos = tokenizer.eos_token_id
    if eos is None or eos in ids:
        raise ValueError('Missing EOS id or embedded EOS in sample')
    ids.append(eos)
    labels.append(eos)
    if len(ids) > max_length:
        raise ValueError(f'Sequence length {len(ids)} exceeds {max_length}; no truncation allowed')
    return {'input_ids': ids, 'labels': labels, 'n_prompt': first,
            'n_supervised': sum(x != -100 for x in labels[1:]),
            'n_processed': len(ids), 'problem_id': row['problem_id'],
            'path_id': row.get('path_id', ''),
            'response_hash': hashlib.sha256(row['response'].encode()).hexdigest()}


def collate(rows, pad_id):
    import torch
    width = max(len(r['input_ids']) for r in rows)
    return {
        'input_ids': torch.tensor([r['input_ids'] + [pad_id]*(width-len(r['input_ids'])) for r in rows]),
        'attention_mask': torch.tensor([[1]*len(r['input_ids']) + [0]*(width-len(r['input_ids'])) for r in rows]),
        'labels': torch.tensor([r['labels'] + [-100]*(width-len(r['labels'])) for r in rows]),
    }


def update_schedule(n_rows, updates, batch_size, seed):
    if min(n_rows, updates, batch_size) <= 0:
        raise ValueError('Positive dataset size, updates and batch size required')
    rng = random.Random(seed)
    order, cursor = [], 0
    schedule = []
    for _ in range(updates):
        batch = []
        for _ in range(batch_size):
            if cursor == len(order):
                order = list(range(n_rows))
                rng.shuffle(order)
                cursor = 0
            batch.append(order[cursor])
            cursor += 1
        schedule.append(batch)
    return schedule


def budget_report(rows, schedule, microbatch_size):
    if microbatch_size <= 0:
        raise ValueError('Positive microbatch size required')
    exposures = Counter(i for update in schedule for i in update)
    problem, path, text = Counter(), Counter(), Counter()
    updates = []
    padding = 0
    for update in schedule:
        supervised = sum(rows[i]['n_supervised'] for i in update)
        processed = sum(rows[i]['n_processed'] for i in update)
        updates.append({'supervised_tokens': supervised, 'processed_tokens': processed})
        for start in range(0, len(update), microbatch_size):
            lengths = [rows[i]['n_processed'] for i in update[start:start+microbatch_size]]
            padding += max(lengths)*len(lengths)-sum(lengths)
    for i, count in exposures.items():
        r = rows[i]
        problem[r['problem_id']] += count
        path[json.dumps([r['problem_id'], r['path_id']])] += count
        text[json.dumps([r['problem_id'], r['response_hash']])] += count
    return {'optimizer_updates': len(schedule), 'presentations': sum(exposures.values()),
            'supervised_response_tokens': sum(u['supervised_tokens'] for u in updates),
            'processed_nonpadding_tokens': sum(u['processed_tokens'] for u in updates),
            'padding_tokens': padding, 'eos_supervised': True, 'packing': False,
            'normalization': 'sum_shifted_response_cross_entropy / update_response_token_count',
            'per_update': updates, 'row_exposures': dict(exposures),
            'problem_exposures': dict(problem), 'path_exposures': dict(path),
            'text_exposures': dict(text), 'cross_condition_token_matching_claimed': False}


def shifted_loss_sum(logits, labels):
    import torch.nn.functional as F
    targets = labels[:, 1:]
    valid = targets != -100
    if not valid.any():
        raise ValueError('No supervised shifted targets')
    return F.cross_entropy(logits[:, :-1][valid].float(), targets[valid], reduction='sum')
