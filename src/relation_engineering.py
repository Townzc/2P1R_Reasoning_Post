"""Frozen E011 input, scoring and provenance checks. No model execution here."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

from src.relation_transport import allocation_schedule, views, render_prompt
from src.relation_verifier import check_certificate, parse_prompt, solve, FINAL
from src.sft_data import encode_row, budget_report, sha256_file

CONFIG = Path('configs/relation_engineering_e011/overfit.json')
RELEASE = Path('configs/relation_engineering_e011/release.json')
C014 = Path('reports/relation_transport_c014_r1')
SOURCES = [
    'src/relation_engineering.py', 'src/relation_experiment.py',
    'src/relation_transport.py', 'src/relation_verifier.py', 'src/sft_data.py',
    'scripts/prepare_relation_engineering.py', 'scripts/run_relation_engineering.py',
    'scripts/audit_relation_engineering_outputs.py', 'scripts/run_bounded.py',
    'scripts/audit_family_matching.py', 'scripts/verify_relation_cpu_audit.py',
    'scripts/run_relation_cpu_audit.py', 'src/relation_audit.py', 'src/relation_probes.py',
    'configs/models.lock.json', 'configs/resource_budget.json', str(CONFIG),
    'requirements.txt', 'requirements-diagnostics.txt',
]


def dump(path, obj):
    with Path(path).open('x') as f:
        json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def provenance(extra=()):
    if git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Publish clean tracked source before execution')
    files = sorted(set(SOURCES) | set(extra))
    git('ls-files', '--error-unmatch', *files)
    commit = git('rev-parse', 'HEAD')
    if commit != git('rev-parse', 'origin/main'):
        raise ValueError('Fetch and synchronize published origin/main first')
    return {'source_commit': commit, 'source_worktree_dirty': False,
            'source_files_sha256': {p: sha256_file(p) for p in files}}


def expected_ids(cfg, split):
    return [f"c014_s{cfg[split+'_seed']:05d}_i{i:03d}" for i in range(cfg[split+'_count'])]


def original_worlds(cfg):
    """Read existing archived records; do not regenerate or select by any score."""
    from scripts.verify_relation_cpu_audit import load_archive
    if sha256_file(C014/'summary.json') != cfg['c014_summary_sha256']:
        raise ValueError('C014 summary identity differs')
    summary = json.loads((C014/'summary.json').read_text())
    if summary['status'] != 'passed_cpu_gates' or summary['worlds'] != 10000:
        raise ValueError('C014 gates did not pass')
    wanted = expected_ids(cfg, 'train') + expected_ids(cfg, 'dev')
    # Shards follow the frozen 100-world seed blocks, 1000 worlds per shard.
    shards = sorted({(cfg[k+'_seed']-401)//10 for k in ('train', 'dev')})
    found = {}
    for index in shards:
        name = f'records_{index:03d}.json'
        if sha256_file(C014/name) != summary['files_sha256'][name]:
            raise ValueError('C014 shard hash mismatch')
        for w in load_archive(C014/name):
            if w['world_id'] in wanted:
                if w['world_id'] in found:
                    raise ValueError('Duplicate source identity')
                found[w['world_id']] = w
    if set(found) != set(wanted):
        raise ValueError('Missing predetermined source world')
    return [found[k] for k in wanted]


def materialize(worlds, cfg, tokenizer):
    """Derive model-facing rows and verify every reference with exposed facts."""
    from scripts.verify_relation_cpu_audit import check_record
    train_ids, dev_ids = expected_ids(cfg, 'train'), expected_ids(cfg, 'dev')
    if [w['world_id'] for w in worlds] != train_ids + dev_ids:
        raise ValueError('Engineering identities/order differ')
    orbits = set()
    for i, w in enumerate(worlds):
        if w['split'] != ('probe_fit' if i < len(train_ids) else 'probe_audit'):
            raise ValueError('Wrong pre-augmentation split')
        check_record(w, tokenizer, cfg['max_length'])
        key = w['audit']['orbit']['key']
        if key in orbits:
            raise ValueError('Conservative world group overlaps')
        orbits.add(key)
    train, evaluation = [], {'train': [], 'dev': []}
    for w in worlds:
        base = {'problem_id': w['world_id'], 'prompt': w['prompt'], 'answer': w['answer'], 'view': 'clean'}
        if w['world_id'] in train_ids:
            evaluation['train'].append(base)
            train.extend({**base, 'path_id': str(i), 'response': r} for i, r in enumerate(w['responses']))
        else:
            for name in cfg['dev_views']:
                q, answer = views(w)[name]
                prompt = render_prompt(q)
                if solve(parse_prompt(prompt)) != [answer]:
                    raise ValueError('Development view label differs from exposed solver')
                evaluation['dev'].append({**base, 'view': name, 'prompt': prompt, 'answer': answer})
    encoded = [encode_row(r, tokenizer, cfg['max_length']) for r in train]
    if {(r['n_supervised'], r['n_processed']) for r in encoded} != {(101, 1137)}:
        raise ValueError('Frozen clean token lengths differ')
    allocation = allocation_schedule(train_ids, cfg['assignment_seed'], cfg['cycles'])
    row_index = {(r['problem_id'], int(r['path_id'])): i for i, r in enumerate(train)}
    schedule = [[row_index[(w, route)] for w, route in zip(u['world_ids'], u['multi'])]
                for u in allocation['updates']]
    validate_schedule(train, schedule, cfg)
    budget = json.loads(json.dumps(budget_report(encoded, schedule, cfg['microbatch_size'])))
    return train, evaluation, encoded, schedule, budget


def validate_schedule(rows, schedule, cfg):
    if len(schedule) != cfg['steps']:
        raise ValueError('Wrong update count')
    counts = Counter()
    for update in schedule:
        if len(update) != cfg['batch_size'] or any(type(i) is not int or i < 0 or i >= len(rows) for i in update):
            raise ValueError('Invalid update indices')
        if len({rows[i]['problem_id'] for i in update}) != cfg['batch_size']:
            raise ValueError('Repeated problem in an update')
        if sorted(rows[i]['path_id'] for i in update) != ['0', '1', '2', '3']:
            raise ValueError('Route slots do not balance within update')
        counts.update(update)
    if set(counts) != set(range(len(rows))) or set(counts.values()) != {cfg['cycles']}:
        raise ValueError('Every route must receive the frozen cycle dose')


def score_completion(row, text, eos, truncated):
    # Only outer ASCII whitespace is normalized; internal text and specials stay.
    normalized = text.strip(' \t\r\n')
    proof = check_certificate(row['prompt'], normalized)
    lines = normalized.splitlines()
    last = FINAL.fullmatch(lines[-1]) if lines else None
    answer = int(last.group(1)) if last else None
    return {'certificate': proof, 'answer_correct': answer == row['answer'],
            'complete_correct': bool(proof['valid'] and eos and not truncated),
            'ended_with_eos': bool(eos), 'truncated': bool(truncated),
            'normalization': 'outer_ascii_whitespace_only'}


def summarize(predictions):
    n = len(predictions)
    if not n:
        raise ValueError('Empty evaluation')
    keys = ('answer_correct', 'complete_correct', 'ended_with_eos', 'truncated')
    return {'n': n, **{k: sum(p['score'][k] for p in predictions) for k in keys},
            'failure_reasons': dict(Counter(p['score']['certificate']['reason'] for p in predictions))}


def load_frozen(tokenizer, require_release=True):
    from scripts.verify_relation_cpu_audit import load_archive
    cfg = json.loads(CONFIG.read_text())
    folder = Path(cfg['data_dir'])
    manifest = json.loads((folder/'manifest.json').read_text())
    if require_release:
        release = json.loads(RELEASE.read_text())
        if sha256_file(folder/'manifest.json') != release['manifest_sha256'] or sha256_file(CONFIG) != release['config_sha256']:
            raise ValueError('Release identity mismatch')
    if manifest['config_sha256'] != sha256_file(CONFIG):
        raise ValueError('Prepared configuration differs')
    for name, expected in manifest['files_sha256'].items():
        if Path(name).name != name or sha256_file(folder/name) != expected:
            raise ValueError('Prepared artifact hash mismatch')
    if set(manifest['source_files_sha256']) != set(SOURCES):
        raise ValueError('Source dependency set differs')
    for path, expected in manifest['source_files_sha256'].items():
        historical = subprocess.check_output(['git', 'show', f"{manifest['source_commit']}:{path}"])
        if sha256_file(path) != expected or hashlib.sha256(historical).hexdigest() != expected:
            raise ValueError('Prepared runtime source differs')
    worlds = load_archive(folder/'worlds.json')
    if worlds != original_worlds(cfg):
        raise ValueError('Compact data differ from fixed C014 source records')
    train, evaluation, encoded, schedule, budget = materialize(worlds, cfg, tokenizer)
    if schedule != json.loads((folder/'schedule.json').read_text()) or budget != json.loads((folder/'budget.json').read_text()):
        raise ValueError('Stored schedule or exact token accounting differs')
    return cfg, manifest, train, evaluation, encoded, schedule, budget
