"""Independent raw-tokenizer check of E015's release; no pretrained model calls."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from scripts.audit_family_matching import verified_tokenizer
from src.real_math_engineering import dump


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(tokenizer_dir):
    folder = Path('reports/real_math_e015_inputs_r1')
    release = json.loads(Path('configs/real_math_e015/release.json').read_text())
    if sha(folder / 'manifest.json') != release['manifest_sha256']:
        raise ValueError('Release manifest hash mismatch')
    manifest = json.loads((folder / 'manifest.json').read_text())
    for name, expected in manifest['files_sha256'].items():
        if Path(name).name != name or sha(folder / name) != expected:
            raise ValueError('Frozen input hash mismatch')
    prior = Path('reports/real_math_e013_inputs_r1')
    if sha(prior / 'manifest.json') != manifest['e013_input_manifest_sha256']:
        raise ValueError('Prior input manifest changed')
    old_manifest = json.loads((prior / 'manifest.json').read_text())
    for name in ('train.jsonl', 'schedule.json', 'budget.json'):
        if sha(prior / name) != old_manifest['files_sha256'][name]:
            raise ValueError('Original E013 input changed')
    with (prior / 'train.jsonl').open() as stream:
        train = [json.loads(line) for line in stream if line.strip()]
    cases = json.loads((folder / 'cases.json').read_text())
    schedule = json.loads((prior / 'schedule.json').read_text())
    tokenizer, token_record = verified_tokenizer(Path(tokenizer_dir))
    if len(cases) != len(train) or len(train) != 32:
        raise ValueError('Require original 32 references')
    lengths = []
    for i, (row, case) in enumerate(zip(train, cases)):
        prompt = 'Problem: ' + row['prompt'] + '\nSolution:\n'
        full = tokenizer(prompt + row['response'], add_special_tokens=False, return_offsets_mapping=True)
        prompt_ids = tokenizer(prompt, add_special_tokens=False)['input_ids']
        boundary = len(prompt)
        positions = [j for j, (start, end) in enumerate(full['offset_mapping']) if start >= boundary and end > start]
        if not positions or positions != list(range(len(prompt_ids), len(full['input_ids']))):
            raise ValueError('Response boundary or mask differs')
        if any(start < boundary < end for start, end in full['offset_mapping']):
            raise ValueError('Token crosses prompt/response boundary')
        targets = full['input_ids'][len(prompt_ids):] + [tokenizer.eos_token_id]
        expected = {'problem_id': row['problem_id'], 'row_index': i, 'selected_for_batch1': False,
                    'prompt_ids': prompt_ids, 'target_ids': targets,
                    'prompt_ids_sha256': hashlib.sha256(json.dumps(prompt_ids, separators=(',', ':')).encode()).hexdigest(),
                    'target_ids_sha256': hashlib.sha256(json.dumps(targets, separators=(',', ':')).encode()).hexdigest()}
        if case != expected or full['input_ids'][:len(prompt_ids)] != prompt_ids:
            raise ValueError('Raw tokenizer differs from frozen case')
        if tokenizer.eos_token_id in full['input_ids'] or len(prompt_ids) + len(targets) > 1024:
            raise ValueError('Embedded EOS or overlength reference')
        lengths.append((len(targets), len(prompt_ids) + len(targets)))
    counts = Counter(index for update in schedule for index in update)
    if len(schedule) != 256 or any(len(u) != 4 for u in schedule) or counts != Counter({i: 32 for i in range(32)}):
        raise ValueError('Original update order/exposures differ')
    total_response = sum(lengths[i][0] for update in schedule for i in update)
    total_processed = sum(lengths[i][1] for update in schedule for i in update)
    planned = json.loads((folder / 'budget.json').read_text())
    if planned != json.loads((prior / 'budget.json').read_text()) or (
            total_response, total_processed) != (167232, 229056):
        raise ValueError('Dose mismatch')
    rates = json.loads((folder / 'learning_rates.json').read_text())
    expected_rates = [0.00005] * 192 + [0.000025 * (1 + math.cos(math.pi * j / 64)) for j in range(1, 65)]
    if (not isinstance(rates, list) or len(rates) != 256
            or any(type(a) not in (int, float) or not math.isfinite(a) for a in rates)
            or any(abs(a-b) > 1e-18 for a, b in zip(rates, expected_rates))):
        raise ValueError('Released learning rate sequence differs')
    return {'phase': 'E015_INDEPENDENT_INPUT_VERIFICATION', 'status': 'passed',
            'train_rows': 32, 'reference_targets': sum(a for a, _ in lengths), 'supervised_eos': 32,
            'optimizer_updates': 256, 'nonzero_lr_updates': sum(x > 0 for x in rates),
            'summed_lr': math.fsum(rates), 'supervised_tokens': total_response,
            'processed_tokens': total_processed, 'original_schedule_sha256': sha(prior / 'schedule.json'),
            'release_sha256': sha('configs/real_math_e015/release.json'), 'tokenizer_revision': token_record['revision'],
            'pretrained_model_calls': 0, 'server_contacted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer-dir', required=True)
    parser.add_argument('--out')
    args = parser.parse_args()
    result = verify(args.tokenizer_dir)
    if args.out:
        dump(Path(args.out), result)
    print(json.dumps(result, indent=2))
