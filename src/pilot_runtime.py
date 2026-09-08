"""CPU-verifiable gate between immutable pilot artifacts and GPU execution."""
import json
from pathlib import Path
from .pilot_data import ARMS, audit_arms, canonical_hash
from .sft_data import read_jsonl, sha256_file


def load_pilot_inputs(cfg, tokenizer=None):
    root = Path(cfg['data_dir'])
    manifest = json.loads((root/'manifest.json').read_text())
    if sha256_file(root/'manifest.json') != cfg['data_manifest_sha256']:
        raise ValueError('Frozen data manifest changed')
    if manifest['status'] != 'FROZEN_PILOT_V1_NO_MODEL_OUTCOMES' or cfg['arm'] not in ARMS:
        raise ValueError('Unknown pilot dataset or arm')
    for name, digest in manifest['files_sha256'].items():
        if Path(name).name != name or sha256_file(root/name) != digest:
            raise ValueError('Frozen pilot artifact changed: ' + name)
    if cfg['batch_size'] != 4 or cfg['microbatch_size'] != 2 or cfg['seed'] != manifest['paired_seed']:
        raise ValueError('Paired seed and batch sizes are frozen')
    schedule = json.loads((root/'schedule_seed17.json').read_text())
    if canonical_hash(schedule) != manifest['schedule_canonical_sha256'] or cfg['steps'] != len(schedule):
        raise ValueError('Pilot must complete the common frozen schedule')
    rows = {arm: read_jsonl(root/f'train_{arm}.jsonl') for arm in ARMS}
    dev = read_jsonl(root/'dev_matched.jsonl')
    broad = read_jsonl(root/'dev_broad.jsonl')
    groups = [{tuple(sorted(r['numbers'])) for r in values} for values in [rows['repeat'], dev, broad]]
    if any(groups[i] & groups[j] for i in range(3) for j in range(i+1, 3)):
        raise ValueError('Training/development group overlap')
    audit = audit_arms(rows, schedule, tokenizer, cfg['max_length']) if tokenizer is not None else None
    return rows[cfg['arm']], dev, broad, schedule, audit


def unique_rows(rows, limit):
    result, seen = [], set()
    for row in rows:
        if row['problem_id'] not in seen:
            result.append(row)
            seen.add(row['problem_id'])
        if len(result) == limit:
            break
    return result
