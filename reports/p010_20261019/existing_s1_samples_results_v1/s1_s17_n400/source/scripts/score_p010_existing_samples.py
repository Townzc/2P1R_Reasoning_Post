"""One frozen symbolic scoring pass for each original S1 model's new samples."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import time

from experiments.p010.common import read, dump, sha, digest, utc
from experiments.p010.existing_samples_scoring import checked_rows, verify_saved_scores, LOCAL_SECONDS, SCENARIO_SECONDS
from experiments.p010.existing_samples_score_process import supervise_once

VERSIONS = {'math-verify': '0.9.0', 'latex2sympy2_extended': '1.11.0',
            'antlr4-python3-runtime': '4.13.2', 'sympy': '1.14.0', 'mpmath': '1.3.0'}
GOLD_SHA256 = '132582ca829ff11820b9d739a14c6e3ce383aacb51dba50e406acd2d27d1b95d'
SCORER_SHA256 = 'd310d7e61b049cdd750f14c65f0ad12551ee45b7eeb0913646a6447a4cbc36fe'
SCORING_SOURCES = (
    'scripts/score_p010_existing_samples.py',
    'experiments/p010/existing_samples_scoring.py',
    'experiments/p010/existing_samples_score_process.py',
    'experiments/learning_regime_p009/math_scoring.py',
    'experiments/learning_regime_p009/math_scoring_pool.py',
    'experiments/learning_regime_p009/math_scoring_journal.py',
    'experiments/learning_regime_p009/stage1_s1_scoring.py',
)


def input_binding(args):
    generated, receipt = Path(args.generation_oracle), Path(args.receipt)
    spec = read(args.spec); proof = read(generated/'COMPLETED.json')
    rows = read(generated/'SCORING_ROWS.json'); env = read(receipt/'RESULT.json')
    intent = read(receipt/'INTENT.json'); sent = read(receipt/'SUBMITTED.json')
    parent = spec['parents'][args.run]
    if ((generated/'FAILED.json').exists() or proof.get('passed') is not True
            or proof['run'] != args.run or sent['run'] != args.run or intent['run'] != args.run
            or proof['outputs_decoded'] != 2000 or proof['technical_unknown'] != 0
            or proof['greedy_outputs_generated'] != 0 or proof['new_training_updates'] != 0
            or proof['repeated_local_binary_loads'] != 0 or proof['original_greedy_reused'] is not True
            or proof['symbolic_scoring_performed'] is not False
            or proof['original_receipt_sha256'] != sha(receipt/'RESULT.json')
            or proof['original_artifact_digest'] != digest(env['artifact']['all_files'])
            or proof['original_state_sha256'] != parent['proof']['checkpoint']['sha256']
            or proof['spec_sha256'] != sha(args.spec) or proof['source_files'] != spec['source_files']
            or proof['verification_source_files'] != spec['verification_source_files']
            or proof['gold_sha256'] != GOLD_SHA256 or proof['scorer_sha256'] != SCORER_SHA256
            or proof['scoring_rows_sha256'] != sha(generated/'SCORING_ROWS.json')
            or proof['decoded_rows_sha256'] != sha(generated/'DECODED_ROWS.json')
            or proof['approval'] != intent['approval'] or env['status'] != 'completed'):
        raise ValueError('Complete original model/restore/raw/source proof required before scoring')
    checked_rows(rows)
    for name, expected in {**spec['source_files'], **spec['verification_source_files']}.items():
        if sha(name) != expected: raise ValueError('Exact reviewed source changed: '+name)
    review = read(args.runtime_review)
    if (sha(review['local_report_file']) != review['report_sha256']
            or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or review['scope'] != 'p010-C5-existing-S1-sample-only-A2'
            or review['spec_sha256'] != sha(args.spec)
            or {k:v for k,v in review.items() if k != 'local_report_file'} != proof['approval']
            or sha('experiments/learning_regime_p009/math_scoring.py') != SCORER_SHA256):
        raise ValueError('Actual exact A2 and unchanged frozen scorer required')
    versions = {name:importlib.metadata.version(name) for name in VERSIONS}
    if versions != VERSIONS: raise ValueError('Frozen symbolic versions differ')
    return rows, proof, dict(run=args.run, spec_sha256=sha(args.spec),
        original_generation_proof_sha256=sha(generated/'COMPLETED.json'),
        original_scoring_rows_sha256=sha(generated/'SCORING_ROWS.json'),
        original_receipt_sha256=sha(receipt/'RESULT.json'),
        original_state_sha256=proof['original_state_sha256'],
        source_files={name:sha(name) for name in SCORING_SOURCES}, versions=versions,
        runtime_source_files=spec['source_files'], original_review=proof['approval'],
        local_scenario_seconds=SCENARIO_SECONDS, uncalibrated_overhead_seconds=300,
        local_hard_cap_seconds=LOCAL_SECONDS, independent_A3_required=True,
        original_greedy_reused=True, new_training_updates=0)


def execute(args):
    rows, proof, binding = input_binding(args)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=False); started = time.monotonic()
    dump(out/'INTENT.json', dict(utc=utc(), binding=binding, local_seconds=LOCAL_SECONDS,
        cleanup_seconds=5, automatic_retry=False, repeated_raw_decoding=False,
        repeated_binary_loading=False, new_model_calls=0))
    try:
        seconds = int(LOCAL_SECONDS-(time.monotonic()-started))
        control = supervise_once(out/'job', rows, binding, seconds)
        checked = verify_saved_scores(out/'job/payload', rows, binding, seconds)
        if control['child_exit_code'] != 0 or not checked['passed'] or time.monotonic()-started >= LOCAL_SECONDS:
            raise TimeoutError('Original local scoring window or child completion failed')
        value = dict(**checked, run=args.run, original_state_sha256=proof['original_state_sha256'],
            logical_stops=proof['logical_stops'], original_binding=binding,
            full_generation_proof_sha256=binding['original_generation_proof_sha256'],
            scoring_control_sha256=sha(out/'job/COMPLETED.json'),
            scoring_payload_sha256=sha(out/'job/payload/COMPLETED.json'),
            independent_adjudication_complete=False, independent_A3_pending=True,
            actual_elapsed_seconds=time.monotonic()-started, utc=utc(), new_training_updates=0,
            new_generations=0, repeated_binary_loads=0, repeated_raw_decodes=0,
            original_greedy_reused=True)
        dump(out/'LOCAL_ORACLE_AUDIT.json', value)
        dump(out/'COMPLETED.json', dict(passed=True, oracle_sha256=sha(out/'LOCAL_ORACLE_AUDIT.json'),
            independent_A3_pending=True, actual_score_once=True))
        return value
    except BaseException as exc:
        dump(out/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
            partial_evidence_preserved=True, automatic_retry=False))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('generation-oracle','receipt','spec','run','runtime-review','out'):
        p.add_argument('--'+name,required=True)
    value = execute(p.parse_args())
    print(json.dumps({k:v for k,v in value.items() if k not in ('original_binding','endpoints')}))
