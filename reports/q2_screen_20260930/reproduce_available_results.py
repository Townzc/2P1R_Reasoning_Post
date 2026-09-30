"""Verify saved sample identities and reproduce descriptive metrics; no execution of code samples."""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.q2_supervision_migration.contracts import identity_hash
from experiments.q2_supervision_migration.analyze_screen import score_maps, paired_question_interval
from experiments.q2_supervision_migration.analyze_available import empirical_bounds

report = Path(__file__).resolve().parent
expected = json.loads((report / 'RESULTS.json').read_text())
plan = json.loads((ROOT / 'experiments/q2_supervision_migration/assets/screen_t128_k128_v2.json').read_text())
assert identity_hash(plan) == expected['plan_sha256']
blob = (report / 'EVALUATION_SAMPLES.jsonl.gz').read_bytes()
assert hashlib.sha256(blob).hexdigest() == expected['raw_evaluation_export']['sha256']
states = defaultdict(list)
identities = set()
for line in gzip.decompress(blob).splitlines():
    wrapped = json.loads(line)
    row = wrapped['record']
    assert identity_hash({k: v for k, v in row.items() if k != 'record_sha256'}) == row['record_sha256']
    assert row['kind'] == 'sample' and row['sample_id'] not in identities
    identities.add(row['sample_id'])
    states[wrapped['state']].append(row)
assert set(states) == {'R', 'W_prefix', 'W_future'} and len(identities) == 3072
maps = {}
for state, rows in states.items():
    assert len(rows) == 1024
    maps[state] = score_maps(rows, plan['eval_ids'])
    values = {k: 100 * sum(v.values()) / len(v) for k, v in maps[state].items()}
    assert values == expected['states'][state]['scores']
    assert empirical_bounds(rows, plan['eval_ids']) == expected['states'][state]['bounds']
    counts = Counter(r['base']['status'] + '/' + r['extra']['status'] for r in rows)
    assert dict(counts) == expected['states'][state]['inspection']['base_extra_counts']
    print(state, values)
for left, right in [('W_prefix', 'R'), ('W_future', 'R'), ('W_future', 'W_prefix')]:
    for metric in maps[left]:
        actual = paired_question_interval(maps[left][metric], maps[right][metric])
        assert actual == expected['descriptive_contrasts'][left + '_minus_' + right][metric]
assert expected['primary_matched_future_contrasts'] == {'W/R': None, 'W/C': None, 'C/R': None}
print('Verified: 3072 signed samples; all scores, counts, bounds and conditional task intervals match.')
