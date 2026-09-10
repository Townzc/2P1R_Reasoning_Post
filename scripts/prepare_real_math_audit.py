"""Reconstruct original problem splits and freeze parent draws before solutions."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile

import pyarrow.parquet as pq

from scripts.fetch_real_math_sources import SUBJECTS, digest, specifications
from src.real_math_audit import assign_partitions, group_records, last_boxed, normalized, sha


def write_json(path, value):
    with Path(path).open('x') as out:
        json.dump(value, out, indent=2, ensure_ascii=False, sort_keys=True)
        out.write('\n')


def write_jsonl(path, rows):
    with Path(path).open('x') as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def math_key(r):
    level = r.get('level')
    if isinstance(level, str):
        m = re.fullmatch(r'Level ([1-5])', level)
        level = int(m[1]) if m else None
    return (r['problem'], r['solution'], r.get('subject', r.get('type')), level)


def source_records(cache, config):
    records, gsm_test = [], []
    for split in ('train', 'test'):
        rows = [json.loads(line) for line in (cache / f'gsm8k_{split}.jsonl').read_text().splitlines()]
        if len(rows) != (7473 if split == 'train' else 1319):
            raise ValueError('Unexpected official GSM8K population')
        if split == 'test':
            gsm_test = rows
        for i, r in enumerate(rows):
            records.append({'id': f'gsm8k/{split}/{i:05d}', 'dataset': 'gsm8k',
                            'original_split': split, 'source_locator': f'{split}.jsonl:{i+1}',
                            'problem': r['question'], 'reference': r['answer'],
                            'answer': r['answer'].rsplit('####', 1)[-1].strip(),
                            'subject': None, 'level': None, 'stratum': 'gsm8k'})
    mirror_counts, source_rows = Counter(), []
    for subject in SUBJECTS:
        for split in ('train', 'test'):
            rs = pq.read_table(cache / f'math_{subject}_{split}.parquet').to_pylist()
            for i, r in enumerate(rs):
                source_rows.append((split, subject, i, r))
                mirror_counts[split] += 1
    id_rows, id_hub_split_counts = [], Counter()
    for hub_split in ('train', 'test'):
        for r in pq.read_table(cache / f'math_benchmark_{hub_split}.parquet').to_pylist():
            split = r['unique_id'].split('/')[0]
            if not re.fullmatch(r'(train|test)/[a-z_]+/\d+\.json', r['unique_id']):
                raise ValueError('Unrecognized original MATH file identifier')
            id_hub_split_counts[f'{hub_split}_hub__{split}_original'] += 1
            id_rows.append(r)
    original_counts = Counter(r['unique_id'].split('/')[0] for r in id_rows)
    if mirror_counts != {'train': 7500, 'test': 5000}:
        raise ValueError('Split-preserving MATH population mismatch')
    merged = pq.read_table(cache / 'math_merged.parquet').to_pylist()
    if Counter(map(math_key, merged)) != Counter(math_key(r) for _, _, _, r in source_rows):
        raise ValueError('Author-linked merged mirror disagrees with split-preserving inventory')
    id_lookup = defaultdict(list)
    for r in id_rows:
        id_lookup[(normalized(r['problem']), normalized(r['solution']))].append(r)
    issues, id_verified, metadata_differences = [], 0, Counter()
    for split, subject, i, r in source_rows:
        candidates = id_lookup[(normalized(r['problem']), normalized(r['solution']))]
        ids = {x['unique_id'] for x in candidates if x['unique_id'].startswith(f'{split}/{subject}/')}
        verified = len(ids) == 1
        original_id = next(iter(ids)) if verified else None
        level = math_key(r)[3]
        source_locator = f'{subject}/{split}-00000-of-00001.parquet:row={i}'
        if verified:
            id_verified += 1
            good = next(x for x in candidates if x['unique_id'] == original_id)
            for field, a, b in zip(('problem', 'solution', 'subject', 'level'), math_key(r), math_key(good)):
                if a != b:
                    metadata_differences[field] += 1
        else:
            issues.append({'locator': source_locator, 'original_split': split,
                           'problem_sha256': sha(r['problem']),
                           'claimed_ids': sorted({x['unique_id'] for x in candidates})})
        pid = original_id or f'{split}/{subject}/unresolved-{sha(r["problem"])[:20]}'
        records.append({'id': 'math/' + pid, 'dataset': 'math',
                        'original_split': split, 'source_locator': source_locator,
                        'original_file_id': original_id, 'original_file_id_verified': verified,
                        'problem': r['problem'], 'reference': r['solution'],
                        'answer': last_boxed(r['solution']), 'subject': r['type'],
                        'level': level, 'stratum': f"{r['type']} / L{level}"})
    if len({r['id'] for r in records}) != len(records):
        raise ValueError('Reconstructed problem IDs are not unique')
    # Only parent metadata are used. No generated robustness answer is scored.
    symbolic = []
    with zipfile.ZipFile(cache / 'gsm_symbolic.zip') as archive:
        for name in sorted(archive.namelist()):
            if '/templates/' not in name or not name.endswith('.json'):
                continue
            r = json.loads(archive.read(name))
            original_id = r['id_orig']
            if not isinstance(original_id, int) or not 0 <= original_id < len(gsm_test):
                raise ValueError('GSM-Symbolic template parent outside official test')
            symbolic.append({'template': name.split('/templates/')[1], 'parent_id': f'gsm8k/test/{original_id:05d}',
                             'template_question_equals_parent': normalized(r['question']) == normalized(gsm_test[original_id]['question'])})
    return records, {'gsm8k': {'train': 7473, 'test': 1319}, 'math_original': dict(mirror_counts),
                     'math_id_mirror_claimed_counts': dict(original_counts),
                     'math_original_file_ids_verified': id_verified,
                     'math_unresolved_original_ids': issues,
                     'math_verified_id_rows_raw_field_differences': dict(metadata_differences),
                     'math_id_mirror_duplicate_id_rows': len(id_rows)-len({r['unique_id'] for r in id_rows}),
                     'math_author_linked_merged_multiset_crosscheck': True,
                     'math_mirror_hub_labels': dict(id_hub_split_counts),
                     'math_original_archive_direct_access': 'author archive returned HTTP 403; original HF archive/loader returned HTTP 401; not used',
                     'math_split_evidence': 'All original problem/solution/subject/level bytes match author-linked merged mirror. Normalize only whitespace to link problem+reference to original file IDs with matching split/subject; quarantine unresolved IDs, preserve original unknown levels and record mirror metadata alterations. Historical loader maps MATH/train and MATH/test.',
                     'symbolic_templates': len(symbolic),
                     'symbolic_unique_official_test_parents': len({r['parent_id'] for r in symbolic}),
                     'symbolic': symbolic}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default='configs/diagnostics/real_math_c017.json')
    p.add_argument('--cache', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--private-out', required=True)
    args = p.parse_args()
    started = time.monotonic()
    c, cache = json.loads(Path(args.config).read_text()), Path(args.cache)
    out, private = Path(args.out), Path(args.private_out)
    out.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    try:
        receipts = {}
        for name, url, _ in specifications(c):
            r = json.loads((cache / f'{name}.receipt.json').read_text())
            if digest(cache / name) != r['sha256'] or r['url'] != url:
                raise ValueError(f'Source provenance mismatch: {name}')
            receipts[name] = r
        records, source_check = source_records(cache, c)
        records.sort(key=lambda r: r['id'])
        print(json.dumps({'source_records': len(records), 'stage': 'duplicate_and_template_join'}), flush=True)
        groups, edges = group_records(records, c['question_jaccard_threshold'], c['question_shingle_words'])
        assign_partitions(records, c, groups)
        public = []
        for r in records:
            public.append({k: v for k, v in r.items() if k not in ('problem', 'reference', 'answer')} |
                          {'problem_sha256': sha(r['problem']), 'normalized_problem_sha256': sha(normalized(r['problem'])),
                           'reference_sha256': sha(r['reference']), 'answer_sha256': sha(r['answer'] or '')})
        write_jsonl(out / 'problem_manifest.jsonl', public)
        write_jsonl(out / 'question_overlap_edges.jsonl', edges)
        write_jsonl(private / 'problem_records.jsonl', records)
        write_json(out / 'source_receipts.json', receipts)
        write_json(out / 'source_split_verification.json', source_check)
        partitions = defaultdict(Counter)
        losses = defaultdict(Counter)
        strata = defaultdict(Counter)
        for r in records:
            partitions[r['dataset']][r['partition']] += 1
            if r['exclusions']:
                losses[r['dataset']][r['exclusions'][0]] += 1
            if r['original_split'] == 'train':
                strata[r['partition']][r['stratum']] += 1
        summary = {'partitions': dict(partitions), 'first_reason_exclusions': dict(losses),
                   'strata_by_partition': dict(strata), 'overlap_edge_types': dict(Counter(e['kind'] for e in edges)),
                   'group_policy': 'Union of normalized exact, exact five-token-shingle Jaccard >=.8, and number-masked Jaccard >=.8; conservative candidate grouping, not semantic identity proof.',
                   'seconds': time.monotonic()-started}
        write_json(out / 'problem_summary.json', summary)
        freeze = {'phase': 'before any released solution shards retrieved',
                  'created_at_utc': datetime.now(timezone.utc).isoformat(),
                  'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  'config_sha256': digest(Path(args.config)),
                  'problem_manifest_sha256': digest(out / 'problem_manifest.jsonl'),
                  'private_problem_records_sha256': digest(private / 'problem_records.jsonl'),
                  'gpu_seconds': 0, 'teacher_calls': 0, 'evaluation_calls': 0}
        write_json(out / 'freeze.json', freeze)
        print(json.dumps(summary), flush=True)
    except Exception as exc:
        write_json(out / 'failure.json', {'type': type(exc).__name__, 'message': str(exc),
                                        'seconds': time.monotonic()-started})
        raise


if __name__ == '__main__':
    main()
