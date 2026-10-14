"""Local CPU-only preparation; never downloads weights, scores outputs or calls a model."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import unicodedata

from experiments.sft_allocation_midpoint.common import dump, manifest, read, sha
from experiments.sft_allocation_acquisition.contract import messages
from src.sft_data import prefix, read_jsonl


def question_key(text):
    return hashlib.sha256(' '.join(unicodedata.normalize('NFC', text).split()).encode()).hexdigest()


def order_key(domain, identity):
    return hashlib.sha256((domain + ':' + identity).encode()).hexdigest()


def teacher_seed(identity):
    # New domain; the old P008 helper intentionally rejects unregistered domains.
    return int(order_key('p009-math-teacher-seed17', identity)[:16], 16) % (2**31)


def jsonl(path, rows):
    with Path(path).open('x', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')


def main():
    p = argparse.ArgumentParser()
    for name in ('assets', 'qwen-tokenizer', 'teacher-tokenizer', 'olmo-tokenizer',
                 'gsm-test', 'gsm-dev-examples', 'output'):
        p.add_argument('--' + name, required=True)
    args = p.parse_args()
    import pyarrow.parquet as pq
    from transformers import AutoTokenizer
    assets, out = Path(args.assets), Path(args.output)
    if out.exists():
        raise FileExistsError('Create-only release; reconcile partial files instead of rerunning')
    qwen = AutoTokenizer.from_pretrained(args.qwen_tokenizer, local_files_only=True)
    teacher = AutoTokenizer.from_pretrained(args.teacher_tokenizer, local_files_only=True)
    olmo = AutoTokenizer.from_pretrained(args.olmo_tokenizer, local_files_only=True)
    train, original_test = [], []
    for file in sorted((assets / 'math_train').glob('*/*.parquet')):
        split = file.name.split('-')[0]
        for i, row in enumerate(pq.read_table(file).to_pylist()):
            row = dict(row, problem_id=f'math/{file.parent.name}/{split}/{i}',
                       question_sha256=question_key(row['problem']))
            (train if split == 'train' else original_test).append(row)
    math500 = read_jsonl(assets / 'math500/test.jsonl')
    math500 = [dict(r, problem_id='math500/' + str(i), question_sha256=question_key(r['problem']))
               for i, r in enumerate(math500)]
    if (len(train), len(original_test), len(math500)) != (7500, 5000, 500):
        raise ValueError('Pinned complete MATH sources required')
    train_keys = {r['question_sha256'] for r in train}
    test_keys = {r['question_sha256'] for r in math500}
    if train_keys & test_keys or len(test_keys) != 500:
        raise ValueError('MATH endpoint overlap or duplicate')
    if not test_keys <= {r['question_sha256'] for r in original_test}:
        raise ValueError('MATH-500 provenance differs')
    gsm = read_jsonl(args.gsm_test)
    examples = read(args.gsm_dev_examples)
    if len(gsm) != 1319 or len({r['problem_id'] for r in gsm}) != 1319 or len(examples) != 4:
        raise ValueError('Complete original GSM test and fixed dev examples required')
    if {question_key(r['problem']) for r in examples} & {question_key(r['prompt']) for r in gsm}:
        raise ValueError('GSM dev/test overlap')

    # Length-only pre-result selection; complete original solutions, never test answers.
    math_prompt_max = max(len(qwen(prefix(r['problem']), add_special_tokens=False)['input_ids']) for r in math500)
    per_example_limit = (2048 - 1024 - math_prompt_max) // 4
    ordered_dev = sorted(original_test, key=lambda r: order_key('p009-math-dev-17', r['problem_id'].removeprefix('math/')))
    math_examples, seen = [], set()
    for r in ordered_dev:
        key = r['question_sha256']
        if key in train_keys | test_keys | seen:
            continue
        text = prefix(r['problem']) + r['solution'] + '\n\n'
        if len(qwen(text, add_special_tokens=False)['input_ids']) <= per_example_limit:
            math_examples.append(r)
            seen.add(key)
        if len(math_examples) == 4:
            break
    if len(math_examples) != 4:
        raise ValueError('Four complete disjoint dev examples do not fit; no silent truncation')
    math_demo = ''.join(prefix(r['problem']) + r['solution'] + '\n\n' for r in math_examples)
    gsm_demo = ''.join(prefix(r['problem']) + r['reference'] + '\n\n' for r in examples)
    unsupported, supported = [], []
    for r in train:
        tokens = teacher.apply_chat_template(messages(r), tokenize=True, add_generation_prompt=True)
        if len(tokens) + 1024 > 2048:
            unsupported.append(dict(problem_id=r['problem_id'], prompt_tokens=len(tokens),
                                    reason='owner_approved_context_unsupported_no_generation'))
        else:
            supported.append(dict(r, prompt_token_ids=tokens))
    if len(unsupported) != 7 or len(supported) != 7493:
        raise ValueError('Exact owner-approved unsupported roster differs')
    extra_ids = {r['problem_id'] for r in sorted(supported, key=lambda r: order_key('p009-extra-500-seed17', r['problem_id']))[:500]}
    requests = []
    # Fixed order: all first attempts, then the same selected500 for attempts2..4.
    for attempt in range(1, 5):
        for r in supported:
            if attempt > 1 and r['problem_id'] not in extra_ids:
                continue
            cid = f"{r['problem_id']}::attempt{attempt:02d}"
            requests.append(dict(candidate_id=cid, problem_id=r['problem_id'], attempt=attempt,
                seed=teacher_seed(cid), prompt_token_ids=r['prompt_token_ids']))
    if len(requests) != 8993 or len({r['candidate_id'] for r in requests}) != 8993:
        raise AssertionError('Finite teacher request count differs')
    evaluations = {}
    for name, tok, rows, field, demo, chat, cap in [
        ('qwen_gsm_zero_parity', qwen, gsm, 'prompt', '', False, 512),
        ('qwen_math_zero', qwen, math500, 'problem', '', False, 1024),
        ('qwen_math_four', qwen, math500, 'problem', math_demo, False, 1024),
        ('teacher_math_zero', teacher, math500, 'problem', '', True, 1024),
        ('olmo_gsm_zero', olmo, gsm, 'prompt', '', False, 512),
        ('olmo_gsm_four', olmo, gsm, 'prompt', gsm_demo, False, 512),
        ('teacher_gsm_zero', teacher, gsm, 'prompt', '', True, 512),
    ]:
        prompts = []
        for row in rows:
            ids = (tok.apply_chat_template(messages({'problem': row[field]}), tokenize=True, add_generation_prompt=True)
                   if chat else tok(demo + prefix(row[field]), add_special_tokens=False)['input_ids'])
            if len(ids) + cap > 2048:
                raise ValueError(f'Untruncated full endpoint does not fit: {name}/{row["problem_id"]}')
            prompts.append(dict(problem_id=row['problem_id'], input_ids=ids))
        evaluations[name] = dict(prompts=prompts, max_new_tokens=cap, max_context=2048,
                                 eos_token_id=tok.eos_token_id, n=len(prompts))
    # Everything above is pure preparation. Begin the create-only release after checks.
    out.mkdir(parents=True, exist_ok=False)
    jsonl(out / 'math_train7500.jsonl', train)
    jsonl(out / 'math500.jsonl', math500)
    jsonl(out / 'gsm8k_test1319.jsonl', gsm)
    jsonl(out / 'math_teacher_requests8993.jsonl', requests)
    dump(out / 'math_dev_examples.json', math_examples)
    dump(out / 'gsm_dev_examples.json', examples)
    dump(out / 'unsupported_math_train.json', unsupported)
    for name, data in evaluations.items():
        dump(out / (name + '.json'), data)
    frequencies = Counter(r['question_sha256'] for r in train)
    duplicates = [{'question_sha256': k, 'problem_ids': [r['problem_id'] for r in train if r['question_sha256'] == k]}
                  for k, count in frequencies.items() if count > 1]
    summary = dict(schema='p009_stage0_inputs_v1', preregistered_inputs_not_runtime_admission=True,
        math_train_rows=7500, math_unique_questions=len(train_keys), unsupported=unsupported,
        supported_rows=7493, extra_attempt_parents=500, maximum_teacher_generations=8993,
        duplicate_questions=duplicates, duplicate_policy='Generate by original row as approved; downstream unique-question curves retain earliest eligible source row and charge all attempts.',
        dev_selection='fixed SHA order, whole original solution, length-only<=floor((1024-max_question_prompt)/4), train/test-disjoint',
        math_dev_per_example_limit=per_example_limit,
        endpoint_summary={k: {a: b for a, b in v.items() if a != 'prompts'} | {'max_prompt_tokens': max(len(x['input_ids']) for x in v['prompts'])} for k, v in evaluations.items()},
        p0_reuse='Both new parity evaluations use the exact qwen_gsm_zero_parity prompts; original model calls stay closed.',
        tokenizer_files={name: manifest(path) for name, path in [('qwen',args.qwen_tokenizer),('teacher',args.teacher_tokenizer),('olmo',args.olmo_tokenizer)]})
    dump(out / 'SUMMARY.json', summary)
    dump(out / 'MANIFEST.json', manifest(out))
    print(json.dumps({'output': str(out), 'manifest_sha256': sha(out/'MANIFEST.json'),
                      'teacher_requests': len(requests), 'eval_prompt_sets': len(evaluations)}))


if __name__ == '__main__':
    main()
