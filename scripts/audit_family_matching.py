"""C009: fixed-inventory CPU feasibility and matching-loss diagnostic, no model."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import importlib.metadata
import time

from scripts.audit_legal_support import FAMILIES, TRAIN_BLOCKS, TRAIN_SHA256, allocate_distinct_classes, load_training_problems
from scripts.audit_pilot_structure_bias import identity_operations
from src.countdown_smoke import canonical, safe_parse, value, render_trace, verify_expression
from src.path_family_matching import family_structure_assignment, find_supported_keys, greedy_blocks
from src.pilot_data import surface_response
from src.sft_data import encode_row

CENSUS_SHA = '42c00622cdf8e9953d50f4a5c781b28e054198dff72915524577fe5a6407f5ef'
STREAM_SHA = 'fa0563f030ffaa810f23e4eb5e9c63a2e12096f2dc675128a9bd9a9362c338d8'
CONFIG = Path('configs/diagnostics/family_matching_v1.json')
PROTOCOL = Path('docs/experiments/C009_token_structure_block_matching.md')
SOURCES = [CONFIG, PROTOCOL, TRAIN_BLOCKS, Path('configs/models.lock.json'),
           Path('scripts/audit_family_matching.py'), Path('src/path_family_matching.py'),
           Path('scripts/audit_legal_support.py'),
           Path('src/sft_data.py'), Path('src/countdown_smoke.py'),
           Path('scripts/audit_pilot_structure_bias.py'), Path('src/pilot_data.py')]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def numeric_features(tree):
    values, operators = [], Counter()
    def visit(t, root=False):
        if t[0] == 'n':
            return 0
        depth = 1 + max(visit(t[1]), visit(t[2]))
        operators[t[0]] += 1
        if not root:
            values.append(value(t))
        return depth
    depth = visit(tree, root=True)
    _, events = identity_operations(tree)
    return {'identity_nodes': len(events), 'zero_nodes': sum(v == 0 for v in values),
            'one_nodes': sum(v == 1 for v in values), 'negative_nodes': sum(v < 0 for v in values),
            'fraction_nodes': sum(v.denominator != 1 for v in values), 'depth': depth,
            'max_abs_intermediate': float(max(map(abs, values))),
            'exact_nonroot_intermediates': [str(v) for v in values], 'operators': dict(operators)}


def verified_tokenizer(path):
    from transformers import AutoTokenizer
    lock = json.loads(Path('configs/models.lock.json').read_text())['main']
    hashes = {}
    for name in ('config.json', 'tokenizer.json', 'vocab.json', 'merges.txt', 'tokenizer_config.json'):
        expected = next(f for f in lock['files'] if f['rfilename'] == name)
        data = (path / name).read_bytes()
        blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
        if blob != expected['blobId'] or len(data) != expected['size']:
            raise ValueError(f'Original tokenizer bytes mismatch: {name}')
        hashes[name] = {'git_blob_sha1': blob, 'sha256': digest(data), 'bytes': len(data)}
    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, use_fast=True)
    if not tokenizer.is_fast:
        raise ValueError('Fast tokenizer with exact offsets required')
    return tokenizer, {'repo_id': lock['repo_id'], 'revision': lock['tokenizer_revision'], 'files': hashes}


def encode_inventory(archive, tokenizer, max_length):
    compressed = archive.read_bytes()
    if digest(compressed) != CENSUS_SHA:
        raise ValueError('C008 compressed stream changed')
    raw = gzip.decompress(compressed)
    if digest(raw) != STREAM_SHA:
        raise ValueError('C008 canonical JSONL stream changed')
    problems = {p['problem_id']: p for p in load_training_problems('.')}
    blocks = json.loads(TRAIN_BLOCKS.read_text())
    prompts = {p['problem']['problem_id']: p['problem']['prompt'] for b in blocks for p in b['problems']}
    seen, records, excluded = set(), [], []
    for line in raw.splitlines():
        r = json.loads(line)
        p = problems[r['problem_id']]
        key = (r['problem_id'], r['expression'])
        if key in seen or any(r[k] != p[k] for k in ('numbers', 'target')):
            raise ValueError('Duplicate or altered original problem')
        seen.add(key)
        t = safe_parse(r['expression'])
        _, events = identity_operations(t)
        family = FAMILIES[0] if events else FAMILIES[1]
        if (not verify_expression(r['expression'], r['numbers'], r['target'])
                or canonical(t) != r['ac_class']
                or canonical(t, structure_only=True) != r['canonical_structure']
                or family != r['identity_family'] or events != r['identity_operations']):
            raise ValueError('C008 expression metadata mismatch')
        row = {k: r[k] for k in ('problem_id', 'numbers', 'target', 'expression', 'ac_class')}
        row.update(family=family, structure_id=r['canonical_structure'], prompt=prompts[r['problem_id']],
                   response=render_trace(t), path_id=r['ac_class'])
        try:
            enc = encode_row(row, tokenizer, max_length)
        except ValueError as error:
            if 'no truncation allowed' not in str(error):
                raise
            excluded.append({'problem_id': r['problem_id'], 'expression': r['expression'], 'reason': 'max_length'})
            # Keep legality inventory with absent lengths for raw-support counts.
            records.append(dict(row, encodable=False, numeric_features=numeric_features(t)))
            continue
        lengths = []
        for v in range(4):
            variant = dict(row, response=surface_response(row['response'], v))
            try:
                lengths.append(encode_row(variant, tokenizer, max_length)['n_supervised'])
            except ValueError as error:
                if 'no truncation allowed' not in str(error):
                    raise
                lengths.append(None)
        row.update({k: enc[k] for k in ('n_prompt', 'n_supervised', 'n_processed', 'response_hash')})
        row.update(encodable=True, surface_lengths=lengths,
                   surface_compatible=all(x == enc['n_supervised'] for x in lengths),
                   numeric_features=numeric_features(t))
        records.append(row)
    if len(records) != 25846 or {r['problem_id'] for r in records} != set(problems):
        raise ValueError('Incomplete C008 inventory')
    return sorted(records, key=lambda r: (r['problem_id'], r['expression'])), problems, excluded


def disjoint(rows):
    return allocate_distinct_classes(*[{r['ac_class'] for r in rows if r['family'] == f} for f in FAMILIES], 4) is not None


def per_problem_support(records):
    by_problem = defaultdict(list)
    for r in records:
        by_problem[r['problem_id']].append(r)
    result = {}
    for pid, rows in sorted(by_problem.items()):
        lengths = defaultdict(list)
        for r in rows:
            if r.get('encodable', True):
                lengths[r['n_supervised']].append(r)
        token_lengths, structure_lengths = [], []
        for length, rs in sorted(lengths.items()):
            if disjoint(rs):
                token_lengths.append(length)
                if family_structure_assignment(rs) is not None:
                    structure_lengths.append(length)
        result[pid] = {'raw_disjoint': disjoint(rows), 'encodable_disjoint': disjoint([r for r in rows if r.get('encodable', True)]),
                       'token_matched': bool(token_lengths), 'structure_matched': bool(structure_lengths),
                       'token_lengths': token_lengths, 'structure_lengths': structure_lengths}
    return result


def policy_filter(records, policy):
    rows = [r for r in records if r.get('encodable', True)]
    if policy == 'surface':
        return [r for r in rows if r['surface_compatible']]
    if policy == 'first_representative':
        chosen = {}
        for r in sorted(rows, key=lambda r: (r['ac_class'], r['expression'])):
            chosen.setdefault((r['problem_id'], r['n_supervised'], r['structure_id']), r)
        return list(chosen.values())
    if policy == 'first12':
        structures = defaultdict(set)
        for r in rows:
            structures[(r['problem_id'], r['n_supervised'])].add(r['structure_id'])
        allowed = {k: set(sorted(s)[:12]) for k, s in structures.items()}
        return [r for r in rows if r['structure_id'] in allowed[(r['problem_id'], r['n_supervised'])]]
    raise ValueError(policy)


def aggregate(stages, problems):
    result = {}
    previous = len(problems)
    for stage in ('raw_disjoint', 'encodable_disjoint', 'token_matched', 'structure_matched'):
        ids = sorted(p for p in problems if stages.get(p, {}).get(stage, False))
        result[stage] = {'count': len(ids), 'denominator': len(problems), 'previous_stage_count': previous, 'problem_ids': ids,
                         'target_histogram': dict(Counter(str(problems[p]['target']) for p in ids)),
                         'contains_input_one': sum(1 in problems[p]['numbers'] for p in ids)}
        previous = len(ids)
    return result


def inventory_counts(records):
    classes = defaultdict(set)
    for r in records:
        classes[(r['problem_id'], r['ac_class'])].add(r['family'])
    mixed = sorted([list(key) for key, labels in classes.items() if len(labels) == 2])
    by_problem = defaultdict(Counter)
    for r in records:
        by_problem[r['problem_id']][r['family']] += 1
    return {'ordered_records': len(records), 'problem_ac_classes': len(classes),
            'mixed_label_classes': len(mixed), 'mixed_class_ids': mixed,
            'ordered_four_plus_four_problem_ids': sorted(p for p, counts in by_problem.items() if all(counts[f] >= 4 for f in FAMILIES))}


def preview(blocks):
    """One four-update cycle; shared question order, distinct within-family paths."""
    rng = random.Random(17)
    result, totals = [], {}
    for block_id, block in enumerate(blocks):
        # Core packing returns key plus problem witnesses.
        witnesses = sorted(block['witnesses'].values(), key=lambda w: w['problem_id'])
        assignment = list(range(4))
        rng.shuffle(assignment)
        conditions = {}
        for family in FAMILIES:
            for allocation in ('paths', 'gcm'):
                condition = family + '_' + allocation
                updates = []
                for round_id in range(4):
                    chosen = []
                    for i, witness in enumerate(witnesses):
                        slots = sorted([s for s in witness['slots'] if s['family'] == family], key=lambda s: s['structure_id'])
                        index = (assignment[i] + (round_id if allocation == 'paths' else 0)) % 4
                        chosen.append(slots[index]['record'])
                    lengths = [r['n_processed'] for r in chosen]
                    padding = sum(max(lengths[j:j+2])*len(lengths[j:j+2])-sum(lengths[j:j+2]) for j in (0, 2))
                    updates.append({'round': round_id, 'records': chosen,
                                    'supervised_tokens': sum(r['n_supervised'] for r in chosen),
                                    'processed_tokens': sum(lengths), 'padding_tokens': padding,
                                    'structure_histogram': dict(Counter(r['structure_id'] for r in chosen))})
                conditions[condition] = updates
        reference = next(iter(conditions.values()))
        for updates in conditions.values():
            assert all(all(a[k] == b[k] for k in ('supervised_tokens', 'processed_tokens', 'padding_tokens')) for a, b in zip(reference, updates))
        for family in FAMILIES:
            assert all(a['structure_histogram'] == b['structure_histogram'] for a, b in zip(conditions[family+'_paths'], conditions[family+'_gcm']))
        result.append({'block_id': block_id, 'problem_ids': [w['problem_id'] for w in witnesses],
                       'identity_structures': block['identity_structures'], 'nonidentity_structures': block['nonidentity_structures'],
                       'witnesses': witnesses, 'assignment': assignment, 'conditions': conditions})
    for family in FAMILIES:
        for allocation in ('paths', 'gcm'):
            name = family + '_' + allocation
            updates = [u for b in result for u in b['conditions'][name]]
            rows = [r for u in updates for r in u['records']]
            feature_names = ('identity_nodes', 'zero_nodes', 'one_nodes', 'negative_nodes', 'fraction_nodes', 'depth', 'max_abs_intermediate')
            totals[name] = {'updates': len(updates), 'presentations': len(rows),
                           **{k: sum(u[k] for u in updates) for k in ('supervised_tokens', 'processed_tokens', 'padding_tokens')},
                           'mean_numeric_features': {k: sum(r['numeric_features'][k] for r in rows)/len(rows) if rows else None for k in feature_names},
                           'operator_histogram': dict(sum((Counter(r['numeric_features']['operators']) for r in rows), Counter()))}
    return result, totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--private-out', type=Path, required=True)
    args = parser.parse_args()
    for p in (args.out, args.private_out):
        if p.exists():
            raise FileExistsError(f'Immutable output exists: {p.name}')
    config = json.loads(CONFIG.read_text())
    if config != {'schema_version':1, 'per_family':4, 'max_length':384, 'schedule_cycles':1,
                  'microbatch_size':2, 'assignment_seed':17, 'max_structure_nodes':2000000,
                  'max_key_pair_checks':2000000, 'max_key_search_seconds':600}:
        raise ValueError('Unsupported protocol settings')
    sources = {str(p): digest(p.read_bytes()) for p in SOURCES}
    source_commit = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
    if subprocess.check_output(['git','status','--porcelain','--',*[str(p) for p in SOURCES]], text=True).strip():
        raise ValueError('Unpublished input/source changes')
    args.out.mkdir(parents=True)
    args.private_out.mkdir(parents=True)
    started = time.monotonic()
    tokenizer, provenance = verified_tokenizer(args.tokenizer)
    records, problems, excluded = encode_inventory(args.archive, tokenizer, config['max_length'])
    inventory_seconds = time.monotonic() - started
    print(f'Encoded and verified {len(records)} fixed-inventory solutions', flush=True)
    encoded = [r for r in records if r['encodable']]
    stream = b''.join((json.dumps(r, sort_keys=True, separators=(',',':'))+'\n').encode() for r in records)
    inventory_file = args.private_out/'tokenized_inventory.jsonl.gz'
    inventory_file.write_bytes(gzip.compress(stream, mtime=0))
    checking_started = time.monotonic()
    full = per_problem_support(records)
    ablations = {}
    for policy in ('surface', 'first_representative', 'first12'):
        subset = policy_filter(records, policy)
        ablations[policy] = {'records': len(subset), 'inventory_counts':inventory_counts(subset), 'stages': aggregate(per_problem_support(subset), problems)}
    serial = records
    for policy in ('surface', 'first_representative', 'first12'):
        serial = policy_filter(serial, policy)
        ablations['serial_through_'+policy] = {'records': len(serial), 'inventory_counts':inventory_counts(serial), 'stages': aggregate(per_problem_support(serial), problems)}
    problem_check_seconds = time.monotonic() - checking_started
    print('Per-problem checks and fixed policy emulations complete', flush=True)
    search_records = [r for r in encoded if r['n_supervised'] in full[r['problem_id']]['structure_lengths']]
    search = find_supported_keys(search_records, max_key_pair_checks=config['max_key_pair_checks'],
                                 max_structure_nodes=config['max_structure_nodes'], max_seconds=config['max_key_search_seconds'])
    packing = greedy_blocks(search['keys'])
    blocks, totals = preview(packing['blocks'])
    write_json(args.out/'shared_keys.json', search)
    write_json(args.out/'block_witnesses.json', {'blocks': blocks, 'condition_totals': totals})
    write_json(args.out/'policy_emulations.json', ablations)
    selected = sorted(p for b in blocks for p in b['problem_ids'])
    supported = sorted({p for k in search['keys'] for p in k['problem_ids']})
    with (args.out/'per_problem.jsonl').open('w') as stream_out:
        for pid, p in sorted(problems.items()):
            row = {k: p[k] for k in ('problem_id','numbers','target')}
            row.update(full[pid], shared_key_supported=pid in supported, greedy_selected=pid in selected)
            stream_out.write(json.dumps(row, sort_keys=True)+'\n')
    summary = {'diagnostic_id':'C009', 'completed_at_utc':datetime.now(timezone.utc).isoformat(),
               'source_commit':source_commit, 'source_sha256':sources, 'configuration':config,
               'status':'complete' if search['complete'] else 'incomplete_shared_key_search',
               'runtime_seconds':time.monotonic()-started, 'gpu_process_seconds':0,
               'phase_seconds':{'inventory_verification_and_tokenization':inventory_seconds,
                                'per_problem_and_policy_checks':problem_check_seconds, 'shared_key_search':search['elapsed_seconds']},
               'environment':{'python':sys.version.split()[0], **{p:importlib.metadata.version(p) for p in ('transformers','tokenizers','networkx')}},
               'original_train_sha256':TRAIN_SHA256, 'census_compressed_sha256':CENSUS_SHA, 'census_stream_sha256':STREAM_SHA,
               'tokenizer':provenance, 'inventory_records':len(records), 'encodable_records':len(encoded),
               'inventory_counts':inventory_counts(records),
               'length_exclusions':excluded, 'tokenized_compressed_sha256':digest(inventory_file.read_bytes()),
               'tokenized_stream_sha256':digest(gzip.decompress(inventory_file.read_bytes())),
               'stages':aggregate(full, problems),
               'shared_key_search':{k:v for k,v in search.items() if k!='keys'},
               'shared_key_count':len(search['keys']), 'shared_key_supported_problem_ids':supported,
               'search_input_records':len(search_records),
               'shared_key_supported_count':len(supported), 'greedy_block_count':len(blocks),
               'greedy_selected_problem_ids':selected, 'greedy_selected_count':len(selected),
               'packing_is_maximum':False, 'condition_totals':totals,
               'limitations':['Fixed selected 256 training questions; no model result or holdout access.',
                 'Identity labels are numerical trajectory properties, not semantic strategy categories.',
                 'Shared-key support is not disjoint packing capacity; greedy packing is a lower bound.',
                 'Capped search is incomplete, never a proof of infeasibility.',
                 'Surface/first-representative/first12 are controlled policy emulations, not a replay of historical solver order.',
                 'Cross-family numerical and operator distributions are descriptive residuals, not matched causal controls.',
                 'These are CPU schedule witnesses, not an approved training dataset or GPU configuration.']}
    if sources != {str(p):digest(p.read_bytes()) for p in SOURCES}:
        raise ValueError('Source bytes changed during execution')
    summary['output_sha256'] = {p.name:digest(p.read_bytes()) for p in args.out.iterdir() if p.is_file()}
    write_json(args.out/'summary.json', summary)
    print(json.dumps({k:summary[k] for k in ('status','runtime_seconds','shared_key_count','shared_key_supported_count','greedy_block_count','greedy_selected_count')}, sort_keys=True), flush=True)

if __name__ == '__main__':
    main()
