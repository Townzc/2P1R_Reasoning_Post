"""A3/A4 descriptive diagnostics on immutable raw outputs and existing labels.

No generation or re-scoring. Freeze the repetition heuristic before inspecting
the allocation contrasts: a contiguous token block repeated at least 3 times,
with at least 60 repeated tokens, period 1..256. Count responses, not episodes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .evaluation import sha256_file


def looping(tokens: list[int]) -> bool:
    # For each period, a run of equal offset pairs implies a repeated block.
    for period in range(1, min(256, len(tokens) // 3) + 1):
        needed = max(60, 3 * period) - period
        run = 0
        for i in range(period, len(tokens)):
            run = run + 1 if tokens[i] == tokens[i-period] else 0
            if run >= needed:
                return True
    return False


def summarize(inputs: Path, generation: Path, scores: Path) -> dict:
    sm = json.loads((scores / 'MANIFEST.json').read_text())
    for key, path in [('input_sha256', inputs), ('raw_sha256', generation/'raw.jsonl'),
                      ('labels_sha256', scores/'labels.jsonl'),
                      ('generation_manifest_sha256', generation/'MANIFEST.json')]:
        if sm[key] != sha256_file(path):
            raise ValueError('Changed evidence: ' + key)
    rows = [json.loads(x) for x in inputs.open()]
    labels = {(r['id'], r['draw']): r for r in map(json.loads, (scores/'labels.jsonl').open())}
    details = []
    seen = set()
    for raw in map(json.loads, (generation/'raw.jsonl').open()):
        key = (raw['id'], raw['draw'])
        if key in seen or key not in labels:
            raise ValueError('Duplicate or missing label')
        seen.add(key)
        normal = raw['finish_reason'] == 'stop' and not raw['length_capped'] and (
            raw['stopped_on_terminator'] or raw['string_stop'])
        details.append({'id':raw['id'], 'draw':raw['draw'], 'correct':labels[key]['correct'],
                        'normal_termination':normal, 'length_capped':raw['length_capped'],
                        'looping':looping(raw['token_ids'])})
    if seen != set(labels):
        raise ValueError('Incomplete raw/label join')
    def stats(rs):
        n = len(rs); normal = [r for r in rs if r['normal_termination']]
        return {'responses':n, 'correct':sum(r['correct'] for r in rs),
                'accuracy':sum(r['correct'] for r in rs)/n,
                'length_cap_count':sum(r['length_capped'] for r in rs),
                'length_cap_rate':sum(r['length_capped'] for r in rs)/n,
                'loop_count':sum(r['looping'] for r in rs),
                'capped_loop_count':sum(r['looping'] and r['length_capped'] for r in rs),
                'normally_terminated_count':len(normal),
                'normally_terminated_correct':sum(r['correct'] for r in normal),
                'normally_terminated_accuracy':sum(r['correct'] for r in normal)/len(normal) if normal else None}
    subset = {r['id'] for r in rows if r.get('math500_id') is not None}
    return {'all':stats(details), 'math500':stats([r for r in details if r['id'] in subset]) if subset else None,
            'loop_definition':'Exact token period1..256 repeated>=3 times and>=60 tokens; response count',
            'normal_definition':'Actual terminator or configured string stop, not length capped; independent of correctness/loop flag',
            'interpretation':'Terminated-only accuracy is descriptive; denominators differ across cells',
            'raw_sha256':sm['raw_sha256'], 'labels_sha256':sm['labels_sha256'],
            'source_sha256':sha256_file(Path(__file__)), 'per_response':details}


def main():
    p = argparse.ArgumentParser()
    for arg in ('inputs','generation','scores','output'):p.add_argument('--'+arg,required=True,type=Path)
    a=p.parse_args(); result=summarize(a.inputs,a.generation,a.scores)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='per_response'}))


if __name__ == '__main__':main()
