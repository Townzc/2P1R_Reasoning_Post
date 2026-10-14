"""Create-only local preparation. Never imports a cloud runtime or calls a model."""
import argparse
from pathlib import Path
import hashlib
import json
import shutil
from transformers import AutoTokenizer
from experiments.sft_allocation_midpoint.common import read, dump, sha, manifest
from experiments.sft_exploratory_20261014.contract import wrong_candidates, dev_examples, prompt_ids, make_plan
from src.sft_data import read_jsonl


def main(root):
    root = Path(root)
    old = Path('.local/p008_20261013/main_r1')
    pool = old/'exports/pool_d1/evidence'
    cache = read(pool/'candidate_cache.json')
    parents = read_jsonl(old/'pool_inputs/eligible_parents.jsonl')
    lookup = {p['id']: p for p in parents}
    order = read(pool/'frozen_wallets.json')['parent_order']
    selected, eligible = wrong_candidates(cache, order)
    if not selected:
        raise ValueError('No eligible wrong outputs')
    dev = read_jsonl('.local/p008_20261013/phase0_inputs/reserved_dev.jsonl')
    testpath = old/'student_preparation_r1/inputs/gsm8k_test1319.jsonl'
    test = read_jsonl(testpath)
    if len(test) != 1319 or len({r['problem_id'] for r in test}) != 1319:
        raise ValueError('Frozen full endpoint missing')
    examples = dev_examples(dev, test, lookup)
    basepath = Path('.local/midpoint_20261011/data_pipeline/reconstruction_r1/tokenizer')
    base = AutoTokenizer.from_pretrained(basepath, local_files_only=True)
    instruct = AutoTokenizer.from_pretrained(root/'metadata', local_files_only=True)
    rows = []
    for r in selected:
        p = lookup[r['problem_id']]
        rows.append(dict(problem_id=p['id'], group_id=p['id'], path_id=r['candidate_id'],
            prompt=p['problem'], response=r['text'], answer=p['answer'], source=dict(
                candidate_id=r['candidate_id'], attempt=r['attempt'],
                response_sha256=hashlib.sha256(r['text'].encode()).hexdigest(),
                original_record_sha256=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest())))
    frozenplan = old/'student_preparation_r1/inputs/d1_b1_p0_breadth_t1_plan.json'
    plan = make_plan(rows, base, read(frozenplan)['lrs'])
    prompts = {}
    for name, tok in [('base_4shot',base), ('instruct_0shot',instruct), ('wrong_teacher_t1',base)]:
        data = [dict(problem_id=r['problem_id'],input_ids=prompt_ids(name,r,tok,examples)) for r in test]
        if any(len(x['input_ids']) + 512 > 2048 for x in data):
            raise ValueError('Frozen four-shot/chat context exceeds 2048; no truncation/alternative selection')
        prompts[name] = data
    # New selection proof reads only selected original raw rows, not an old pool
    # oracle or a new teacher invocation. The old full-pool oracle remains intact.
    wanted = {r['candidate_id']:r for r in selected}; rawproof = {}
    for file in sorted(pool.glob('physical_batch_*_raw.json')):
        for r in read(file)['outputs']:
            if r['candidate_id'] not in wanted:continue
            s = wanted[r['candidate_id']]
            if r['token_ids'] != s['stop']['token_ids'] or r['finish_reason'] != 'stop':
                raise ValueError('Selected original native EOS evidence differs')
            rawproof[r['candidate_id']] = dict(raw_file=file.name,raw_file_sha256=sha(file),token_ids_sha256=hashlib.sha256(json.dumps(r['token_ids']).encode()).hexdigest())
    if set(rawproof) != set(wanted):raise ValueError('Selected physical raw missing')
    out = root/'inputs'; out.mkdir(exist_ok=False)
    def jsonl(path, values):
        with path.open('x') as f:
            for r in values:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
    shutil.copyfile(testpath,out/'gsm8k_test1319.jsonl')
    jsonl(out/'wrong_teacher.jsonl',rows);dump(out/'wrong_teacher_t1_plan.json',plan)
    dump(out/'dev_examples.json',examples)
    for name,data in prompts.items():dump(out/(name+'_prompts.json'),data)
    model=read(root/'metadata/instruct_api.json')
    modeldir=out/'instruct_model';modeldir.mkdir()
    for name in ('config.json','generation_config.json','tokenizer_config.json','tokenizer.json','merges.txt','vocab.json'):
        shutil.copyfile(root/'metadata'/name,modeldir/name)
    weight=next(x for x in model['siblings'] if x['rfilename']=='model.safetensors')['lfs']
    dump(out/'instruct_model_lock.json',dict(repo_id=model['id'],revision=model['sha'],weight=weight,
        metadata_files=manifest(modeldir)))
    dump(out/'manifest.json',dict(files=manifest(out)))
    dump(root/'SELECTION.json',dict(selected_count=len(rows),eligible_before_limit=eligible,
        selected_records=selected,original_raw_proof=rawproof,duplicate_definition='NFC_whitespace_exact_within_parent',
        parent_order_sha256=sha(pool/'frozen_wallets.json'),candidate_cache_sha256=sha(pool/'candidate_cache.json'),
        old_pool_oracle_sha256=sha(pool/'LOCAL_ORACLE_AUDIT.json'),
        dev_file_sha256=sha('.local/p008_20261013/phase0_inputs/reserved_dev.jsonl'),
        dev_example_ids=[e['id'] for e in examples],test_sha256=sha(testpath),
        control_plan_sha256=sha(frozenplan),selected_parents=len({r['problem_id'] for r in rows}),
        input_manifest_sha256=sha(out/'manifest.json'),
        prompt_length_ranges={k:[min(len(r['input_ids']) for r in v),max(len(r['input_ids']) for r in v)] for k,v in prompts.items()},
        schedule_targets=plan['supervised_targets'],exposed_answers=plan['exposed_answers'],
        max_training_tokens=max(r['source']['n_processed'] for r in rows),
        models_called=0,new_teacher_outputs=0,old_primary_scores_modified=False))
    print(json.dumps(dict(selected=len(rows),eligible=eligible,parents=len({r['problem_id'] for r in rows}),
        prompt_lengths=read(root/'SELECTION.json')['prompt_length_ranges'],input_sha256=sha(out/'manifest.json'))))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True)
    main(parser.parse_args().root)
