"""E013 frozen GSM8K inputs and conservative numeric-completion scoring."""
from __future__ import annotations

import base64
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

from src.real_math_audit import last_boxed, normalized, scalar, sha
from src.sft_data import read_jsonl, encode_row, update_schedule, budget_report, sha256_file

CONFIG = Path('configs/real_math_e013/overfit.json')
RELEASE = Path('configs/real_math_e013/release.json')
PARENTS = Path('reports/real_math_c017_parents_r2')
SELECTION = Path('reports/real_math_c017_scale_proposal_r1/engineering_32_rows.jsonl')


def dump(path, obj):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        f.write('\n')


def write_rows(path, rows):
    with Path(path).open('x', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n')


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def source_files():
    # Include the transitive local helpers, not only the entry point.
    return sorted([str(p) for folder in ('src', 'scripts') for p in Path(folder).glob('*.py')]
                  + [str(CONFIG), 'configs/models.lock.json', 'configs/resource_budget.json',
                     'requirements.txt', 'requirements-diagnostics.txt'])


def provenance(extra=()):
    if git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Commit and publish tracked changes before execution')
    files = sorted(set(source_files()) | set(map(str, extra)))
    git('ls-files', '--error-unmatch', *files)
    commit = git('rev-parse', 'HEAD')
    if commit != git('rev-parse', 'origin/main'):
        raise ValueError('Synchronize the published origin/main first')
    return {'source_commit': commit, 'source_worktree_dirty': False,
            'source_files_sha256': {name: sha256_file(name) for name in files}}


def parent_index(cfg):
    if sha256_file(PARENTS/'freeze.json') != cfg['parent_freeze_sha256']:
        raise ValueError('C017 parent freeze differs')
    freeze = json.loads((PARENTS/'freeze.json').read_text())
    raw = gzip.decompress(base64.b64decode((PARENTS/'problem_manifest.jsonl.gz.b64').read_bytes()))
    if hashlib.sha256(raw).hexdigest() != freeze['problem_manifest_sha256']:
        raise ValueError('Archived C017 parent index differs')
    rows = [json.loads(line) for line in raw.decode().split('\n') if line.strip()]
    index = {r['id']: r for r in rows}
    if len(index) != len(rows):
        raise ValueError('Duplicate parent identity')
    return index


def numeric_final(text):
    """Last explicit marker wins. Never fish a number out of working or prose."""
    markers = list(re.finditer(r'\\(?:boxed|fbox)\s*\{|####', text))
    if not markers:
        return None, 'missing_final_marker'
    marker = markers[-1]
    value = text[marker.end():].strip() if marker[0] == '####' else last_boxed(text[marker.start():])
    # The general MATH layout normalizer joins whitespace; do not join two
    # numeric tokens into a different GSM8K number (e.g. "1 2" -> 12).
    if value is None or re.search(r'\d\s+\d', value):
        return value, 'unresolved_numeric_final'
    if scalar(value) is None:
        return value, 'unresolved_numeric_final'
    return value, 'parsed'


def score_completion(row, text, eos, truncated):
    gold = scalar(row['answer'])
    if gold is None:
        raise ValueError('Engineering GSM8K gold must be an exact scalar')
    value, reason = numeric_final(text)
    special = bool(re.search(r'<\|[^<>]*\|>', text))
    if special:
        reason = 'embedded_special_token'
    correct = reason == 'parsed' and scalar(value) == gold
    return {'extracted_answer': value, 'parse_status': reason, 'answer_correct': correct,
            'terminated_correct': bool(correct and eos and not truncated),
            'ended_with_eos': bool(eos), 'truncated': bool(truncated),
            'reference_exact_match': text.strip() == row['response'].strip() if 'response' in row else None,
            'reasoning_validated': False}


def summarize(predictions):
    if not predictions:
        raise ValueError('Empty evaluation')
    keys = ('answer_correct', 'terminated_correct', 'ended_with_eos', 'truncated')
    return {'n': len(predictions), **{k: sum(p['score'][k] for p in predictions) for k in keys},
            'parse_status': dict(Counter(p['score']['parse_status'] for p in predictions)),
            'reference_exact_matches': sum(p['score']['reference_exact_match'] is True for p in predictions),
            'output_tokens': sum(p['generated_tokens'] for p in predictions)}


def engineering_gate(cfg, steps, throughput, stats, nll):
    return {'passed': bool(steps == cfg['steps'] and throughput['profile_complete']
                and stats['n'] == cfg['train_count']
                and stats['terminated_correct'] >= cfg['overfit_required_correct']
                and stats['truncated'] == 0 and math.isfinite(nll) and nll < cfg['overfit_max_nll']),
            'scope': 'engineering_memorization_feasibility_only; no proof-validity or treatment-effect claim'}


def validate_rows(cfg, train, dev, tokenizer):
    index = parent_index(cfg)
    if sha256_file(SELECTION) != cfg['selection_sha256']:
        raise ValueError('Frozen engineering selection differs')
    selection = read_jsonl(SELECTION)
    expected_train = [r['problem_id'] for r in selection]
    expected_dev = [r['id'] for r in sorted((p for p in index.values()
        if p['dataset'] == 'gsm8k' and p['partition'] == 'development'), key=lambda r: r['rank'])[:cfg['dev_count']]]
    if len(train) != cfg['train_count'] or len(dev) != cfg['dev_count'] or [r['problem_id'] for r in train] != expected_train or [r['problem_id'] for r in dev] != expected_dev:
        raise ValueError('Predetermined train/dev count or order differs')
    groups = set()
    for split, rows in [('audit_draw', train), ('development', dev)]:
        for row in rows:
            parent = index[row['problem_id']]
            if parent['dataset'] != 'gsm8k' or parent['original_split'] != 'train' or parent['partition'] != split or parent['exclusions']:
                raise ValueError('Ineligible or held-out problem')
            if row['group_id'] != parent['group_id'] or row['group_id'] in groups:
                raise ValueError('Duplicate or train/dev group overlap')
            groups.add(row['group_id'])
            if sha(row['prompt']) != parent['problem_sha256'] or sha(row['answer']) != parent['answer_sha256']:
                raise ValueError('Original prompt/answer bytes differ')
            if scalar(row['answer']) is None:
                raise ValueError('Unresolved reference scalar')
    encoded = [encode_row(r, tokenizer, cfg['max_length']) for r in train]
    for row, enc, decision in zip(train, encoded, selection):
        if row['source'] != decision or decision['reason'] != 'accepted' or sha(row['response']) != decision['response_sha256']:
            raise ValueError('Frozen accepted candidate differs')
        if row['path_id'] != str(decision['candidate_index']):
            raise ValueError('Candidate path identity differs')
        if any(enc[k] != decision[k] for k in ('n_prompt', 'n_supervised', 'n_processed')):
            raise ValueError('C017 response token accounting differs')
        if not score_completion(row, row['response'], True, False)['terminated_correct']:
            raise ValueError('Selected reference fails frozen numeric scorer')
    from src.sft_data import prefix
    for row in train+dev:
        length = len(tokenizer(prefix(row['prompt']), add_special_tokens=False)['input_ids'])
        if length + cfg['max_new_tokens'] > cfg['max_length']:
            raise ValueError('Prompt plus generation allowance exceeds context cap')
    schedule = update_schedule(len(train), cfg['steps'], cfg['batch_size'], cfg['seed'])
    counts = Counter(i for update in schedule for i in update)
    if set(counts) != set(range(32)) or set(counts.values()) != {32}:
        raise ValueError('E013 must present each frozen response exactly 32 times')
    budget = json.loads(json.dumps(budget_report(encoded, schedule, cfg['microbatch_size'])))
    return encoded, schedule, budget


def load_frozen(tokenizer):
    cfg = json.loads(CONFIG.read_text())
    folder = Path(cfg['data_dir'])
    release = json.loads(RELEASE.read_text())
    if sha256_file(CONFIG) != release['config_sha256'] or sha256_file(folder/'manifest.json') != release['manifest_sha256']:
        raise ValueError('E013 release differs')
    manifest = json.loads((folder/'manifest.json').read_text())
    if manifest['config_sha256'] != sha256_file(CONFIG) or set(manifest['source_files_sha256']) != set(source_files()):
        raise ValueError('Prepared source/configuration set differs')
    for name, expected in manifest['source_files_sha256'].items():
        historical = subprocess.check_output(['git', 'show', f"{manifest['source_commit']}:{name}"])
        if sha256_file(name) != expected or hashlib.sha256(historical).hexdigest() != expected:
            raise ValueError('Runtime or historical source differs from preparation')
    for name, expected in manifest['files_sha256'].items():
        if Path(name).name != name or sha256_file(folder/name) != expected:
            raise ValueError('Frozen data artifact differs')
    train, dev = read_jsonl(folder/'train.jsonl'), read_jsonl(folder/'dev.jsonl')
    encoded, schedule, budget = validate_rows(cfg, train, dev, tokenizer)
    if schedule != json.loads((folder/'schedule.json').read_text()) or budget != json.loads((folder/'budget.json').read_text()):
        raise ValueError('Schedule/exposure/token budget differs')
    return cfg, manifest, train, dev, encoded, schedule, budget
