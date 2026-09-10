"""Independent raw-tokenizer verification of frozen E014 diagnostic inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from tokenizers import Tokenizer


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def token_hash(ids):
    return hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()


def read_rows(path):
    with Path(path).open() as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--ledger', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    if Path(a.out).exists():
        raise FileExistsError('Independent verification output is immutable')
    cfg = json.loads(Path('configs/real_math_e014/diagnostic.json').read_text())
    folder = Path('reports/real_math_e014_inputs_r1')
    manifest = json.loads((folder / 'manifest.json').read_text())
    release = json.loads(Path('configs/real_math_e014/release.json').read_text())
    assert release['manifest_sha256'] == sha(folder / 'manifest.json')
    assert manifest['config_sha256'] == sha('configs/real_math_e014/diagnostic.json')
    for name, digest in manifest['files_sha256'].items():
        assert Path(name).name == name and sha(folder / name) == digest, name
    for name, digest in manifest['source_files_sha256'].items():
        historical = subprocess.check_output(['git', 'show', manifest['source_commit'] + ':' + name])
        assert sha(name) == hashlib.sha256(historical).hexdigest() == digest, name
    lock = json.loads(Path('configs/models.lock.json').read_text())['main']
    for name in ('config.json', 'tokenizer.json', 'vocab.json', 'merges.txt', 'tokenizer_config.json'):
        item = next(r for r in lock['files'] if r['rfilename'] == name)
        data = (Path(a.tokenizer_dir) / name).read_bytes()
        assert len(data) == item['size'] and hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest() == item['blobId']
    tok = Tokenizer.from_file(str(Path(a.tokenizer_dir) / 'tokenizer.json'))
    eos = 151643
    cases = json.loads((folder / 'cases.json').read_text())
    evidence = json.loads((folder / 'cpu_evidence.json').read_text())
    old_folder = Path('reports/real_math_e013_inputs_r1')
    assert sha(old_folder / 'manifest.json') == cfg['e013_input_manifest_sha256']
    old_manifest = json.loads((old_folder / 'manifest.json').read_text())
    assert sha(old_folder / 'train.jsonl') == old_manifest['files_sha256']['train.jsonl']
    train = read_rows(old_folder / 'train.jsonl')
    original_path = Path('runs/gsm8k_overfit_e013_r1/final_train.jsonl')
    assert sha(original_path) == cfg['reference_prediction_sha256']
    original = read_rows(original_path)
    assert len(cases) == len(train) == len(original) == 32
    failed = [r['problem_id'] for r in original if not r['score']['terminated_correct']]
    controls = [r['problem_id'] for r in original if r['score']['terminated_correct']][:2]
    assert failed == cfg['selected_failed_ids'] and controls == cfg['selected_control_ids']
    selected = set(failed + controls)
    target_count = prompt_count = 0
    offsets = []
    for i, (case, row, pred) in enumerate(zip(cases, train, original)):
        prefix = 'Problem: ' + row['prompt'] + '\nSolution:\n'
        enc = tok.encode(prefix + row['response'], add_special_tokens=False)
        assert not any(start < len(prefix) < end for start, end in enc.offsets)
        first = next(j for j, (start, end) in enumerate(enc.offsets) if start >= len(prefix) and end > start)
        prompt = tok.encode(prefix, add_special_tokens=False).ids
        target = enc.ids[first:] + [eos]
        assert prompt == enc.ids[:first] == case['prompt_ids']
        assert target == case['target_ids'] and eos not in enc.ids
        assert token_hash(prompt) == case['prompt_ids_sha256'] and token_hash(target) == case['target_ids_sha256']
        assert case['problem_id'] == row['problem_id'] == pred['problem_id'] and case['row_index'] == i
        assert case['original_generated_ids'] == pred['generated_ids'] and case['original_score'] == pred['score']
        assert case['selected_for_batch1'] == (row['problem_id'] in selected)
        assert case['selection_role'] == ('failed' if row['problem_id'] in failed else
                                           ('control' if row['problem_id'] in controls else 'replay_only'))
        n = 0
        while n < min(len(target), len(pred['generated_ids'])) and target[n] == pred['generated_ids'][n]:
            n += 1
        assert n == case['original_common_prefix_tokens']
        assert case['original_first_difference'] == (n if n < len(target) else None)
        offsets.append({'problem_id': row['problem_id'], 'n_prompt': first, 'n_target': len(target),
                        'first_difference_target_index': case['original_first_difference'],
                        'first_difference_logit_index': first + n - 1 if n < len(target) else None,
                        'eos_logit_index': len(enc.ids) - 1})
        target_count += len(target); prompt_count += len(prompt)
    assert [c['problem_id'] for c in cases if c['selected_for_batch1']] == cfg['single_example_decode_order']
    assert target_count == evidence['unique_supervised_tokens'] == 5226
    for b, start in zip(evidence['batches'], range(0, 32, 8)):
        group = cases[start:start + 8]; width = max(len(c['prompt_ids']) for c in group)
        assert b == {'row_indices': list(range(start, start + 8)), 'prompt_width': width,
                     'left_padding': [width - len(c['prompt_ids']) for c in group],
                     'maximum_context_tokens': width + 768}
    assert sha(a.ledger) == cfg['expected_ledger_sha256']
    ledger = json.loads(Path(a.ledger).read_text())
    assert ledger['authorized_gpu_seconds'] == 7200 and len(ledger['jobs']) == 17
    assert len({j['run_id'] for j in ledger['jobs']}) == 17
    for job in ledger['jobs']:
        assert job['status'] != 'reserved' and job == json.loads((Path('runs') / job['run_id'] / 'resource_receipt.json').read_text())
    used = sum(j['charged_seconds'] for j in ledger['jobs'])
    assert used == 6297 and 7200 - used - cfg['max_seconds'] - cfg['guard_seconds'] == 528
    result = {'phase': 'E014_INDEPENDENT_CPU_INPUT_VERIFICATION', 'status': 'passed',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'verifier_sha256': sha(__file__), 'release_sha256': sha('configs/real_math_e014/release.json'),
        'raw_tokenizer_api_used': True, 'training_rows_checked': 32, 'individual_decode_rows': 10,
        'reference_targets_including_eos': target_count, 'prompt_tokens': prompt_count,
        'all_eos_supervised': True, 'all_case_offsets_checked': offsets,
        'checkpoint_hash_verification': 'All12 files rehashed during CPU preparation; no model loaded.',
        'ledger_sha256': sha(a.ledger), 'receipts_reconciled': 17, 'used_seconds': used,
        'remaining_seconds': 7200 - used, 'maximum_new_reservation': 375, 'unreserved_after_maximum': 528,
        'pretrained_model_calls': 0, 'server_contacted': False, 'gpu_seconds_added': 0}
    with Path(a.out).open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True); f.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'all_case_offsets_checked'}, indent=2))


if __name__ == '__main__':
    main()
