"""Reconstruct the frozen C017 bank and whole-response allocation inputs on CPU.

Offline: inputs must already exist and match their original public receipts.
Never overwrite outputs, load model weights, redraw parents, or fill K shortfalls.
Public audit output contains hashes/counts/relative source paths, never raw text.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

PARENT_ROOT = Path('reports/real_math_c017_parents_r2')
SOLUTION_ROOT = Path('reports/real_math_c017_solutions_r2')
SCHEDULE_ROOT = Path('reports/real_math_c017_scale_proposal_r1')
CONFIG = Path('configs/diagnostics/real_math_c017.json')


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def jsonl_bytes(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows).encode()


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def write_rows(path, rows):
    with Path(path).open('xb') as stream:
        stream.write(jsonl_bytes(rows))


def read_rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def archive_rows(root, storage_file):
    meta = read(root / storage_file)
    raw = gzip.decompress(base64.b64decode((root / meta['archive']).read_bytes()))
    if sha_bytes(raw) != meta['sha256']:
        raise ValueError('Archived metadata checksum mismatch')
    return [json.loads(line) for line in raw.split(b'\n') if line], meta['sha256']


def restore_parents(public, source_records):
    """Join content to previously frozen metadata; never redraw partitions."""
    content = {r['id']: r for r in source_records}
    if len(content) != len(source_records) or set(content) != {r['id'] for r in public}:
        raise ValueError('Parent identity inventory mismatch')
    restored = []
    for p in public:
        c = content[p['id']]
        for field in ('problem', 'reference', 'answer'):
            if sha_bytes((c[field] or '').encode()) != p[field + '_sha256']:
                raise ValueError('Parent content checksum mismatch')
        for field in ('dataset', 'original_split', 'source_locator', 'subject', 'level', 'stratum'):
            if c[field] != p[field]:
                raise ValueError('Parent source metadata mismatch')
        restored.append({k: v for k, v in p.items() if not k.endswith('_sha256')} |
                        {k: c[k] for k in ('problem', 'reference', 'answer')})
    return restored


def validate_schedule(rows, saved):
    schedule = saved['updates']
    summary = saved['summary']
    counts = Counter()
    for update in schedule:
        if not update or any(type(i) is not int or not 0 <= i < len(rows) for i in update):
            raise ValueError('Invalid full-row update indices')
        counts.update(update)
    if set(counts) != set(range(len(rows))):
        raise ValueError('A selected pair was never exposed')
    supervised = sum(rows[i]['n_supervised'] * n for i, n in counts.items())
    processed = sum(rows[i]['n_processed'] * n for i, n in counts.items())
    if (len(schedule), supervised, processed) != (summary['optimizer_updates'],
            summary['supervised_response_tokens'], summary['processed_nonpadding_tokens']):
        raise ValueError('Schedule dose mismatch')
    if dict(counts) != {int(k): v for k, v in saved['row_exposures'].items()}:
        raise ValueError('Row exposure mismatch')
    return dict(updates=len(schedule), supervised_response_tokens=supervised,
                processed_nonpadding_tokens=processed, unique_pairs=len(rows),
                all_pairs_exposed=True, full_responses_only=True,
                row_exposure_range=[min(counts.values()), max(counts.values())])


def expected_selected_pairs(acquired, decisions, k):
    accepted = defaultdict(list)
    for d in decisions:
        if d['reason'] == 'accepted':
            accepted[d['problem_id']].append(d)
    return [d for parent in acquired for d in accepted[parent['id']][:k]]


def question_alias_inventory(parents):
    """Find exact question aliases in retained input and output JSONL records.

    Includes prepared inputs conservatively; a match does not by itself prove
    model execution. Whole-source index files are excluded and named explicitly.
    """
    from src.real_math_audit import normalized
    dev = {normalized(r['problem']): r['id'] for r in parents
           if r['dataset'] == 'gsm8k' and r['partition'] == 'development'}
    files = subprocess.check_output(['git', 'ls-files', 'runs', 'reports', 'experiments'], text=True).splitlines()
    evidence = []
    scanned = 0
    for name in files:
        p = Path(name)
        if p.suffix != '.jsonl' or p.name in ('future_train_pool_ids.jsonl',):
            continue
        scanned += 1
        hits = {}
        with p.open() as stream:
            for line in stream:
                if not line.strip():
                    continue
                r = json.loads(line)
                if not isinstance(r, dict):
                    continue
                for field in ('question', 'prompt', 'problem'):
                    text = r.get(field)
                    if not isinstance(text, str):
                        continue
                    key = normalized(text)
                    if key in dev:
                        pid = dev[key]
                        hits[pid] = dict(parent_id=pid, question_field=field,
                                         record_id=r.get('problem_id', r.get('id', r.get('row_id'))))
        if hits:
            evidence.append(dict(path=name, matches=list(hits.values())))
    ids = sorted({r['parent_id'] for e in evidence for r in e['matches']})
    return dict(scope='Exact whitespace-normalized question fields in tracked JSONL inputs/outputs',
                scanned_files=scanned, matching_development_ids=ids, evidence=evidence,
                excluded_large_unexecuted_pool_indices=['future_train_pool_ids.jsonl'],
                limitations=['Prepared input matches are conservatively counted, not asserted as model executions.',
                             'Paraphrases, wrapped prompts, compressed corpora and remote/private-only outputs remain unaudited.'])


def exposure_inventory(public):
    """Conservative ID exposure in all Git-tracked run records, not proof of freshness.

    A mentioned ID counts even if a run artifact was merely prepared. Aliased
    questions lacking original IDs and untracked/remote-only outputs are not
    certified by this search; limitations are part of the public audit.
    """
    dev = {r['id'] for r in public if r['dataset'] == 'gsm8k' and r['partition'] == 'development'}
    files = subprocess.check_output(['git', 'ls-files', 'runs'], text=True).splitlines()
    hits, scanned = {}, 0
    for name in files:
        path = Path(name)
        if path.suffix not in ('.json', '.jsonl', '.log', '.csv', '.txt', '.md'):
            continue
        data = path.read_bytes()
        scanned += 1
        ids = {s.decode() for s in re.findall(rb'gsm8k/train/\d{5}', data)} & dev
        if ids:
            hits[name] = sorted(ids)
    seen = set().union(*map(set, hits.values())) if hits else set()
    return dict(scope='All Git-tracked run text artifacts; original C017 GSM8K train IDs',
                scanned_files=scanned, development_parents=len(dev),
                conservatively_mentioned_parents=len(seen),
                not_found_in_this_inventory=len(dev - seen),
                mentioned_ids=sorted(seen), candidate_unmentioned_ids=sorted(dev - seen),
                evidence_files=hits,
                freshness_certified=False,
                limitations=['Mention is conservative and can include preparation rather than execution.',
                    'Question aliases without original IDs, private/untracked and remote-only outputs are not certified.',
                    'No claim of unknown pretraining decontamination.'])


def run(args):
    # Heavy CPU dependencies are optional for importing/testing the pure helpers.
    import pyarrow.parquet as pq
    from transformers import AutoTokenizer
    from scripts.prepare_real_math_audit import source_records
    from src.real_math_audit import normalized, check_candidate
    from src.sft_data import encode_row

    out = Path(args.out)
    if out.exists():
        raise FileExistsError('Choose a new output directory; preserve all earlier attempts')
    out.mkdir(parents=True)
    started = time.monotonic()
    cache, token_dir = Path(args.cache), Path(args.tokenizer_dir)
    config = read(CONFIG)
    freeze = read(PARENT_ROOT / 'freeze.json')
    try:
        if sha_file(CONFIG) != freeze['config_sha256']:
            raise ValueError('Historical C017 configuration changed')
        receipts = read(PARENT_ROOT / 'source_receipts.json') | read(SOLUTION_ROOT / 'solution_source_receipts.json')
        for name, receipt in receipts.items():
            if sha_file(cache / name) != receipt['sha256']:
                raise ValueError('Pinned source hash mismatch: ' + name)
        public, public_hash = archive_rows(PARENT_ROOT, 'manifest_storage.json')
        decisions, decision_hash = archive_rows(SOLUTION_ROOT, 'decision_storage.json')
        parents, _ = source_records(cache, config)
        parents = restore_parents(public, parents)
        if sha_bytes(jsonl_bytes(parents)) != freeze['private_problem_records_sha256']:
            raise ValueError('Reconstructed full private parent bytes differ')
        write_rows(out / 'problem_records.jsonl', parents)
        write_rows(out / 'candidate_decisions.jsonl', decisions)
        print(json.dumps(dict(stage='parents_verified', parents=len(parents))), flush=True)

        lock = read('configs/models.lock.json')['main']
        for name in ('config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json', 'merges.txt'):
            blob = (token_dir / name).read_bytes()
            expected = next(f['blobId'] for f in lock['files'] if f['rfilename'] == name)
            if hashlib.sha1(f'blob {len(blob)}\0'.encode() + blob).hexdigest() != expected:
                raise ValueError('Pinned tokenizer blob mismatch')
        tokenizer = AutoTokenizer.from_pretrained(token_dir, local_files_only=True)
        by_text = defaultdict(list)
        for p in parents:
            by_text[(p['dataset'], normalized(p['problem']))].append(p)
        draw = {p['id']: p for p in parents if p['partition'] == 'audit_draw'}
        raw, recomputed = [], []
        counts, seen = Counter(), defaultdict(set)
        for shard in config['solution_shards']:
            name = f'omi_{shard:05d}.parquet'
            ordinal = 0
            for batch in pq.ParquetFile(cache / name).iter_batches(batch_size=4096):
                for row in batch.to_pylist():
                    index = ordinal
                    ordinal += 1
                    if row['problem_source'] not in ('gsm8k', 'math'):
                        continue
                    matches = by_text.get((row['problem_source'], normalized(row['problem'])), [])
                    if any(p['original_split'] == 'test' for p in matches):
                        continue
                    targets = [p for p in matches if p['id'] in draw]
                    if not targets:
                        continue
                    if len(targets) != 1:
                        raise ValueError('Ambiguous original parent')
                    p = targets[0]
                    if counts[p['id']] >= config['candidates_per_problem']:
                        continue
                    counts[p['id']] += 1
                    d = check_candidate(p, row, seen[p['id']], tokenizer, config['max_sequence_length'])
                    d.update(shard=name, row_index=index, problem_id=p['id'], dataset=p['dataset'],
                             candidate_index=counts[p['id']],
                             source_row_sha256=sha_bytes(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()))
                    recomputed.append(d)
                    raw.append(dict(shard=name, row_index=index, problem_id=p['id'],
                                    candidate_index=counts[p['id']], row=row))
            print(json.dumps(dict(stage='candidate_reconstruction', shard=name, rows=ordinal,
                                  recovered_candidates=len(raw))), flush=True)
        if recomputed != decisions:
            raise ValueError('Candidate decisions changed; retain output and diagnose')
        raw_hash = sha_bytes(jsonl_bytes(raw))
        if raw_hash != read(SOLUTION_ROOT / 'summary.json')['private_raw_candidates_sha256']:
            raise ValueError('Raw candidate reconstruction byte hash mismatch')
        write_rows(out / 'raw_candidates.jsonl', raw)
        candidates = {(r['problem_id'], r['candidate_index']): r for r in raw}
        parent_by_id = {r['id']: r for r in parents}
        schedules, arms = [], []
        old_checks = {r['file']: r['sha256'] for r in read(SCHEDULE_ROOT / 'verification.json')['schedules']}
        audit_draw = sorted((p for p in parents if p['dataset'] == 'gsm8k' and p['partition'] == 'audit_draw'),
                            key=lambda p: p['rank'])
        for arm in ('repeat', 'solutions', 'mixed', 'breadth'):
            first_summary = read(SCHEDULE_ROOT / f'{arm}_seed17.json')['summary']
            acquired = audit_draw[:first_summary['acquired_p']]
            selected = read_rows(SCHEDULE_ROOT / f'{arm}_rows.jsonl')
            if selected != expected_selected_pairs(acquired, decisions, first_summary['target_k']):
                raise ValueError('Selected pairs differ from first-K accepted on the frozen parent prefix')
            data = []
            for d in selected:
                p = parent_by_id[d['problem_id']]
                r = candidates[(d['problem_id'], d['candidate_index'])]
                if d['reason'] != 'accepted' or any(d[k] != r[k] for k in ('shard', 'row_index')):
                    raise ValueError('Selection does not identify an accepted source')
                row = dict(problem_id=p['id'], group_id=p['group_id'], prompt=p['problem'],
                           answer=p['answer'], response=r['row']['generated_solution'],
                           path_id=str(d['candidate_index']), source=d)
                encoded = encode_row(row, tokenizer, 1024)
                if any(encoded[k] != d[k] for k in ('n_prompt', 'n_supervised', 'n_processed')):
                    raise ValueError('Allocation row exact token counts differ')
                data.append(row)
            write_rows(out / f'{arm}_train.jsonl', data)
            first_summary = read(SCHEDULE_ROOT / f'{arm}_seed17.json')['summary']
            acquired = audit_draw[:first_summary['acquired_p']]
            selected_ids = {r['problem_id'] for r in data}
            denominator = [dict(problem_id=p['id'], rank=p['rank'], group_id=p['group_id'],
                                retained_solutions=sum(r['problem_id'] == p['id'] for r in data)) for p in acquired]
            write_rows(out / f'{arm}_acquired_parents.jsonl', denominator)
            if len(acquired) != first_summary['acquired_p'] or len(selected_ids) != first_summary['trainable_p']:
                raise ValueError('Acquired or trainable denominator differs')
            arms.append(dict(arm=arm, acquired_p=len(acquired), trainable_p=len(selected_ids),
                             zero_solution_p=len(acquired) - len(selected_ids), unique_pairs=len(data),
                             target_k=first_summary['target_k'],
                             data_sha256=sha_file(out / f'{arm}_train.jsonl'),
                             acquired_denominator_sha256=sha_file(out / f'{arm}_acquired_parents.jsonl')))
            for seed in (17, 23):
                name = f'{arm}_seed{seed}.json'
                if sha_file(SCHEDULE_ROOT / name) != old_checks[name]:
                    raise ValueError('Frozen schedule checksum differs')
                saved = read(SCHEDULE_ROOT / name)
                checked = validate_schedule(selected, saved)
                with (out / name).open('xb') as stream:
                    stream.write((SCHEDULE_ROOT / name).read_bytes())
                schedules.append(dict(arm=arm, seed=seed, schedule_sha256=old_checks[name], **checked))
        exposure = exposure_inventory(public)
        aliases = question_alias_inventory(parents)
        seen = set(exposure['mentioned_ids']) | set(aliases['matching_development_ids'])
        dev_ids = {r['id'] for r in public if r['dataset'] == 'gsm8k' and r['partition'] == 'development'}
        exposure['question_alias_audit'] = aliases
        exposure['combined_conservative_exposure_count'] = len(seen)
        exposure['candidate_unmentioned_after_alias_audit'] = sorted(dev_ids - seen)
        exposure['combined_unmentioned_count'] = len(dev_ids - seen)
        write_json(out / 'development_exposure_inventory.json', exposure)
        audit = dict(schema='midpoint_c017_inventory_v1', status='verified_cpu_reconstruction',
                     created_at_utc=datetime.now(timezone.utc).isoformat(),
                     source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                     executed_script_sha256=sha_file(__file__),
                     scope='Historical bank reconstruction and allocation readiness; no model or new scientific result',
                     parent_records=len(parents), candidate_records=len(raw),
                     parent_manifest_sha256=public_hash, private_parents_sha256=freeze['private_problem_records_sha256'],
                     candidate_decisions_sha256=decision_hash, raw_candidates_sha256=raw_hash,
                     all_candidate_decisions_recomputed_equal=True,
                     source_bytes=sum((cache / n).stat().st_size for n in receipts),
                     source_files=[dict(name=n, sha256=r['sha256'], bytes=(cache/n).stat().st_size, url=r['url'])
                                   for n,r in sorted(receipts.items())],
                     tokenizer_repo=lock['repo_id'], tokenizer_revision=lock['tokenizer_revision'],
                     tokenizer_sha256=sha_file(token_dir/'tokenizer.json'),
                     arms=arms, schedules=schedules, exposure=exposure,
                     training_executed=False, teacher_calls=0, model_weights_loaded=False,
                     elapsed_seconds=time.monotonic()-started,
                     limitations=['Cached-bank original teacher failures and historical costs unknown.',
                                  'Whole-trace exact-token matching has length-dependent q/q+1 exposure residuals.',
                                  'Processed tokens and per-update token counts differ across conditions.',
                                  'No pretraining cleanliness or strategy-level diversity claim.',
                                  'No Modal or GPU recovery/runtime validation.'])
        write_json(out / 'PUBLIC_AUDIT.json', audit)
        write_json(out / 'PRIVATE_ARTIFACT_MANIFEST.json', dict(files=[dict(name=p.name, bytes=p.stat().st_size,
            sha256=sha_file(p)) for p in sorted(out.iterdir()) if p.is_file()]))
        print(json.dumps(dict(status=audit['status'], arms=len(arms), schedules=len(schedules),
                             development_mentioned=exposure['conservatively_mentioned_parents'],
                             development_unmentioned=exposure['combined_unmentioned_count'])), flush=True)
    except Exception as exc:
        write_json(out / 'FAILURE.json', dict(type=type(exc).__name__, message=str(exc),
                   elapsed_seconds=time.monotonic()-started, model_work=0))
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', required=True)
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--out', required=True)
    run(p.parse_args())


if __name__ == '__main__':
    main()
