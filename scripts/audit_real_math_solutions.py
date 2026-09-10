"""Audit a frozen, bounded solution-bank slice without backfilling parent draws."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import time

import pyarrow.parquet as pq

from scripts.fetch_real_math_sources import digest, specifications
from scripts.prepare_real_math_audit import write_json, write_jsonl
from src.real_math_audit import (check_candidate, grid_statistics, jaccard,
                                normalized, quantiles, sha, shingles)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default='configs/diagnostics/real_math_c017.json')
    p.add_argument('--cache', required=True)
    p.add_argument('--parents', required=True)
    p.add_argument('--frozen', required=True)
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--private-out', required=True)
    args = p.parse_args()
    started = time.monotonic()
    cache, out, private = Path(args.cache), Path(args.out), Path(args.private_out)
    out.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    c = json.loads(Path(args.config).read_text())
    frozen = json.loads((Path(args.frozen) / 'freeze.json').read_text())
    try:
        if digest(Path(args.config)) != frozen['config_sha256'] or digest(Path(args.parents)) != frozen['private_problem_records_sha256']:
            raise ValueError('Problem/config freeze changed')
        if digest(Path(args.frozen) / 'problem_manifest.jsonl') != frozen['problem_manifest_sha256']:
            raise ValueError('Public problem manifest changed')
        from transformers import AutoTokenizer
        tokenizer_dir = Path(args.tokenizer_dir)
        lock = json.loads(Path('configs/models.lock.json').read_text())[c['model_role']]
        tokenizer_sha = digest(tokenizer_dir / 'tokenizer.json')
        # Verify against the retained original main-model verification receipt,
        # then independently check Git blob identity in the pinned lock.
        blob = (tokenizer_dir / 'tokenizer.json').read_bytes()
        import hashlib
        git_blob = hashlib.sha1(f'blob {len(blob)}\0'.encode()+blob).hexdigest()
        expected_blob = next(x['blobId'] for x in lock['files'] if x['rfilename'] == 'tokenizer.json')
        if git_blob != expected_blob:
            raise ValueError('Tokenizer does not match pinned base')
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir, local_files_only=True)
        parents = [json.loads(line) for line in Path(args.parents).read_text().splitlines()]
        lookup = defaultdict(list)
        for parent in parents:
            lookup[(parent['dataset'], normalized(parent['problem']))].append(parent)
        draw = {r['id']: r for r in parents if r['partition'] == 'audit_draw'}
        inventory, checked, seen = Counter(), Counter(), defaultdict(set)
        accepted, decisions, raw = defaultdict(list), [], []
        source_counts, linkage, receipts, shard_progress = Counter(), Counter(), {}, []
        for name, url, expected in specifications(c, True):
            receipt = json.loads((cache / f'{name}.receipt.json').read_text())
            if receipt['url'] != url or digest(cache / name) != expected or receipt['sha256'] != expected:
                raise ValueError('Solution source checksum mismatch')
            receipts[name] = receipt
            ordinal = 0
            for batch in pq.ParquetFile(cache / name).iter_batches(batch_size=4096):
                for row in batch.to_pylist():
                    location = {'shard': name, 'row_index': ordinal}
                    ordinal += 1
                    source_counts[row['problem_source']] += 1
                    dataset = row['problem_source']
                    if dataset not in ('gsm8k', 'math'):
                        linkage['augmented_or_other_excluded'] += 1
                        continue
                    matches = lookup.get((dataset, normalized(row['problem'])), [])
                    if not matches:
                        linkage[dataset + ':unmatched_problem'] += 1
                        continue
                    if any(r['original_split'] == 'test' for r in matches):
                        linkage[dataset + ':official_test_match_excluded'] += 1
                        continue
                    targets = [r for r in matches if r['id'] in draw]
                    if not targets:
                        partitions = sorted({r['partition'] for r in matches})
                        linkage[dataset + ':' + '+'.join(partitions)] += 1
                        continue
                    if len(targets) != 1:
                        raise ValueError('Multiple selected parents for the same source problem')
                    parent = targets[0]
                    pid = parent['id']
                    inventory[pid] += 1
                    linkage[dataset + ':audit_draw'] += 1
                    if checked[pid] >= c['candidates_per_problem']:
                        continue
                    checked[pid] += 1
                    result = check_candidate(parent, row, seen[pid], tokenizer, c['max_sequence_length'])
                    result.update(location, problem_id=pid, dataset=dataset, candidate_index=checked[pid],
                                  source_row_sha256=sha(json.dumps(row, ensure_ascii=False, sort_keys=True)))
                    decisions.append(result)
                    raw.append(location | {'problem_id': pid, 'candidate_index': checked[pid], 'row': row})
                    if result['reason'] == 'accepted':
                        accepted[pid].append(result)
            snapshot = {'shard': name, 'rows': ordinal, 'cumulative_source_counts': dict(source_counts),
                        'cumulative_checked_candidates': len(decisions),
                        'draw_parents_observed': sum(inventory[p] > 0 for p in draw)}
            shard_progress.append(snapshot)
            print(json.dumps(snapshot), flush=True)
        write_jsonl(out / 'candidate_decisions.jsonl', decisions)
        write_jsonl(private / 'raw_candidates.jsonl', raw)
        write_json(out / 'solution_source_receipts.json', receipts)
        write_json(out / 'shard_progress.json', shard_progress)
        raw_by_key = {(r['problem_id'], r['candidate_index']): r for r in raw}
        per_problem = []
        for pid, parent in sorted(draw.items()):
            accepted_shingles, near_retained = [], []
            for a in accepted[pid]:
                text = raw_by_key[(pid, a['candidate_index'])]['row']['generated_solution']
                ss = shingles(text)
                if not any(jaccard(ss, other) >= c['near_solution_jaccard_threshold'] for other in accepted_shingles):
                    near_retained.append(a)
                    accepted_shingles.append(ss)
            per_problem.append({'problem_id': pid, 'dataset': parent['dataset'], 'stratum': parent['stratum'],
                                'rank': parent['rank'], 'available_in_scanned_shards': inventory[pid],
                                'checked_candidates': checked[pid], 'accepted_k': len(accepted[pid]),
                                'near_text_sensitivity_k': len(near_retained),
                                'candidate_cap_reached': checked[pid] == c['candidates_per_problem']})
        write_jsonl(out / 'per_problem.jsonl', per_problem)
        tables = {}
        for dataset in ('gsm8k', 'math'):
            pp = [r for r in draw.values() if r['dataset'] == dataset]
            dd = [d for d in decisions if d['dataset'] == dataset]
            aa = [a for r in pp for a in accepted[r['id']]]
            per = [r for r in per_problem if r['dataset'] == dataset]
            by_stratum = {}
            for st in sorted({r['stratum'] for r in pp}):
                group = [r for r in per if r['stratum'] == st]
                by_stratum[st] = {'acquired_p': len(group), 'zero_solution_p': sum(r['accepted_k'] == 0 for r in group),
                                  'k4_p': sum(r['accepted_k'] >= 4 for r in group),
                                  'accepted_solutions': sum(r['accepted_k'] for r in group)}
            tables[dataset] = {
                'acquired_p': len(pp), 'available_in_scanned_shards': sum(inventory[r['id']] for r in pp),
                'checked_candidates': len(dd), 'candidate_cap_reached_p': sum(r['candidate_cap_reached'] for r in per),
                'first_reason_counts': dict(Counter(d['reason'] for d in dd)),
                'coverage_p': {str(k): sum(r['accepted_k'] >= k for r in per) for k in (1, 2, 4, 8, 16)},
                'zero_solution_p': sum(r['accepted_k'] == 0 for r in per),
                'accepted_k_histogram': dict(Counter(r['accepted_k'] for r in per)),
                'near_text_sensitivity_coverage_p': {str(k): sum(r['near_text_sensitivity_k'] >= k for r in per) for k in (1, 2, 4)},
                'response_tokens_including_eos': quantiles([a['n_supervised'] for a in aa]),
                'processed_tokens': quantiles([a['n_processed'] for a in aa]),
                'length_sensitivity': {str(length): {
                    'solutions': sum(d.get('n_processed', 10**9) <= length for d in dd),
                    'k4_p': sum(sum(d.get('n_processed', 10**9) <= length for d in dd if d['problem_id'] == r['id']) >= 4 for r in pp)}
                    for length in c['length_sensitivity']},
                'strata': by_stratum,
                'grid': grid_statistics(pp, accepted, c[f'{dataset}_nested_p'], c['target_k'])}
        # Prespecified sampled qualitative audit; these are AI-reviewed, not human gold.
        qa = []
        for dataset in ('gsm8k', 'math'):
            candidates = [a for pid in draw for a in accepted[pid] if draw[pid]['dataset'] == dataset]
            candidates.sort(key=lambda a: sha(f"{c['seed']}:qa:{a['problem_id']}:{a['response_sha256']}"))
            used = set()
            for a in candidates:
                if a['problem_id'] in used:
                    continue
                used.add(a['problem_id'])
                parent = draw[a['problem_id']]
                row = raw_by_key[(a['problem_id'], a['candidate_index'])]['row']
                qa.append({'problem_id': a['problem_id'], 'stratum': parent['stratum'],
                           'response_sha256': a['response_sha256'], 'question': parent['problem'],
                           'reference_answer': parent['answer'], 'response': row['generated_solution']})
                if len(used) == c['manual_review_per_dataset']:
                    break
        write_jsonl(private / 'qualitative_review_sample.jsonl', qa)
        write_json(out / 'qualitative_review_manifest.json', [{k: r[k] for k in ('problem_id', 'stratum', 'response_sha256')} for r in qa])
        environment = {'python': platform.python_version(), 'platform': platform.system(), 'machine': platform.machine(),
                       'packages': {k: importlib.metadata.version(k) for k in ('pyarrow', 'transformers', 'tokenizers')},
                       'tokenizer_repo': lock['repo_id'], 'tokenizer_revision': lock['tokenizer_revision'],
                       'tokenizer_sha256': tokenizer_sha, 'tokenizer_git_blob': git_blob,
                       'model_weights_loaded': False, 'devices_used': ['CPU']}
        summary = {'audit': 'C017', 'scope': c['scope'], 'source_counts': dict(source_counts),
                   'source_linkage': dict(linkage), 'tables': tables,
                   'source_shards': c['solution_shards'], 'shards_in_complete_bank': 32,
                   'historical_teacher_attempts': None, 'historical_teacher_cost': None,
                   'teacher_calls': 0, 'gpu_seconds': 0, 'evaluations': 0,
                   'audit_seconds': time.monotonic()-started,
                   'created_at_utc': datetime.now(timezone.utc).isoformat(),
                   'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                   'config_sha256': digest(Path(args.config)),
                   'problem_manifest_sha256': frozen['problem_manifest_sha256'],
                   'private_raw_candidates_sha256': digest(private / 'raw_candidates.jsonl'),
                   'interpretation': 'Released-slice, cap-16, conservative answer agreement and normalized text uniqueness; not total-bank coverage, generation yield, full-proof correctness, or distinct strategies.'}
        write_json(out / 'environment.json', environment)
        write_json(out / 'summary.json', summary)
        print(json.dumps({'completed': True, 'seconds': summary['audit_seconds'],
                          'coverage': {k: v['coverage_p'] for k, v in tables.items()}}), flush=True)
    except Exception as exc:
        write_json(out / 'failure.json', {'type': type(exc).__name__, 'message': str(exc), 'seconds': time.monotonic()-started})
        raise


if __name__ == '__main__':
    main()
