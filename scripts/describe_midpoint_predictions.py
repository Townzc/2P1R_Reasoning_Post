"""Post-hoc descriptions of already audited predictions; no model/network calls.

Does not replace the primary all-question endpoint or change any score. In
particular, the jointly parsed/EOS subset is a descriptive decomposition, not
an alternative selected benchmark or a causal test of reasoning quality.
"""
import argparse
import json
from pathlib import Path
import statistics

from experiments.sft_allocation_midpoint.common import sha


def describe(mapping):
    runs, table, provenance = {}, {}, {}
    roster = None
    for name, directory in mapping.items():
        root = Path(directory)
        audit = json.loads((root / 'LOCAL_ORACLE_AUDIT.json').read_text())
        files = json.loads((root / 'artifact_manifest.json').read_text())
        result = json.loads((root / 'result.json').read_text())
        rows = {}
        for file in sorted((root / 'endpoint431').glob('batch_*_scored.jsonl')):
            record = files[str(file.relative_to(root))]
            assert file.stat().st_size == record['bytes'] and sha(file) == record['sha256']
            for line in file.read_text().splitlines():
                row = json.loads(line)
                assert row['problem_id'] not in rows
                assert type(row['task_score']['task_answer_correct']) is bool
                rows[row['problem_id']] = row
        assert len(rows) == 431
        if roster is None:
            roster = set(rows)
        assert set(rows) == roster
        correct = {k: r['task_score']['task_answer_correct'] for k, r in rows.items()}
        assert correct == result['endpoint']['question_correct']
        assert sum(correct.values()) == result['endpoint']['correct']
        lengths = [r['generated_tokens'] for r in rows.values()]
        table[name] = dict(
            n=431, correct=sum(correct.values()),
            parsed=sum(r['task_score']['marked']['status'] == 'parsed' for r in rows.values()),
            native_eos=sum(r['stop']['stop_reason'] == 'native_eos' for r in rows.values()),
            length_cap=sum(r['stop']['stop_reason'] == 'length_cap' for r in rows.values()),
            mean_generated_tokens=statistics.mean(lengths), median_generated_tokens=statistics.median(lengths),
            train_seconds=result.get('train_seconds'), wall_seconds=result['wall_seconds'])
        provenance[name] = dict(artifact_manifest_sha256=sha(root / 'artifact_manifest.json'),
                                independent_audit_sha256=sha(root / 'LOCAL_ORACLE_AUDIT.json'),
                                result_sha256=sha(root / 'result.json'))
        runs[name] = rows
    decompositions = {}
    for high, low in [('solutions', 'repeat'), ('breadth', 'solutions')]:
        for seed in (17, 23):
            hn, ln = f'{high}_{seed}', f'{low}_{seed}'
            if hn not in runs or ln not in runs:
                continue
            a, b = runs[hn], runs[ln]
            clean = {q for q in roster if all(
                r['task_score']['marked']['status'] == 'parsed' and r['stop']['stop_reason'] == 'native_eos'
                for r in (a[q], b[q]))}
            strata = {}
            for label, ids in [('both_parsed_native_eos', clean), ('other', roster - clean)]:
                gained = sum(a[q]['task_score']['task_answer_correct'] and not b[q]['task_score']['task_answer_correct'] for q in ids)
                lost = sum(b[q]['task_score']['task_answer_correct'] and not a[q]['task_score']['task_answer_correct'] for q in ids)
                strata[label] = dict(n=len(ids), gained=gained, lost=lost, net_correct=gained-lost,
                                     contribution_to_full_endpoint_pp=100*(gained-lost)/431)
            assert sum(v['net_correct'] for v in strata.values()) == table[hn]['correct'] - table[ln]['correct']
            decompositions[hn + '_minus_' + ln] = strata
    return dict(schema='midpoint_posthoc_prediction_description_v1', source=provenance,
                table=table, paired_decomposition=decompositions,
                interpretation='Post-hoc diagnostic only. Every contribution uses the original denominator 431. '
                'No endpoint exclusion, rescoring, checkpoint selection, new generation, or causal identification.',
                new_model_calls=0)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--mapping', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    report = describe(json.loads(Path(args.mapping).read_text()))
    with Path(args.out).open('x') as file:
        json.dump(report, file, indent=2, sort_keys=True)
        file.write('\n')
