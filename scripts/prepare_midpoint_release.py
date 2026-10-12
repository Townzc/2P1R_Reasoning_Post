"""Freeze the already-audited inventory and development rosters, without model calls."""
import argparse
import json
import shutil
from pathlib import Path
from experiments.sft_allocation_midpoint.common import dump, sha, manifest, verify
from src.sft_data import read_jsonl


def prepare(inventory, out):
    inventory, out = Path(inventory), Path(out)
    files = {r['name']: {k: r[k] for k in ('sha256', 'bytes')}
             for r in json.loads((inventory/'PRIVATE_ARTIFACT_MANIFEST.json').read_text())['files']}
    verify(inventory, files)
    exposures = json.loads((inventory/'development_exposure_inventory.json').read_text())
    records = read_jsonl(inventory/'problem_records.jsonl')
    by_id = {r['id']: r for r in records}
    observed = sorted(exposures['mentioned_ids'])
    endpoint = sorted(exposures['candidate_unmentioned_after_alias_audit'])
    if len(observed) != 80 or len(endpoint) != 431 or set(observed) & set(endpoint):
        raise ValueError('Frozen exposure roster differs')
    train = {r['problem_id'] for arm in ('repeat','solutions','mixed','breadth')
             for r in read_jsonl(inventory/f'{arm}_train.jsonl')}
    if train & (set(observed) | set(endpoint)):
        raise ValueError('Train/evaluation problem overlap')
    train_groups = {by_id[i]['group_id'] for i in train}
    if train_groups & {by_id[i]['group_id'] for i in observed+endpoint}:
        raise ValueError('Train/evaluation group overlap')
    out.mkdir(parents=True, exist_ok=False)
    for arm in ('repeat','solutions','mixed','breadth'):
        for name in (f'{arm}_train.jsonl', f'{arm}_seed17.json', f'{arm}_seed23.json'):
            shutil.copyfile(inventory/name, out/name)
    for name, ids in (('observed80', observed), ('endpoint431', endpoint)):
        with (out/f'{name}.jsonl').open('x') as f:
            for i in ids:
                r = by_id[i]
                if r['partition'] != 'development' or r['original_split'] != 'train' or r['exclusions']:
                    raise ValueError('Ineligible development parent')
                json.dump(dict(problem_id=i, group_id=r['group_id'], prompt=r['problem'],
                               answer=r['answer'], response=r['reference']), f, sort_keys=True)
                f.write('\n')
    frozen = dict(schema='midpoint_inputs_v1', files=manifest(out),
        source_inventory_sha256=sha(inventory/'PRIVATE_ARTIFACT_MANIFEST.json'),
        roster=dict(observed80=observed, endpoint431=endpoint, excluded_alias='gsm8k/train/05016'),
        test_usage=0, fresh_confirmation=False, actual_generation_calls=0)
    dump(out/'manifest.json', frozen)
    return frozen


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--inventory',required=True);p.add_argument('--out',required=True)
    a=p.parse_args(); result=prepare(a.inventory,a.out)
    print(json.dumps({'files':len(result['files']), 'roster_counts':{'observed':80,'endpoint':431}}))

