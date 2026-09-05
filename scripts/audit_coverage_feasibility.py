"""CPU necessary conditions for matching fixed-set, single-path repeated exposure.

This is an impossibility bound, not a coverage-matching sampler.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from src.sft_data import read_jsonl, sha256_file

p=argparse.ArgumentParser()
p.add_argument('--data', required=True)
p.add_argument('--out', required=True)
a=p.parse_args()
root=Path(a.data)
paths=read_jsonl(root/'arm_paths.jsonl')
repeat=read_jsonl(root/'arm_repeat.jsonl')
counts=Counter(r['structure_id'] for r in paths)
exposure=Counter(r['problem_id'] for r in repeat)
if len(set(exposure.values())) != 1: raise ValueError('Uniform exposure required for this bound')
r=next(iter(exposure.values()))
# Every GCM structure count is a multiple of R. Summing coordinatewise
# distances to multiples of R is a lower bound, even without eligibility limits.
l1_bound=sum(min(n%r,r-n%r) for n in counts.values())
report={'scope':'existing engineering fixture only; no scientific training',
 'paths_data_sha256':sha256_file(root/'arm_paths.jsonl'),
 'repeat_data_sha256':sha256_file(root/'arm_repeat.jsonl'),
 'problems':len(exposure),'presentations':len(paths),'fixed_exposures_per_problem':r,
 'within_paths_distinct_structures':len(counts),
 'single_path_max_distinct_structures':len(exposure),
 'target_structure_histogram':dict(sorted(counts.items())),
 'necessary_l1_count_error_lower_bound':l1_bound,
 'necessary_total_variation_lower_bound':l1_bound/(2*len(paths)),
 'exact_global_coverage_feasible':l1_bound==0 and len(counts)<=len(exposure),
 'interpretation':'False proves impossibility for these counts. True would only mean these necessary conditions pass; joint eligibility still needs a solver.',
 'decision':'Redesign candidate pool jointly before any matched-coverage claim. Do not rename a best-effort sampler as an exact control.'}
with Path(a.out).open('x') as f: json.dump(report,f,indent=2); f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='target_structure_histogram'},indent=2))
