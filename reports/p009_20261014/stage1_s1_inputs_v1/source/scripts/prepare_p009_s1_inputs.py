"""Freeze S1 input candidates from accepted original P1 records, without scoring.

This is one new local selection/encoding/whole-answer planning operation. It
does not admit a worker. An existing or partial output blocks a whole-tool retry.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import traceback

from experiments.sft_allocation_midpoint.common import digest, dump, manifest, read, sha, verify
from experiments.learning_regime_p009.stage1_roster import math_first_attempt_inventory, nested_encoded_sets
from experiments.learning_regime_p009.training_plan import make_plan, TARGETS, UPDATES, LR_VECTOR_SHA256
from src.sft_data import encode_row, read_jsonl

P1_TARGET = 'ae8b8c3c2f1ad75bac25678d49f85f6a7c1b6694'
P1_SCOPE = 'p009-math-p1-complete-scoring-and-independent-adjudication-A2'
GENERATION_SPEC = 'e3775978166cf1e5209c864ef3e3e84c03c2751c3c58cbe2c14a58273efa6b24'


def require_p1_review(value):
    if (value.get('scope') != P1_SCOPE or value.get('target_commit') != P1_TARGET
            or value.get('decision') != 'PASS_WITH_SEPARATE_ELIGIBILITY_AND_G0_DISPOSITIONS'
            or value.get('teacher_labels_eligible_for_frozen_roster') is not True
            or value.get('raw_integrity_passed') is not True or value.get('labels_changed') is not False
            or value.get('independent_adjudication_decision') not in ('PASS', 'PASS-WITH-NOTES')
            or value.get('adjudicated_sample_count') != 117
            or value.get('G0', {}).get('S1') != dict(passed=True, teacher_correct=359,
                student_zero_correct=136, total=500, caps=[36, 68], technical_unknown=0)):
        raise ValueError('Actual complete P1, independent adjudication, eligibility and S1 G0 required')
    return value


def join_original_rows(rows, scores, excluded, generated):
    """Only reference the accepted original fields; no answer parsing/decoding."""
    score_map = {x['id']: x for x in scores}
    if len(rows) != 10489 or len(scores) != 10489 or len(score_map) != len(scores):
        raise ValueError('All complete P1 rows required before subset binding')
    if {x['id'] for x in rows} != set(score_map):
        raise ValueError('Complete score/input identities differ')
    proc = [x for x in rows if x['dataset'] == 'math_procurement']
    unsupported = [x for x in excluded if x['dataset'] == 'math_procurement']
    if len(proc) != 8989 or len(unsupported) != 4 or len(excluded) != 4 or len(generated) != 8993:
        raise ValueError('Original supported and unsupported denominators differ')
    raw_map = {x['id']: x for x in generated}
    if len(raw_map) != len(generated):
        raise ValueError('Duplicate original generation identity')
    for row in proc:
        if row['original_generation_record'] != raw_map.get(row['id']):
            raise ValueError('Original P1 generation lineage differs')
    for row in unsupported:
        if row['original_record'] != raw_map.get(row['id']) or row['id'] in score_map:
            raise ValueError('Unsupported gold must retain its original unscored record')
    if {x['id'] for x in proc} | {x['id'] for x in unsupported} != set(raw_map):
        raise ValueError('Missing generated row')
    return [score_map[x['id']] for x in proc], [x['id'] for x in unsupported]


def original_endpoint(value, gold):
    if (value.get('n') != 500 or value.get('eos_token_id') != 151643
            or value.get('max_context') != 2048 or value.get('max_new_tokens') != 1024
            or len(value.get('prompts', [])) != 500 or len(gold) != 500):
        raise ValueError('Original complete MATH zero-shot endpoint required')
    ids = [x['problem_id'] for x in gold]
    if len(set(ids)) != 500 or [x['problem_id'] for x in value['prompts']] != ids:
        raise ValueError('Original MATH500 order and membership differ')
    result = []
    for row in value['prompts']:
        tokens = row['input_ids']
        if (not isinstance(tokens, list) or not 0 < len(tokens) <= 1024
                or any(type(x) is not int or not 0 <= x < 151936 for x in tokens)):
            raise ValueError('Original full endpoint token IDs differ')
        item = dict(problem_id=row['problem_id'], input_ids=tokens)
        result.append(dict(**item, candidate_id='S1::'+row['problem_id'], source_row_sha256=digest(item)))
    return result


def checked_report(path, scope, out, name):
    value = read(path)
    if (value['scope'] != scope or len(value.get('report_commit', '')) != 40
            or sha(value['local_report_path']) != value['report_sha256']):
        raise ValueError('Original fixed review report must be locally present')
    shutil.copyfile(value['local_report_path'], out/(name+'.REPORT.md'))
    projected = {k: v for k, v in value.items() if k != 'local_report_path'}
    dump(out/(name+'.json'), projected)
    return value


def prepare(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
    dump(out/'PREPARATION_STARTED.json', dict(utc=datetime.now(timezone.utc).isoformat(),
        new_input_candidate_only=True, model_calls=0, symbolic_calls=0, runtime_admitted=False))
    try:
        p1 = Path(args.p1_root); inputs = Path(args.stage0_inputs); gen = Path(args.generation_root)
        pub = Path(args.p1_publication)
        review = require_p1_review(checked_report(args.p1_review, P1_SCOPE, out, 'P1_A2_ACCEPTED'))
        for key, filename in [('manifest_file_sha256', 'MANIFEST.json'),
                ('collection_file_sha256', 'COLLECTION.json'), ('summary_file_sha256', 'SUMMARY.json')]:
            if sha(pub/filename) != review[key]:
                raise ValueError('Actual reviewed complete P1 publication differs')
        original = read(pub/'COLLECTION.json')['original_files']
        names = ('ROWS.json', 'ALL_SCORED_ROWS.json', 'UNSUPPORTED_GOLD.json',
                 'INPUT_SUMMARY.json', 'INPUT_BINDING.json', 'FROZEN.json',
                 'ALL_ROWS_SCORED.json', 'REMAINDER_COMPLETED.json')
        verify(p1, {n: original[n] for n in names})
        summary = read(p1/'INPUT_SUMMARY.json')
        spec = read(args.generation_admission)
        if digest(spec) != GENERATION_SPEC or summary['generation_spec_sha256'] != GENERATION_SPEC:
            raise ValueError('Actual accepted Stage0 generation specification differs')
        proof = summary['generation_proof']['teacher_p2_p3']
        oracle_path = gen/'exports/teacher_p2_p3/evidence/LOCAL_ORACLE_AUDIT.json'
        if sha(oracle_path) != proof['oracle_sha256']:
            raise ValueError('Original complete teacher oracle differs')
        oracle = read(oracle_path)
        if oracle['passed'] is not True:
            raise ValueError('Complete original raw oracle must pass')
        for name, key in [('provider.json', 'provider_sha256'), ('COMPLETED.json', 'closeout_sha256')]:
            if sha(gen/'closeouts/teacher_p2_p3'/name) != proof[key]:
                raise ValueError('Original generation closeout differs')
        provider = read(gen/'closeouts/teacher_p2_p3/provider.json')
        if provider['state'] != 'stopped' or provider['owned_container_ids']:
            raise ValueError('Original teacher must have stopped')
        for filename in ('math_train7500.jsonl', 'math500.jsonl'):
            if sha(inputs/filename) != spec['local_gold_files'][filename]['sha256']:
                raise ValueError('Frozen original source rows differ')
        if sha(inputs/'qwen_math_zero.json') != spec['inputs']['qwen_math_zero.json']['sha256']:
            raise ValueError('Original endpoint bytes differ')
        tokenizer_files = read(inputs/'SUMMARY.json')['tokenizer_files']['qwen']
        verify(args.tokenizer, tokenizer_files)
        roster_review = checked_report(args.roster_review, 'p009-stage1-roster-selection-code',
                                       out, 'ROSTER_CODE_ACCEPTED')
        if (roster_review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
                or roster_review['target_commit'] != 'fd03e883c9377258c81ce080cef79dedee856b82'):
            raise ValueError('Actual exact roster code review required')
        for name, expected in roster_review['source_files'].items():
            if sha(name) != expected:
                raise ValueError('Accepted roster source changed: '+name)
        train = read_jsonl(inputs/'math_train7500.jsonl')
        if len(train) != 7500:
            raise ValueError('Complete frozen training source required')
        generated = oracle['decoded']['math_procurement']
        labels, unsupported = join_original_rows(read(p1/'ROWS.json'), read(p1/'ALL_SCORED_ROWS.json'),
                                                read(p1/'UNSUPPORTED_GOLD.json'), generated)
        inventory = math_first_attempt_inventory(train, generated, labels, unsupported)
        dump(out/'ELIGIBLE_INVENTORY.json', inventory)
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
        if tokenizer.eos_token_id != 151643:
            raise ValueError('Original Qwen native EOS required')
        encoded = [encode_row(row, tokenizer, 2048) for row in inventory['rows']]
        dump(out/'ALL_ENCODED.json', encoded)
        by_id = {r['problem_id']: (r, e) for r, e in zip(inventory['rows'], encoded)}
        if len(by_id) != len(encoded):
            raise ValueError('One complete answer per unique normalized question required')
        endpoint = original_endpoint(read(inputs/'qwen_math_zero.json'), read_jsonl(inputs/'math500.jsonl'))
        dump(out/'S1_ENDPOINT.json', endpoint)
        model = {k: spec['models']['qwen'][k] for k in
                 ('model_id', 'revision', 'architecture', 'vocab_size', 'eos_token_ids')}
        summaries = {}
        for seed in (17, 29):
            selection = nested_encoded_sets(encoded, seed, 151643)
            dump(out/f'ROSTER_s{seed}.json', selection)
            for size, item in selection['selections'].items():
                n = int(size); rr = [by_id[x][0] for x in item['problem_ids']]
                ee = [by_id[x][1] for x in item['problem_ids']]
                plan = make_plan(ee, seed, 151643)
                config = dict(setting='S1', seed=seed, n=n, model=model, updates=UPDATES, targets=TARGETS,
                    encoded_rows_sha256=digest(ee), training_rows_sha256=digest(rr), plan_sha256=digest(plan),
                    lr_vector_sha256=LR_VECTOR_SHA256)
                run = f's1_s{seed}_n{n}'
                for suffix, value in [('rows', rr), ('encoded', ee), ('plan', plan), ('config', config)]:
                    dump(out/f'{run}_{suffix}.json', value)
                summaries[run] = dict(config=config, once_each_target_sum=item['once_each_target_sum'],
                    q=plan['q'], exposure_min=min(plan['row_exposures']), exposure_max=max(plan['row_exposures']),
                    presentations=sum(plan['row_exposures']), zero_exposure_answers=plan['zero_exposure_answers'])
        basis = dict(schema='p009_s1_actual_input_candidates_v1', source_file_sha256=sha(__file__),
            p1_A2_review_sha256=sha(args.p1_review), p1_actual_target=P1_TARGET,
            P1_source_file_bindings={n: original[n] for n in names}, generation_proof=proof,
            generation_spec_sha256=GENERATION_SPEC, train_file_sha256=sha(inputs/'math_train7500.jsonl'),
            original_prompt_file_sha256=sha(inputs/'qwen_math_zero.json'), tokenizer_files=tokenizer_files,
            original_generated_rows=len(generated), scorable_procurement=len(labels), unsupported_gold=unsupported,
            source_rows=inventory['source_rows'], normalized_unique_questions=inventory['normalized_unique_questions'],
            duplicate_rows=inventory['duplicate_rows'], eligible_distinct_questions=len(encoded),
            eligibility='pre_label_first_normalized_question_then_attempt01_nativeEOS_parseable_correct_only',
            stage2_raw_seed17_order_not_redefined=True, summaries=summaries,
            full_inventory_encoded=True, new_model_calls=0, symbolic_calls=0, raw_decoding_repeated=False,
            labels_changed=False, runtime_admitted=False, external_input_review_accepted=False,
            NC_must_pass_before_S1_dispatch=True, scientific_stop_rules_unchanged=True)
        dump(out/'BASIS.json', basis)
        files = manifest(out); dump(out/'MANIFEST.json', files); verify(out, files)
        dump(out/'PREPARATION_COMPLETED.json', dict(utc=datetime.now(timezone.utc).isoformat(),
            basis_sha256=digest(basis), manifest_sha256=sha(out/'MANIFEST.json'), runtime_admitted=False))
        print(json.dumps(dict(out=str(out), eligible_distinct_questions=len(encoded), summaries=summaries)))
    except BaseException:
        dump(out/'PREPARATION_FAILED.json', dict(utc=datetime.now(timezone.utc).isoformat(),
            traceback=traceback.format_exc(), whole_tool_retry_allowed=False))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('out', 'p1-root', 'p1-publication', 'p1-review', 'stage0-inputs',
                 'generation-root', 'generation-admission', 'tokenizer', 'roster-review'):
        parser.add_argument('--'+name, required=True)
    prepare(parser.parse_args())


if __name__ == '__main__':
    main()
