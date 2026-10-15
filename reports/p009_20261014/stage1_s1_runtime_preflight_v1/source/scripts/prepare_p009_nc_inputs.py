"""Create the two registered NC input candidates locally, never admit a worker.

Reuse the original complete D1 inventory and its exact G1 evidence. This is a
new P009 encoding/selection/1024-step planning operation, not a repeat oracle or
teacher/student call. An incomplete output directory blocks a whole-tool retry.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import traceback

from experiments.sft_allocation_midpoint.common import digest, dump, manifest, read, sha, verify
from experiments.learning_regime_p009.stage1_roster import nested_encoded_sets
from experiments.learning_regime_p009.training_plan import make_plan, TARGETS, UPDATES, LR_VECTOR_SHA256
from src.sft_data import encode_row

CORPUS_SHA = '3e239334229b5b79dd86dac3cdd789469038fd4be4a54c924c7dadf8a0b6d2f0'
INPUT_MANIFEST_SHA = 'dae1bd27ae469f5b8c32af68146f8447717af5ef4f6299b36f8ddf2bcbf8ee24'
PROMPTS_SHA = 'bfbb7b5b131de24a0d65e524f2eff356864a6019e8d16a51934e25843cd7451c'
STAGE0_SUMMARY_SHA = 'e50b48baff1497e37d0e4cf25ae63dcb2970a8bd029321e976190fadf6f8bf5e'
OLD_G1 = {
    'G1_D1_ACCEPTED.json': ('4a8bace07f8e0bb30e12294ad92f2a26d7ff844b',
        'ffff275684f860b1dca142b401ce5b59c7f2c9804d09d4fc8decd88ebbb3f659'),
    'G1_D1_POOL_ACCEPTED.json': ('b4a0e5e7f43f580d4d7c8eab92ad7b1f6e16d0dc',
        'c6d808172e8c7f16aad507099ad94f36af9f1dc537b1b8d13e3aeb043d6cdbd3'),
}


def physical_jsonl(path):
    # U+2028/U+2029 inside JSON strings are not physical JSONL separators.
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def checked_encoding(row, encoded):
    source = row['source']
    if (source['candidate_id'] != row['path_id']
            or encoded['problem_id'] != row['problem_id']
            or encoded['path_id'] != row['path_id']
            or encoded['response_hash'] != source['response_sha256']
            or hashlib.sha256(row['response'].encode()).hexdigest() != source['response_sha256']
            or any(encoded[k] != source[k] for k in ('n_prompt', 'n_processed', 'n_supervised'))):
        raise ValueError('Original accepted complete answer or token lengths differ')


def original_endpoint(value):
    if (value['n'] != 1319 or value['eos_token_id'] != 151643
            or value['max_context'] != 2048 or value['max_new_tokens'] != 512
            or len(value['prompts']) != 1319):
        raise ValueError('Original complete GSM zero-shot endpoint differs')
    result = []
    for i, row in enumerate(value['prompts']):
        if (row['problem_id'] != f'gsm8k/test/{i:05d}'
                or not isinstance(row['input_ids'], list) or not 0 < len(row['input_ids']) <= 1536
                or any(type(x) is not int or not 0 <= x < 151936 for x in row['input_ids'])):
            raise ValueError('Original complete ordered prompt token IDs required')
        item = dict(problem_id=row['problem_id'], input_ids=row['input_ids'])
        result.append(dict(**item, candidate_id='NC::'+row['problem_id'],
                           source_row_sha256=digest(item)))
    return result


def prepare(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    dump(out/'PREPARATION_STARTED.json', dict(started_utc=datetime.now(timezone.utc).isoformat(),
        operation='new_P009_NC_input_candidates_only', runtime_admitted=False,
        no_model_calls=True, no_raw_oracle=True, no_source_scoring=True))
    try:
        old = Path(args.old_root); inputs = Path(args.stage0_inputs)
        corpus = old/'student_preparation_r1/inputs/d1_b8_p0_breadth.jsonl'
        old_manifest = corpus.parent/'MANIFEST.json'
        if sha(corpus) != CORPUS_SHA or sha(old_manifest) != INPUT_MANIFEST_SHA:
            raise ValueError('Immutable original D1 input bytes differ')
        verify(corpus.parent, {corpus.name: read(old_manifest)['files'][corpus.name]})
        if (sha(inputs/'SUMMARY.json') != STAGE0_SUMMARY_SHA
                or sha(inputs/'qwen_gsm_zero_parity.json') != PROMPTS_SHA):
            raise ValueError('Original tokenizer/prompt binding differs')
        tokenizer_files = read(inputs/'SUMMARY.json')['tokenizer_files']['qwen']
        verify(args.tokenizer, tokenizer_files)
        provenance = {}
        for name, (commit, report_sha) in OLD_G1.items():
            record = read(old/name); report = old/record['local_report_path']
            if (record['verdict'] not in ('PASS', 'PASS-WITH-NOTES')
                    or record['review_commit'] != commit or record['review_report_sha256'] != report_sha
                    or sha(report) != report_sha):
                raise ValueError('Real original fixed G1 report binding differs')
            provenance[name] = {k: v for k, v in record.items() if k != 'local_report_path'}
            shutil.copyfile(report, out/(name+'.REPORT.md'))
        if (provenance['G1_D1_ACCEPTED.json']['input_sha256'] != INPUT_MANIFEST_SHA
                or provenance['G1_D1_ACCEPTED.json']['pool_G1_acceptance_sha256']
                    != sha(old/'G1_D1_POOL_ACCEPTED.json')):
            raise ValueError('Original pool/input acceptance chain differs')
        roster_review = read(args.roster_review)
        if (roster_review['scope'] != 'p009-stage1-roster-selection-code'
                or roster_review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
                or roster_review['target_commit'] != 'fd03e883c9377258c81ce080cef79dedee856b82'
                or sha(roster_review['local_report_path']) != roster_review['report_sha256']):
            raise ValueError('Actual fixed roster code acceptance required')
        for name, expected in roster_review['source_files'].items():
            if sha(name) != expected:
                raise ValueError('Accepted roster dependency changed: '+name)
        rows = physical_jsonl(corpus)
        if len(rows) != 3436:
            raise ValueError('Retain all3436 original complete accepted D1 answers')
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
        if tokenizer.eos_token_id != 151643:
            raise ValueError('Original Qwen EOS required')
        encoded = []
        for row in rows:
            value = encode_row(row, tokenizer, 2048)
            checked_encoding(row, value)
            encoded.append(value)
        selection = nested_encoded_sets(encoded, 17, 151643, negative_control=True)
        by_id = {row['problem_id']: (row, value) for row, value in zip(rows, encoded)}
        if len(by_id) != 3436:
            raise ValueError('Original inventory contains duplicate question IDs')
        dump(out/'ROSTER.json', selection)
        dump(out/'ORIGINAL_G1.json', provenance)
        dump(out/'ROSTER_CODE_ACCEPTED.json', {k: v for k, v in roster_review.items() if k != 'local_report_path'})
        shutil.copyfile(roster_review['local_report_path'], out/'ROSTER_CODE_REPORT.md')
        shutil.copyfile(corpus, out/'ORIGINAL_D1_INPUT.jsonl')
        dump(out/'ALL_ENCODED.json', encoded)
        dump(out/'NC_ENDPOINT.json', original_endpoint(read(inputs/'qwen_gsm_zero_parity.json')))
        # The original exact model descriptor is copied, not downloaded or loaded.
        original_model = read(args.generation_admission)['models']['qwen']
        model = {key: original_model[key] for key in
                 ('model_id', 'revision', 'architecture', 'vocab_size', 'eos_token_ids')}
        if model != dict(model_id='Qwen/Qwen2.5-1.5B',
                revision='8faed761d45a263340a0528343f099c05c9a4323',
                architecture='Qwen2ForCausalLM', vocab_size=151936, eos_token_ids=[151643]):
            raise ValueError('Original Qwen base descriptor differs')
        summaries = {}
        for n in (400, 3200):
            pid_order = selection['selections'][str(n)]['problem_ids']
            rr = [by_id[pid][0] for pid in pid_order]
            ee = [by_id[pid][1] for pid in pid_order]
            plan = make_plan(ee, 17, 151643)
            config = dict(setting='NC', seed=17, n=n, model=model, updates=UPDATES, targets=TARGETS,
                encoded_rows_sha256=digest(ee), training_rows_sha256=digest(rr),
                plan_sha256=digest(plan), lr_vector_sha256=LR_VECTOR_SHA256)
            for suffix, value in [('rows', rr), ('encoded', ee), ('plan', plan), ('config', config)]:
                dump(out/f'nc17_n{n}_{suffix}.json', value)
            summaries[str(n)] = dict(config=config,
                once_each_target_sum=sum(x['n_supervised'] for x in ee),
                q=plan['q'], exposure_min=min(plan['row_exposures']),
                exposure_max=max(plan['row_exposures']),
                presentations=sum(plan['row_exposures']), zero_exposure_answers=plan['zero_exposure_answers'])
        basis = dict(schema='p009_nc_input_candidate_v1', original_corpus_sha256=CORPUS_SHA,
            original_input_manifest_sha256=INPUT_MANIFEST_SHA, original_inventory_count=3436,
            original_prompt_file_sha256=PROMPTS_SHA, tokenizer_files=tokenizer_files,
            generation_admission_file_sha256=sha(args.generation_admission),
            roster_code_review_sha256=sha(args.roster_review), source_file_sha256=sha(__file__),
            whole_answer_target_budget=TARGETS, seed=17, sizes=[400, 3200],
            summaries=summaries, new_training_updates=0, new_generations=0,
            runtime_admitted=False, actual_input_external_review_accepted=False,
            G0_external_review_required=True, new_runtime_and_numeric_review_required=True,
            no_historical_HF_effect_comparison=True)
        dump(out/'BASIS.json', basis)
        files = manifest(out)
        dump(out/'MANIFEST.json', files)
        verify(out, files)
        dump(out/'PREPARATION_COMPLETED.json', dict(completed_utc=datetime.now(timezone.utc).isoformat(),
            basis_sha256=digest(basis), manifest_sha256=sha(out/'MANIFEST.json'),
            runtime_admitted=False))
        print(json.dumps({'out': str(out), 'summaries': summaries, 'runtime_admitted': False}))
    except BaseException:
        dump(out/'PREPARATION_FAILED.json', dict(failed_utc=datetime.now(timezone.utc).isoformat(),
            traceback=traceback.format_exc(), whole_tool_retry_allowed=False))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('out', 'old-root', 'stage0-inputs', 'tokenizer', 'roster-review', 'generation-admission'):
        parser.add_argument('--'+name, required=True)
    prepare(parser.parse_args())


if __name__ == '__main__':
    main()
