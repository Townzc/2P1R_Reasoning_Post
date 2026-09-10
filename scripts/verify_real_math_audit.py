"""Reconcile C017 using independent source-index and token-count reconstruction.

This does not independently prove mathematical arguments. The sampled step
review and conservative answer matcher have explicitly separate limitations.
"""
import argparse
import base64
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
import unicodedata

import pyarrow.parquet as pq
from tokenizers import Tokenizer


def rows(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def digest_bytes(b):
    return hashlib.sha256(b).hexdigest()


def norm(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', value)).strip()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parents', required=True)
    p.add_argument('--frozen', required=True)
    p.add_argument('--solutions', required=True)
    p.add_argument('--raw', required=True)
    p.add_argument('--cache', required=True)
    p.add_argument('--tokenizer-json', required=True)
    p.add_argument('--previous')
    p.add_argument('--out', required=True)
    args = p.parse_args()
    started = time.monotonic()
    out = Path(args.out)
    if out.exists():
        raise FileExistsError(out)
    frozen, solution, cache = Path(args.frozen), Path(args.solutions), Path(args.cache)
    summary = json.loads((solution / 'summary.json').read_text())
    config = json.loads(Path('configs/diagnostics/real_math_c017.json').read_text())
    parent_rows = rows(args.parents)
    parents = {r['id']: r for r in parent_rows}
    public_bytes = gzip.decompress(base64.b64decode((frozen / 'problem_manifest.jsonl.gz.b64').read_bytes()))
    check(digest_bytes(public_bytes) == summary['problem_manifest_sha256'], 'Public manifest archive differs')
    public = [json.loads(line) for line in public_bytes.split(b'\n') if line]
    check(len(public) == len(parents) == 21292, 'Parent denominator/uniqueness')
    for r in public:
        a = parents[r['id']]
        check(r['problem_sha256'] == digest_bytes(a['problem'].encode()), 'Problem content hash')
        check(r['reference_sha256'] == digest_bytes(a['reference'].encode()), 'Reference content hash')
        check(r['normalized_problem_sha256'] == digest_bytes(norm(a['problem']).encode()), 'Normalized hash')
        check(all(a[k] == r[k] for k in ('partition', 'group_id', 'original_split', 'exclusions')), 'Partition divergence')
    by_group = defaultdict(set)
    for r in parent_rows:
        if r['partition'] != 'excluded':
            by_group[r['group_id']].add(r['partition'])
        if r['partition'] not in ('official_test', 'excluded'):
            check(r['original_split'] == 'train', 'Original-test parent entered candidate training split')
    check(all(len(partitions) == 1 for partitions in by_group.values()), 'Group split leakage')
    draw = {r['id']: r for r in parent_rows if r['partition'] == 'audit_draw'}
    check(Counter(r['dataset'] for r in draw.values()) == {'gsm8k': 1024, 'math': 512}, 'Acquired denominators')
    for part in ('development', 'audit_draw', 'fresh_draw_reserved'):
        check(len({r['stratum'] for r in parent_rows if r['dataset'] == 'math' and r['partition'] == part}) == 21,
              'A MATH stratum disappeared from a main partition')
    by_text = defaultdict(list)
    for r in parent_rows:
        by_text[(r['dataset'], norm(r['problem']))].append(r)
    expected_locations, availability, source_counts = [], Counter(), Counter()
    # Independently re-enumerate the pinned source rows, not saved candidate counts.
    receipts = json.loads((solution / 'solution_source_receipts.json').read_text())
    for shard in config['solution_shards']:
        name = f'omi_{shard:05d}.parquet'
        check(digest_bytes((cache/name).read_bytes()) == receipts[name]['sha256'], 'Shard hash mismatch')
        ordinal = 0
        for batch in pq.ParquetFile(cache/name).iter_batches(columns=['problem', 'problem_source'], batch_size=16384):
            for r in batch.to_pylist():
                index = ordinal
                ordinal += 1
                source_counts[r['problem_source']] += 1
                matches = by_text[(r['problem_source'], norm(r['problem']))]
                if any(a['original_split'] == 'test' for a in matches):
                    continue
                selected = [a for a in matches if a['id'] in draw]
                if not selected:
                    continue
                check(len(selected) == 1, 'Ambiguous selected parent')
                pid = selected[0]['id']
                availability[pid] += 1
                if availability[pid] <= config['candidates_per_problem']:
                    expected_locations.append((pid, name, index))
    raw = rows(args.raw)
    decisions = rows(solution / 'candidate_decisions.jsonl')
    check(len(raw) == len(decisions) == len(expected_locations), 'Candidate population mismatch')
    check([(r['problem_id'], r['shard'], r['row_index']) for r in decisions] == expected_locations,
          'Candidates are not the prescribed first-16 released rows')
    check(source_counts == summary['source_counts'], 'Source row counts differ')
    tokenizer = Tokenizer.from_file(args.tokenizer_json)
    eos = tokenizer.token_to_id('<|endoftext|>')
    accepted, token_rows = defaultdict(list), 0
    for r, d in zip(raw, decisions):
        check((r['problem_id'], r['shard'], r['row_index']) == (d['problem_id'], d['shard'], d['row_index']), 'Candidate order differs')
        text = r['row']['generated_solution']
        check(digest_bytes(text.encode()) == d['response_sha256'], 'Raw response hash')
        check(digest_bytes(json.dumps(r['row'], ensure_ascii=False, sort_keys=True).encode()) == d['source_row_sha256'], 'Raw source row hash')
        check(norm(r['row']['problem']) == norm(draw[d['problem_id']]['problem']), 'Candidate/parent identity')
        if 'n_processed' in d:
            prefix = 'Problem: ' + draw[d['problem_id']]['problem'] + '\nSolution:\n'
            encoded = tokenizer.encode(prefix+text, add_special_tokens=False)
            check(not any(a < len(prefix) < b for a, b in encoded.offsets), 'Cross-boundary token')
            prompt_count = sum(a < len(prefix) for a, b in encoded.offsets)
            response_count = sum(a >= len(prefix) and b > a for a, b in encoded.offsets) + 1
            check(encoded.ids[:prompt_count] == tokenizer.encode(prefix, add_special_tokens=False).ids, 'Inference/training prefix mismatch')
            check(eos not in encoded.ids and eos is not None, 'EOS contamination')
            check((d['n_prompt'], d['n_supervised'], d['n_processed']) == (prompt_count, response_count, len(encoded.ids)+1), 'Exact token accounting')
            token_rows += 1
        if d['reason'] == 'accepted':
            check(d['n_processed'] <= config['max_sequence_length'], 'Accepted over-length response')
            accepted[d['problem_id']].append(d)
    per_problem = rows(solution / 'per_problem.jsonl')
    check({r['problem_id'] for r in per_problem} == set(draw), 'Zero parents missing')
    for r in per_problem:
        check(r['available_in_scanned_shards'] == availability[r['problem_id']], 'Inventory mismatch')
        check(r['accepted_k'] == len(accepted[r['problem_id']]), 'Accepted count mismatch')
    for dataset, table in summary['tables'].items():
        check(Counter(d['reason'] for d in decisions if d['dataset'] == dataset) == table['first_reason_counts'], 'Attrition arithmetic')
        pp = sorted((r for r in draw.values() if r['dataset'] == dataset), key=lambda r: r['rank'])
        for g in table['grid']:
            ids = [r['id'] for r in pp[:g['acquired_p']]]
            aa = [a for pid in ids for a in accepted[pid][:g['target_k']]]
            check(len(aa) == g['unique_pairs'], 'Grid pair count')
            check(sum(a['n_supervised'] for a in aa) == g['one_pass_supervised_tokens'], 'Grid supervision count')
            check(sum(a['n_processed'] for a in aa) == g['one_pass_processed_tokens'], 'Grid processed count')
            check(sum(not accepted[pid] for pid in ids) == g['zero_solution_p'], 'Grid missing-parent denominator')
    changes = None
    if args.previous:
        previous = Path(args.previous)
        old = rows(previous / 'candidate_decisions.jsonl')
        old_summary = json.loads((previous / 'summary.json').read_text())
        check(len(old) == len(decisions), 'Replay changed candidate count')
        check(old_summary['private_raw_candidates_sha256'] == summary['private_raw_candidates_sha256'], 'Replay changed raw candidates')
        check(all(a['source_row_sha256'] == b['source_row_sha256'] for a, b in zip(old, decisions)), 'Replay changed candidate ordering')
        changes = dict(Counter(a['reason']+' -> '+b['reason'] for a, b in zip(old, decisions) if a['reason'] != b['reason']))
    receipt = {'verified': True, 'parents': len(parents), 'audit_parents': len(draw),
               'source_rows_reenumerated': sum(source_counts.values()), 'candidates': len(decisions),
               'rows_independently_tokenized': token_rows, 'cross_partition_group_leakage': 0,
               'original_test_training_rows': 0, 'math_strata_per_partition': 21,
               'same_candidate_replay_changes': changes, 'seconds': time.monotonic()-started,
               'semantic_scope': 'Identity/cap/denominator/hash/token/aggregate verification, not independent proof validation.',
               'summary_sha256': digest_bytes((solution/'summary.json').read_bytes())}
    with out.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
