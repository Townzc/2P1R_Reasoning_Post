"""Create-only OT3 or paired-AM input construction after one exact path-level CR.

Reads pinned local bytes only. No downloads, model inference, symbolic scoring,
training, cloud writes, or automatic retry. Partial output is evidence, not cache
that can silently admit a second invocation.
"""
import argparse
from collections import Counter, defaultdict
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random
import shutil
import sqlite3
import time

from experiments.p011 import data_contract as rules

SOURCE_FILES = ('experiments/p011/__init__.py', 'experiments/p011/data_contract.py',
                'scripts/prepare_p011_long_inputs.py')
REVIEW_SCOPE = 'p011-OT3-AM-long-data-construction-CR'
CUTOFF = datetime.datetime(2026, 10, 22, 5, tzinfo=datetime.timezone.utc)
OT3_TARGET = 4096
D_TARGET = 1024


def check_cutoff():
    if datetime.datetime.now(datetime.timezone.utc) >= CUTOFF:
        raise TimeoutError('P011 result cutoff reached; retain partial evidence')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def dump(path, obj):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write('\n')


def checked_file(item):
    path = Path(item['local_path'])
    if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
        raise ValueError(f'Pinned source bytes differ: {path}')
    return path


def admit_code(review_path, lock_path, owner_path=None, proposal_path=None):
    review = json.loads(Path(review_path).read_text())
    lock = json.loads(Path(lock_path).read_text())
    sources = {p: sha(p) for p in SOURCE_FILES}
    if (review['scope'] != REVIEW_SCOPE
            or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or review['source_files'] != sources
            or review['plan_sha256'] != rules.PLAN_SHA256
            or review['source_lock_sha256'] != sha(lock_path)
            or sha(review['local_report_path']) != review['report_sha256']
            or review['operational_details_accepted'] is not True
            or lock['plan_sha256'] != rules.PLAN_SHA256):
        raise ValueError('Real exact code-path review and pinned source lock required')
    if owner_path is None or proposal_path is None:
        raise ValueError('Direct R1/R3 owner amendment must accompany revised CR')
    owner = json.loads(Path(owner_path).read_text())
    if (owner['scope'] != 'p011-long-data-R1-R3-owner-amendment'
            or owner['authority'] != 'direct_human_reply_in_current_chat'
            or owner['original_plan_sha256'] != rules.PLAN_SHA256
            or owner['proposal_sha256'] != sha(proposal_path)
            or owner['B_rule'] != 'maximum_once_pass_tokens_across_original_A_cells'
            or owner['sampling_rule'] != 'shuffle_candidates_then_check_until_original_target_reached'
            or owner['required_real_re_review'] is not True
            or owner['budget_changed'] is not False
            or review['owner_amendment_sha256'] != sha(owner_path)
            or review['proposal_sha256'] != sha(proposal_path)):
        raise ValueError('Exact direct owner amendment and re-review binding required')
    return lock, sources


def read_rows(path):
    if path.suffix == '.parquet':
        import pyarrow.parquet as pq
        for batch in pq.ParquetFile(path).iter_batches(batch_size=256):
            yield from batch.to_pylist()
    elif path.suffix == '.jsonl':
        with path.open() as f:
            for line in f:
                yield json.loads(line)
    else:
        raise ValueError(f'Unsupported source format: {path.suffix}')


def benchmarks(lock):
    rows = []
    for item in lock['benchmarks']:
        original = list(read_rows(checked_file(item)))
        if len(original) != item['expected_rows']:
            raise ValueError('Benchmark cardinality differs')
        for i, row in enumerate(original):
            question = row[item['question_field']]
            rows.append({'benchmark': item['label'], 'source_row': i,
                         'problem': question, 'answer': row[item['answer_field']]})
    if len(rows) != 600:
        raise ValueError('Expected MATH500 + AIME30+30 + AMC40')
    return rows


def ingest(db, dataset, spec, progress):
    counts = Counter()
    for item in sorted(spec['files'], key=lambda x: x['source_file']):
        check_cutoff()
        path = checked_file(item)
        for index, row in enumerate(read_rows(path)):
            if index % 100 == 0:
                check_cutoff()
            counts['raw_rows'] += 1
            if dataset == 'ot3' and row['domain'] != 'math':
                counts['non_math_rows'] += 1
                continue
            question, answer = rules.conversation_pair(row)
            if dataset != 'ot3':
                if row['conversations'][0]['info']['category'] != 'math':
                    counts['non_math_rows'] += 1
                    continue
                score = row['conversations'][1]['info'].get('verify_score')
                if type(score) not in (int, float) or score < 0.9:
                    counts['author_verification_missing_or_below_0_9'] += 1
            # For AM, the pinned file is math.jsonl. Retain available author
            # metadata without adding a new correctness re-filter or re-score.
            metadata = {'difficulty': row.get('difficulty'), 'source': row.get('source'),
                        'turn_info': [x.get('info') for x in row['conversations']],
                        'original_system': row.get('system')}
            db.execute('INSERT INTO rows VALUES(?,?,?,?,?,?,?)',
                       (dataset, rules.parent_key(question), item['source_file'], index,
                        question, answer, json.dumps(metadata, ensure_ascii=False)))
            counts['math_rows'] += 1
        db.commit()
        progress.write(json.dumps({'utc': utc(), 'dataset': dataset,
            'source_file': item['source_file'], 'counts': dict(counts)}) + '\n')
        progress.flush()
    return dict(counts)


def grouped_rows(db, dataset, key):
    found = db.execute('SELECT source_file,row_index,question,response,metadata '
                       'FROM rows WHERE dataset=? AND parent=? ORDER BY source_file,row_index',
                       (dataset, key)).fetchall()
    return [{'source_file': p, 'source_row': i, 'question': q, 'response': a,
             'metadata': json.loads(m), 'path_id': f'{dataset}:{p}:{i}'}
            for p, i, q, a, m in found]


def ot3_inventory(db, tokenizer, decontam, out, progress):
    counts, histograms, eligible = Counter(), defaultdict(Counter), []
    keys = db.execute("SELECT parent,COUNT(*) FROM rows WHERE dataset='ot3' "
                      'GROUP BY parent ORDER BY parent').fetchall()
    candidates = [key for key, n in keys if n == 16]
    counts.update(total_math_parents=len(keys), cardinality_16_candidates=len(candidates),
                  full_pool_wrong_cardinality=len(keys) - len(candidates))
    random.Random(20261020).shuffle(candidates)
    with (out / 'PARENT_DISPOSITIONS.jsonl').open('x') as disposition:
        for number, key in enumerate(candidates, 1):
            check_cutoff()
            rows = grouped_rows(db, 'ot3', key)
            complete = all(rules.complete(x['response']) for x in rows)
            leaked = decontam.hit(key)
            too_long = False
            if complete and not leaked:
                for row in rows:
                    if rules.bounded_length(tokenizer, row['question'], row['response']) > rules.MAX_TOTAL_TOKENS:
                        too_long = True
                        break
            flags = {'incomplete': not complete,
                     'decontamination_hit': leaked,
                     'any_overlength': too_long if complete and not leaked else None}
            kept = complete and not leaked and not too_long
            counts['examined_candidate_parents'] += 1
            counts['eligible' if kept else 'excluded'] += 1
            for flag, value in flags.items():
                if value is True:
                    counts[flag] += 1
            # Preserve the full multiset, since cross-source parents may mix difficulty.
            difficulty = sorted((str(x['metadata']['difficulty']) for x in rows))
            histograms['kept' if kept else 'excluded'][json.dumps(difficulty)] += 1
            if kept:
                eligible.append(key)
            disposition.write(json.dumps({'parent_sha256': rules.identity(key),
                'row_count': 16, 'candidate_position': number, 'flags': flags, 'eligible': kept,
                'difficulty_multiset': difficulty}) + '\n')
            if number % 100 == 0:
                disposition.flush()
                progress.write(json.dumps({'utc': utc(), 'parents_filtered': number,
                    'eligible': len(eligible)}) + '\n')
                progress.flush()
            if len(eligible) == OT3_TARGET:
                break
    report = {'counts': dict(counts), 'filter_and_difficulty_denominator': 'examined_cardinality_16_prefix',
              'candidate_seed': 20261020, 'stopped_at_target': len(eligible) == OT3_TARGET,
              'unexamined_candidates': len(candidates) - counts['examined_candidate_parents'],
              'eligible_population_total_unknown_unless_exhausted': True,
              'difficulty_parent_histograms':
                     {k: dict(v) for k, v in histograms.items()}}
    if len(eligible) < OT3_TARGET:
        dump(out / 'INSUFFICIENT_OT3_PARENTS.json', dict(report,
             requires_owner_disposition=True, training_admitted=False))
        raise ValueError('OT3 eligible parents below4096; report without resampling')
    return eligible, report


def common_source_agreement(db, common_keys):
    """A1 metadata-only full-common-pool source check; no response tokenization."""
    maps = {}
    for teacher in ('am_thinking', 'am_qwen3'):
        by_parent = defaultdict(set)
        rows = db.execute("SELECT parent,json_extract(metadata,'$.turn_info[0].source') "
                          'FROM rows WHERE dataset=? GROUP BY parent,2', (teacher,))
        for parent, source in rows:
            if parent in common_keys:
                by_parent[parent].add(source)
        maps[teacher] = by_parent
    counts = Counter(common_parents=len(common_keys))
    for parent in common_keys:
        left, right = (maps[t][parent] for t in ('am_thinking', 'am_qwen3'))
        counts['matching_source_sets' if left == right else 'different_source_sets'] += 1
        counts['missing_source_in_either'] += int(None in left or None in right)
    return dict(counts, scope='full_common_parent_pool_original_human_info_source_sets')


def d_inventory(db, tokenizer, decontam, out, progress):
    common = db.execute("SELECT parent FROM rows WHERE dataset='am_thinking' INTERSECT "
                        "SELECT parent FROM rows WHERE dataset='am_qwen3' ORDER BY parent").fetchall()
    common = [key for (key,) in common]
    source_agreement = common_source_agreement(db, set(common))
    random.Random(20261021).shuffle(common)
    eligible, selected, counts = [], {}, Counter(total_common_parents=len(common))
    with (out / 'PARENT_DISPOSITIONS.jsonl').open('x') as f:
        for number, key in enumerate(common, 1):
            check_cutoff()
            pair = {teacher: rules.choose_d_row(key, teacher, grouped_rows(db, teacher, key))
                    for teacher in ('am_thinking', 'am_qwen3')}
            flags = {'decontamination_hit': decontam.hit(key)}
            for teacher, row in pair.items():
                flags[teacher + '_incomplete'] = not rules.complete(row['response'])
            check_length = not any(flags.values())
            for teacher, row in pair.items():
                flags[teacher + '_overlength'] = (rules.bounded_length(
                    tokenizer, row['question'], row['response']) > rules.MAX_TOTAL_TOKENS
                    if check_length else None)
            kept = not any(value is True for value in flags.values())
            counts['examined_common_parents'] += 1
            counts['eligible' if kept else 'excluded'] += 1
            for flag, value in flags.items():
                counts[flag] += int(value is True)
            if kept:
                eligible.append(key)
                # Keep only row identities; do not retain the entire common corpus in RAM.
                selected[key] = {t: r['path_id'] for t, r in pair.items()}
            f.write(json.dumps({'parent_sha256': rules.identity(key), 'candidate_position': number,
                'flags': flags, 'length_checks_performed': check_length,
                'eligible': kept, 'chosen': {t: r['path_id'] for t, r in pair.items()}}) + '\n')
            if number % 100 == 0:
                f.flush()
                progress.write(json.dumps({'utc': utc(), 'common_parents_filtered': number}) + '\n')
                progress.flush()
            if len(eligible) == D_TARGET:
                break
    if len(eligible) < D_TARGET:
        dump(out / 'INSUFFICIENT_COMMON_PARENTS.json', {'counts': dict(counts),
             'requires_owner_disposition': True, 'training_admitted': False})
        raise ValueError('D common eligible parents below1024; report before deciding')
    cells = {'D1': [], 'D2': []}
    for key in eligible:
        for cell, teacher in (('D1', 'am_thinking'), ('D2', 'am_qwen3')):
            cells[cell].append(next(x for x in grouped_rows(db, teacher, key)
                                    if x['path_id'] == selected[key][teacher]))
    return cells, {'counts': dict(counts), 'selected_parent_sha256':
                  [rules.identity(x) for x in eligible], 'candidate_seed': 20261021,
                  'filter_denominator': 'examined_common_parent_prefix',
                  'unexamined_candidates': len(common) - counts['examined_common_parents'],
                  'source_agreement': source_agreement, 'stopped_at_target': True}


def encode_and_plan(cells, tokenizer, out, mode):
    unique = {x['path_id']: x for rows in cells.values() for x in rows}
    summary = {}
    with (out / 'SELECTED_RAW.jsonl').open('x') as raw, (out / 'ENCODED.jsonl').open('x') as encoded:
        for path_id in sorted(unique):
            check_cutoff()
            row = unique[path_id]
            obj = rules.encode_complete(tokenizer, row['question'], row['response'], path_id)
            summary[path_id] = {k: v for k, v in obj.items() if k not in ('input_ids', 'labels')}
            raw.write(json.dumps(row, ensure_ascii=False) + '\n')
            encoded.write(json.dumps(obj, ensure_ascii=False) + '\n')
    small = {k: [summary[x['path_id']] for x in rows] for k, rows in cells.items()}
    once = {k: sum(x['n_supervised'] for x in rows) for k, rows in small.items()}
    budget = max(once.values())
    dump(out / 'FROZEN_DOSE.json', {'B': budget, 'U': (budget + 63999) // 64000,
         'once_pass_tokens': once, 'fixed_before_any_student_outcome': True,
         'dose_definition': 'max_once_pass_tokens_across_original_cells',
         'A7_exactly_one_pass_required': False,
         'owner_amendment_required': mode == 'ot3'})
    failures = {}
    for cell, rows in small.items():
        check_cutoff()
        try:
            planned = rules.whole_schedule(rows, budget)
        except ValueError as exc:
            failures[cell] = str(exc)
        else:
            dump(out / (cell + '_PLAN.json'), planned)
    dump(out / 'CELL_INVENTORY.json', {'cells': {k: [x['path_id'] for x in v] for k, v in small.items()},
         'whole_answer_planning_failures': failures, 'training_admitted': False})
    return failures


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('ot3', 'am'), required=True)
    p.add_argument('--source-lock', required=True)
    p.add_argument('--code-review', required=True)
    p.add_argument('--owner-amendment', required=True)
    p.add_argument('--amendment-proposal', required=True)
    p.add_argument('--tokenizer', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    check_cutoff()
    lock, sources = admit_code(args.code_review, args.source_lock,
                              args.owner_amendment, args.amendment_proposal)
    out = Path(args.out)
    datasets = ('ot3',) if args.mode == 'ot3' else ('am_thinking', 'am_qwen3')
    required_free = (3 * sum(f['bytes'] for d in datasets for f in lock['datasets'][d]['files']) + 1) // 2
    probe = out.parent
    while not probe.exists():
        probe = probe.parent
    disk_free = shutil.disk_usage(probe).free
    if disk_free < required_free:
        raise OSError('Free disk below1.5 times original input bytes; report before construction')
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    dump(out / 'INTENT.json', {'utc': utc(), 'mode': args.mode, 'source_files': sources,
         'source_lock_sha256': sha(args.source_lock), 'review_sha256': sha(args.code_review),
         'owner_amendment_sha256': sha(args.owner_amendment),
         'amendment_proposal_sha256': sha(args.amendment_proposal),
         'disk_free_bytes_at_entry': disk_free, 'required_free_bytes': required_free,
         'no_scoring': True, 'no_training': True})
    db = None
    try:
        for name, item in lock['tokenizer_files'].items():
            path = Path(args.tokenizer) / name
            if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
                raise ValueError('Pinned native tokenizer differs')
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True,
                                                   trust_remote_code=False, use_fast=True)
        if not tokenizer.is_fast:
            raise ValueError('Pinned fast tokenizer required')
        bench = benchmarks(lock)
        dump(out / 'BENCHMARKS.json', bench)
        decontam = rules.Decontamination([x['problem'] for x in bench])
        db = sqlite3.connect(out / 'RAW_INDEX.sqlite')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE rows(dataset TEXT,parent TEXT,source_file TEXT,row_index INTEGER,'
                   'question TEXT,response TEXT,metadata TEXT,PRIMARY KEY(dataset,source_file,row_index))')
        with (out / 'PROGRESS.jsonl').open('x') as progress:
            ingested = {k: ingest(db, k, lock['datasets'][k], progress) for k in datasets}
            db.execute('CREATE INDEX parents ON rows(dataset,parent,source_file,row_index)')
            db.commit()
            dump(out / 'INGESTED.json', ingested)
            if args.mode == 'ot3':
                eligible, report = ot3_inventory(db, tokenizer, decontam, out, progress)
                dump(out / 'FILTER_COUNTS.json', report)
                order, rows = rules.ot3_order(eligible, lambda key: grouped_rows(db, 'ot3', key))
                cells = {cell: [r for key in order[:n] for r in rows[key][:k]]
                         for cell, (n, k) in rules.CELLS.items()}
                dump(out / 'PARENT_ORDER.json', [rules.identity(x) for x in order])
            else:
                cells, report = d_inventory(db, tokenizer, decontam, out, progress)
                dump(out / 'FILTER_COUNTS.json', report)
            failures = encode_and_plan(cells, tokenizer, out, args.mode)
        db.close()
        db = None
        dump(out / 'CONSTRUCTION_COMPLETED.json', {'utc': utc(),
             'elapsed_seconds': time.monotonic() - started,
             'packages': {x: importlib.metadata.version(x) for x in ('transformers', 'tokenizers', 'pyarrow')},
             'planning_failures': failures, 'actual_A1_accepted': False,
             'training_admitted': False, 'old_outputs_rescored': 0})
        artifacts = {x.name: {'bytes': x.stat().st_size, 'sha256': sha(x)}
                     for x in sorted(out.iterdir()) if x.is_file()}
        dump(out / 'MANIFEST.json', {'files': artifacts})
    except BaseException as exc:
        dump(out / 'FAILED.json', {'utc': utc(), 'type': type(exc).__name__,
             'message': str(exc), 'automatic_retry_allowed': False})
        raise
    finally:
        if db is not None:
            db.close()


if __name__ == '__main__':
    main()
