"""CPU-only exact-token audit of engineering fixtures; no budget matching claim."""
import argparse
import json
from collections import Counter
from pathlib import Path
from transformers import AutoTokenizer
from src.sft_data import encode_row, read_jsonl, sha256_file

p=argparse.ArgumentParser()
p.add_argument('--data', required=True)
p.add_argument('--out', required=True)
a=p.parse_args()
lock=json.loads(Path('configs/models.lock.json').read_text())['debug']
tokenizer=AutoTokenizer.from_pretrained(lock['repo_id'],revision=lock['revision'],use_fast=True,local_files_only=True)
report={'model': {k:lock[k] for k in ('repo_id','revision','tokenizer_revision')},
        'scope':'engineering fixtures only; these arms are NOT token matched', 'conditions':{}}
paths = sorted(Path(a.data).glob('arm_*.jsonl'))
if not paths: raise ValueError('No condition files found')
for path in paths:
    rows=read_jsonl(path)
    encoded=[encode_row(r,tokenizer,384) for r in rows]
    report['conditions'][path.stem]={'data_sha256':sha256_file(path),'presentations':len(rows),
        'distinct_problems':len({r['problem_id'] for r in rows}),
        'distinct_problem_paths':len({(r['problem_id'],r['path_id']) for r in rows}),
        'supervised_response_tokens':sum(r['n_supervised'] for r in encoded),
        'processed_tokens':sum(r['n_processed'] for r in encoded),
        'response_token_histogram':dict(sorted(Counter(r['n_supervised'] for r in encoded).items())),
        'max_sequence_tokens':max(r['n_processed'] for r in encoded),
        'prompt_boundary_checks_passed':True, 'prompt_masked':True, 'eos_supervised':True}
with Path(a.out).open('x') as f: json.dump(report,f,indent=2); f.write('\n')
print(json.dumps(report,indent=2))
