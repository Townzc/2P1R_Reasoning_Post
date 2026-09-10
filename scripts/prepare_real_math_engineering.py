"""Prepare E013 on CPU from the already audited C017 bytes; no new data/model."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from scripts.audit_family_matching import verified_tokenizer
from src.real_math_audit import sha, normalized
from src.real_math_engineering import (CONFIG, PARENTS, SELECTION, provenance,
                                      parent_index, validate_rows, dump, write_rows)
from src.sft_data import read_jsonl, sha256_file


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--parents', required=True)
    p.add_argument('--candidates', required=True)
    p.add_argument('--tokenizer-dir', required=True)
    a = p.parse_args()
    cfg = json.loads(CONFIG.read_text())
    folder = Path(cfg['data_dir'])
    if folder.exists():
        raise FileExistsError('Immutable E013 input directory already exists')
    source = provenance()
    index = parent_index(cfg)
    freeze = json.loads((PARENTS/'freeze.json').read_text())
    if sha256_file(a.parents) != freeze['private_problem_records_sha256'] or sha256_file(a.candidates) != cfg['raw_candidates_sha256']:
        raise ValueError('C017 private source bytes differ; do not reacquire a different pool')
    tokenizer, token_record = verified_tokenizer(Path(a.tokenizer_dir))
    start = time.monotonic()
    parents = {r['id']: r for r in read_jsonl(a.parents)}
    selection = read_jsonl(SELECTION)
    wanted = {(d['problem_id'], d['candidate_index']) for d in selection}
    candidates = [r for r in read_jsonl(a.candidates) if (r['problem_id'], r['candidate_index']) in wanted]
    if len(candidates) != len(wanted):
        raise ValueError('Missing or repeated selected candidate')
    candidates = {(r['problem_id'], r['candidate_index']): r for r in candidates}
    def base(parent):
        return {'problem_id': parent['id'], 'group_id': parent['group_id'],
                'prompt': parent['problem'], 'answer': parent['answer']}
    train = []
    for d in selection:
        parent = parents[d['problem_id']]
        raw = candidates[(d['problem_id'], d['candidate_index'])]
        if any(raw[k] != d[k] for k in ('shard', 'row_index')) or sha(json.dumps(raw['row'], ensure_ascii=False, sort_keys=True)) != d['source_row_sha256']:
            raise ValueError('Candidate provenance differs')
        if raw['row']['problem_source'] != 'gsm8k' or normalized(raw['row']['problem']) != normalized(parent['problem']):
            raise ValueError('Response source refers to a different problem')
        train.append({**base(parent), 'response': raw['row']['generated_solution'],
                      'path_id': str(d['candidate_index']), 'source': d})
    dev_ids = [r['id'] for r in sorted((r for r in index.values() if r['dataset'] == 'gsm8k'
               and r['partition'] == 'development'), key=lambda r: r['rank'])[:cfg['dev_count']]]
    dev = [base(parents[k]) for k in dev_ids]
    encoded, schedule, budget = validate_rows(cfg, train, dev, tokenizer)
    folder.mkdir(parents=True, exist_ok=False)
    write_rows(folder/'train.jsonl', train)
    write_rows(folder/'dev.jsonl', dev)
    dump(folder/'schedule.json', schedule)
    dump(folder/'budget.json', budget)
    dump(folder/'attribution.json', {
        'questions': 'OpenAI GSM8K (MIT), original train split only',
        'question_repository': 'https://github.com/openai/grade-school-math',
        'question_revision': '3101c7d5072418e28b9008a6636bde82a006892c',
        'responses': 'NVIDIA OpenMathInstruct-2 (CC-BY-4.0); unchanged selected generated_solution text',
        'response_repository': 'https://huggingface.co/datasets/nvidia/OpenMathInstruct-2',
        'response_revision': '469216e3f46f4dacf476b382e192485ea51a143e',
        'license': 'https://creativecommons.org/licenses/by/4.0/',
        'source_notice': 'Per-response shard, row, candidate index and hashes are in train.jsonl; original problem wording is used in place of equivalent normalized source wording.',
        'limitations': 'Answer-agreement screening does not prove intermediate reasoning; selection is an engineering subset, not an unbiased scientific sample.'})
    manifest = {**source, 'phase': 'E013_CPU_PREPARATION', 'status': 'prepared_cpu_only',
        'config_sha256': sha256_file(CONFIG), 'parent_freeze_sha256': sha256_file(PARENTS/'freeze.json'),
        'private_parent_sha256': sha256_file(a.parents), 'private_candidate_sha256': sha256_file(a.candidates),
        'selection_sha256': sha256_file(SELECTION), 'tokenizer': token_record,
        'selection': 'C017 fixed first32 available audit-rank parents, first accepted response; first16 frozen development ranks; no model outputs inspected',
        'train_count': len(train), 'dev_count': len(dev), 'baseline_generation_prompts': len(dev),
        'final_generation_prompts': len(train)+len(dev),
        'one_pass_supervised_tokens': sum(r['n_supervised'] for r in encoded),
        'max_training_sequence': max(r['n_processed'] for r in encoded),
        'gpu_seconds_added': 0, 'teacher_calls': 0, 'model_weights_loaded': False,
        'wall_seconds': time.monotonic()-start, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'files_sha256': {x.name: sha256_file(x) for x in sorted(folder.iterdir()) if x.is_file()}}
    dump(folder/'manifest.json', manifest)
    print(json.dumps({k: manifest[k] for k in ('status','train_count','dev_count','one_pass_supervised_tokens','max_training_sequence')}))


if __name__ == '__main__':
    main()
