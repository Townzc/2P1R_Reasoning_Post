"""Score original Tier3 seed29 five endpoints once; unchanged frozen symbolic functions."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import time

from experiments.p010.common import read, dump, sha, digest, utc
from experiments.p010.e9_scoring import (
    checked_rows, verify_saved_scores, LOCAL_SECONDS, SCENARIO_SECONDS,
)
from experiments.p010.e9_score_process import supervise_once
from experiments.p010.e9_dispatch import validate_data as validate_data_binding, validate_a4
from experiments.p010.e9_contract import BASELINE

VERSIONS = {'math-verify': '0.9.0', 'latex2sympy2_extended': '1.11.0',
            'antlr4-python3-runtime': '4.13.2', 'sympy': '1.14.0', 'mpmath': '1.3.0'}
GOLD_SHA256 = '132582ca829ff11820b9d739a14c6e3ce383aacb51dba50e406acd2d27d1b95d'
SCORER_SHA256 = 'd310d7e61b049cdd750f14c65f0ad12551ee45b7eeb0913646a6447a4cbc36fe'
SCORING_SOURCES = (
    'scripts/score_p010_e9.py',
    'experiments/p010/e9_dispatch.py',
    'experiments/p010/e9_scoring.py',
    'experiments/p010/e9_score_process.py',
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
    if ((generated/'FAILED.json').exists() or proof.get('passed') is not True
            or proof['run'] != args.run or sent['run'] != args.run or intent['run'] != args.run
            or proof['outputs_decoded'] != 500 or proof['technical_unknown'] != 0
            or proof['updates_verified'] != (0 if args.run==BASELINE else 1024) or proof['targets_verified'] != (0 if args.run==BASELINE else 2097148)
            or proof['full_state_loaded_once'] is not (args.run!=BASELINE)
            or proof['symbolic_scoring_performed'] is not False
            or proof['original_receipt_sha256'] != sha(receipt/'RESULT.json')
            or proof['original_artifact_digest'] != digest(env['artifact']['all_files'])
            or (args.run!=BASELINE and proof['state_sha256'] != env['artifact']['all_files']['checkpoint_1024/state.pt']['sha256'])
            or (args.run==BASELINE and proof['state_sha256'] is not None)
            or proof['spec_sha256'] != sha(args.spec) or proof['source_files'] != spec['source_files']
            or proof['gold_sha256'] != GOLD_SHA256 or proof['scorer_sha256'] != SCORER_SHA256
            or proof['scoring_rows_sha256'] != sha(generated/'SCORING_ROWS.json')
            or proof['decoded_rows_sha256'] != sha(generated/'DECODED_ROWS.json')
            or proof['reviews'] != intent['reviews'] or env['status'] != 'completed'):
        raise ValueError('Original complete state/raw/source proof required before symbolic scoring')
    checked_rows(rows)
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Actual original runtime source changed: '+name)
    for label, name in [('A1', args.data_review), ('A2', args.runtime_review)]:
        review = read(name)
        if (sha(review['local_report_file']) != review['report_sha256']
                or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
                or {k: v for k, v in review.items() if k != 'local_report_file'} != proof['reviews'][label]):
            raise ValueError('Original exact review differs')
    validate_data_binding(spec, args.run, proof['reviews']['A1'])
    validate_a4(proof['reviews']['A4']['report'], proof['reviews']['actual_results_A3'])
    if (proof['reviews']['A2']['scope'] != 'p010-E9-complete-runtime-A2'
            or proof['reviews']['A2']['spec_sha256'] != sha(args.spec)
            or sha('experiments/learning_regime_p009/math_scoring.py') != SCORER_SHA256):
        raise ValueError('Frozen scorer and original A1/A2 scope differ')
    versions = {name: importlib.metadata.version(name) for name in VERSIONS}
    if versions != VERSIONS:
        raise ValueError('Frozen local symbolic versions differ')
    return rows, proof, dict(run=args.run, spec_sha256=sha(args.spec),
        original_generation_proof_sha256=sha(generated/'COMPLETED.json'),
        original_scoring_rows_sha256=sha(generated/'SCORING_ROWS.json'),
        original_receipt_sha256=sha(receipt/'RESULT.json'), original_state_sha256=proof['state_sha256'],
        source_files={name: sha(name) for name in SCORING_SOURCES}, versions=versions,
        runtime_source_files=spec['source_files'], original_reviews=proof['reviews'],
        local_scenario_seconds=SCENARIO_SECONDS, uncalibrated_overhead_seconds=300,
        local_hard_cap_seconds=LOCAL_SECONDS, independent_A3_required=True)


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
        if (control['child_exit_code'] != 0 or not checked['passed']
                or time.monotonic()-started >= LOCAL_SECONDS):
            raise TimeoutError('Original local scoring window or child completion failed')
        value = dict(**checked, run=args.run, updates_verified=proof['updates_verified'], targets_verified=proof['targets_verified'],
            state_sha256=proof['state_sha256'], logical_stops=proof['logical_stops'],
            original_binding=binding, full_generation_proof_sha256=binding['original_generation_proof_sha256'],
            scoring_control_sha256=sha(out/'job/COMPLETED.json'),
            scoring_payload_sha256=sha(out/'job/payload/COMPLETED.json'),
            independent_adjudication_complete=False, independent_A3_pending=True,
            actual_elapsed_seconds=time.monotonic()-started, utc=utc(),
            new_training_updates=0, new_generations=0, repeated_binary_loads=0,
            repeated_raw_decodes=0)
        dump(out/'LOCAL_ORACLE_AUDIT.json', value)
        dump(out/'COMPLETED.json', dict(passed=True, oracle_sha256=sha(out/'LOCAL_ORACLE_AUDIT.json'),
            independent_A3_pending=True, actual_score_once=True))
        return value
    except BaseException as exc:
        dump(out/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
            partial_evidence_preserved=True, automatic_retry=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('generation-oracle', 'receipt', 'spec', 'run', 'data-review', 'runtime-review', 'out'):
        parser.add_argument('--'+name, required=True)
    value = execute(parser.parse_args())
    print(json.dumps({k: v for k, v in value.items() if k not in ('original_binding', 'endpoints')}))
