"""Score only the original 3,200 new E3 rows once after full generation proof."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import time

from experiments.p010.common import read, dump, sha, digest, utc
from experiments.p010.e3_scoring import checked_rows, verify_saved_scores, LOCAL_SECONDS, SCENARIO_SECONDS
from experiments.p010.e3_score_process import supervise_once
from experiments.p010.tier3_dispatch import fixed_review, validate_a4

VERSIONS = {'math-verify': '0.9.0', 'latex2sympy2_extended': '1.11.0',
            'antlr4-python3-runtime': '4.13.2', 'sympy': '1.14.0', 'mpmath': '1.3.0'}
SCORER_SHA256 = 'd310d7e61b049cdd750f14c65f0ad12551ee45b7eeb0913646a6447a4cbc36fe'


def input_binding(a):
    generated, receipt = Path(a.generation_oracle), Path(a.receipt)
    spec = read(a.spec); proof = read(generated/'COMPLETED.json')
    rows = read(generated/'SCORING_ROWS.json'); env = read(receipt/'RESULT.json')
    intent = read(receipt/'INTENT.json'); sent = read(receipt/'SUBMITTED.json')
    sources = {**spec['source_files'], **spec['verification_source_files']}
    if ((generated/'FAILED.json').exists() or proof.get('passed') is not True
            or sent['run'] != 'temperature_supply_r1' or env['status'] != 'completed'
            or proof['outputs_decoded'] != 3200 or proof['technical_unknown'] != 0
            or proof['symbolic_scoring_performed'] is not False or proof['old_T08_decodes'] != 0
            or proof['new_training_updates'] != 0 or proof['old_binary_loads'] != 0
            or proof['original_receipt_sha256'] != sha(receipt/'RESULT.json')
            or proof['original_artifact_digest'] != digest(env['artifact']['all_files'])
            or proof['spec_sha256'] != sha(a.spec) or proof['source_files'] != spec['source_files']
            or proof['verification_source_files'] != spec['verification_source_files']
            or proof['gold_source_sha256'] != spec['gold_source_sha256']
            or proof['scorer_sha256'] != SCORER_SHA256
            or proof['scoring_rows_sha256'] != sha(generated/'SCORING_ROWS.json')
            or proof['decoded_rows_sha256'] != sha(generated/'DECODED_ROWS.json')
            or proof['reviews'] != intent['reviews']):
        raise ValueError('Original complete 3200-row source/raw proof required')
    checked_rows(rows)
    for name, expected in sources.items():
        if sha(name) != expected:
            raise ValueError('Frozen runtime or verification source changed: '+name)
    review = read(a.runtime_review)
    if (fixed_review(review) != proof['reviews']['A2']
            or review['scope'] != spec['runtime_A2_scope']
            or review['spec_sha256'] != sha(a.spec)
            or review['source_files'] != spec['source_files']
            or review.get('input_A1_accepted') is not True
            or review.get('all_old_T08_outputs_reused_without_rescoring') is not True
            or sha('experiments/learning_regime_p009/math_scoring.py') != SCORER_SHA256):
        raise ValueError('Exact original A1/A2 and frozen scorer required')
    validate_a4(proof['reviews']['A4']['report'], proof['reviews']['actual_results_A3'])
    versions = {name: importlib.metadata.version(name) for name in VERSIONS}
    if versions != VERSIONS:
        raise ValueError('Frozen symbolic versions differ')
    return rows, proof, dict(spec_sha256=sha(a.spec),
        original_generation_proof_sha256=sha(generated/'COMPLETED.json'),
        original_scoring_rows_sha256=sha(generated/'SCORING_ROWS.json'),
        original_receipt_sha256=sha(receipt/'RESULT.json'), source_files=sources,
        versions=versions, original_reviews=proof['reviews'], old_T08_symbolic_calls=0,
        local_scenario_seconds=SCENARIO_SECONDS, uncalibrated_overhead_seconds=300,
        local_hard_cap_seconds=LOCAL_SECONDS, independent_A3_required=True)


def execute(a):
    rows, proof, binding = input_binding(a)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=False); started = time.monotonic()
    dump(out/'INTENT.json', dict(utc=utc(), binding=binding, local_seconds=LOCAL_SECONDS,
        cleanup_seconds=5, automatic_retry=False, repeated_raw_decoding=False,
        repeated_binary_loading=False, old_T08_scoring=False, new_model_calls=0))
    try:
        seconds = int(LOCAL_SECONDS-(time.monotonic()-started))
        control = supervise_once(out/'job', rows, binding, seconds)
        checked = verify_saved_scores(out/'job/payload', rows, binding, seconds)
        if (control['child_exit_code'] != 0 or not checked['passed']
                or time.monotonic()-started >= LOCAL_SECONDS):
            raise TimeoutError('Original local scoring window or child completion failed')
        value = dict(**checked, technical_unknown=0, logical_stops=proof['stops'], original_binding=binding,
            full_generation_proof_sha256=binding['original_generation_proof_sha256'],
            scoring_control_sha256=sha(out/'job/COMPLETED.json'),
            scoring_payload_sha256=sha(out/'job/payload/COMPLETED.json'),
            independent_adjudication_complete=False, independent_A3_pending=True,
            actual_elapsed_seconds=time.monotonic()-started, utc=utc(),
            new_training_updates=0, new_generations=0, repeated_binary_loads=0,
            repeated_raw_decodes=0, old_T08_symbolic_calls=0)
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
    for name in ('generation-oracle', 'receipt', 'spec', 'runtime-review', 'out'):
        p.add_argument('--'+name, required=True)
    v = execute(p.parse_args())
    print(json.dumps({k:v[k] for k in ('passed', 'outputs', 'technical_unknown', 'utc')}))
